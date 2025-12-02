from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.db.models import Min, Max, Sum
from django.template.loader import get_template
from datetime import datetime, timedelta
from django.http import JsonResponse
from collections import defaultdict
from .utils import compare_lithology_with_prognosis
import os
import importlib.util
from django.template.loader import render_to_string
from io import BytesIO
from xhtml2pdf import pisa
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.platypus import Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import (
    WellData, Core, GrainSize, Mineralogy, Fossils,
    GasField, Well, ProductionData,
    ExplorationTimeline, ExplorationCategory, OperationActivity,
    DailyDrillingReport, WellPrognosis, DrillingLithology
)
from .forms import DailyDrillingReportForm, DrillingLithologyForm

# Load the `plotter/utils/pdf_parser.py` module directly to avoid
# "not a package" errors when a `plotter/utils.py` module exists.
_pdf_parser_path = os.path.join(os.path.dirname(__file__), 'utils', 'pdf_parser.py')
spec = importlib.util.spec_from_file_location('plotter.utils.pdf_parser', _pdf_parser_path)
pdf_parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pdf_parser)
parse_pdf_text = pdf_parser.parse_pdf_text
extract_drilling_report_data = pdf_parser.extract_drilling_report_data
extract_lithology_data = pdf_parser.extract_lithology_data

def login_view(request):
    """Handle user login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'registration/login.html')

def logout_view(request):
    """Handle user logout"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')

@login_required
def dashboard(request):
    # Get recent operation activities (limit to 10 most recent)
    recent_activities = OperationActivity.objects.filter(is_active=True)[:10]
    
    context = {
        'recent_activities': recent_activities,
    }
    return render(request, 'visualization/dashboard.html', context)

@login_required
def credits(request):
    return render(request, 'visualization/credits.html')

@login_required
def graph_view(request):
    selected_well = request.GET.get('well_name')
    selected_core = request.GET.get('core_no')

    # Fetch core numbers filtered by the selected well
    core_numbers = (
        WellData.objects.filter(well_name=selected_well)
        .values_list('core_no', flat=True)
        .distinct()
        if selected_well
        else Core.objects.values_list('core_no', flat=True)
    )

    if selected_well and selected_core:
        # Fetch the core and well data
        core = Core.objects.get(well_name=selected_well, core_no=selected_core)
        well_data = WellData.objects.filter(
            well_name=selected_well, 
            core_no=selected_core
        ).values('depth', 'porosity', 'perm_kair')
        
        # Fetch grain size data for the selected core
        grain_size_data = GrainSize.objects.filter(core=core).order_by('sampling_depth_start')
        
        # Fetch mineralogy data for the selected core
        mineralogy_data = Mineralogy.objects.filter(core=core).order_by('sampling_depth_start', 'analysis_type')
        
        # Fetch fossils data for the selected core
        fossils_data = Fossils.objects.filter(core=core).order_by('sampling_depth_start')
        
        # Convert to list for JSON serialization
        data_list = list(well_data)
        
        # Prepare grain size chart data
        grain_size_chart_data = {
            'depths': [f"{gs.sampling_depth_start}-{gs.sampling_depth_end}" for gs in grain_size_data],
            'depth_midpoints': [gs.depth_midpoint for gs in grain_size_data],
            'gravel': [gs.gravel_percent or 0 for gs in grain_size_data],
            'coarse_sand': [gs.coarse_sand_percent or 0 for gs in grain_size_data],
            'medium_sand': [gs.medium_sand_percent or 0 for gs in grain_size_data],
            'fine_sand': [gs.fine_sand_percent or 0 for gs in grain_size_data],
            'very_fine_sand': [gs.very_fine_sand_percent or 0 for gs in grain_size_data],
            'silt': [gs.silt_percent or 0 for gs in grain_size_data],
            'clay': [gs.clay_percent or 0 for gs in grain_size_data]
        }
        
        # Group mineralogy data by analysis type
        bulk_mineralogy = mineralogy_data.filter(analysis_type='bulk')
        clay_mineralogy = mineralogy_data.filter(analysis_type='clay')
        
        # Prepare data for the template
        context = {
            'selected_well': selected_well,
            'selected_core': selected_core,
            'core_img_url': core.image.url if core.image else None,
            'litho_image_url': core.litho_image.url if core.litho_image else None,
            'well_names': WellData.objects.values_list('well_name', flat=True).distinct(),
            'core_numbers': core_numbers,
            'chart_data': {
                'depths': [d['depth'] for d in data_list],
                'porosity': [d['porosity'] for d in data_list],
                'permeability': [d['perm_kair'] for d in data_list]
            },
            'grain_size_data': grain_size_data,
            'grain_size_chart_data': grain_size_chart_data,
            'bulk_mineralogy': bulk_mineralogy,
            'clay_mineralogy': clay_mineralogy,
            'fossils_data': fossils_data
        }
    else:
        context = {
            'well_names': WellData.objects.values_list('well_name', flat=True).distinct(),
            'core_numbers': core_numbers,
            'selected_well': selected_well,
            'selected_core': selected_core
        }

    return render(request, 'visualization/graph.html', context)




@login_required
def production_graph(request):
    # Get all gas fields with their related wells
    gas_fields = GasField.objects.prefetch_related('wells').all()
    
    # Group the attributes into rate and cumulative parameters
    rate_attributes = [
        ('flow_rate', 'Flow Rate (MMscf/d)'),
        ('water_production', 'Water Production (bbl/d)'),
        ('condensate_production', 'Condensate Production (bbl/d)')
    ]
    
    cumulative_attributes = [
        ('cumulative_flow_rate', 'Cumulative Flow Rate (MMscf)'),
        ('cumulative_water', 'Cumulative Water (bbl)'),
        ('cumulative_condensate', 'Cumulative Condensate (bbl)')
    ]
    
    # Keep a complete list for x-axis options
    x_axis_attributes = [
        ('date', 'Date')
    ] + rate_attributes + cumulative_attributes
    
    # Get date range across all production data
    date_range = ProductionData.objects.aggregate(
        min_date=Min('date'),
        max_date=Max('date')
    )
    
    context = {
        'gas_fields': gas_fields,
        'rate_attributes': rate_attributes,
        'cumulative_attributes': cumulative_attributes,
        'x_axis_attributes': x_axis_attributes,
        'min_date': date_range['min_date'],
        'max_date': date_range['max_date']
    }
    return render(request, 'production/production_graph.html', context)


@login_required
def production_fields(request):
    """Show all gas fields as the entry point for production data exploration."""
    gas_fields = GasField.objects.all().order_by('name')
    return render(request, 'production/production_fields.html', {
        'gas_fields': gas_fields,
    })


@login_required
def production_field_detail(request, field_id):
    """Show details for a specific gas field and its wells.

    The page lists wells and provides links to per-well production graphs.
    """
    try:
        gas_field = GasField.objects.prefetch_related('wells').get(id=field_id)
    except GasField.DoesNotExist:
        messages.error(request, 'Gas field not found')
        return redirect('production_fields')

    # Simple aggregates for the field (min/max date across wells)
    prod_qs = ProductionData.objects.filter(well__gas_field=gas_field)
    date_range = prod_qs.aggregate(min_date=Min('date'), max_date=Max('date'))

    wells = gas_field.wells.all().order_by('name')

    # Compute field-level aggregates
    number_of_wells = wells.count()
    total_area = gas_field.total_area
    discovery_date = gas_field.discovery_date

    total_cumulative_flow = 0.0
    total_cumulative_water = 0.0
    total_cumulative_condensate = 0.0
    total_latest_flow_rate = 0.0

    for well in wells:
        latest = ProductionData.objects.filter(well=well).order_by('-date').first()
        if latest:
            # Prefer recorded cumulative fields when present
            try:
                cum_flow = float(latest.cumulative_flow_rate or 0)
            except Exception:
                cum_flow = 0.0
            total_cumulative_flow += cum_flow

            try:
                total_cumulative_water += float(latest.cumulative_water or 0)
            except Exception:
                # If cumulative_water isn't stored, try computing sum of water_production
                total_cumulative_water += ProductionData.objects.filter(well=well).aggregate(s=Sum('water_production'))['s'] or 0

            try:
                total_cumulative_condensate += float(latest.cumulative_condensate or 0)
            except Exception:
                total_cumulative_condensate += ProductionData.objects.filter(well=well).aggregate(s=Sum('condensate_production'))['s'] or 0

            try:
                total_latest_flow_rate += float(latest.flow_rate or 0)
            except Exception:
                total_latest_flow_rate += 0.0

    context = {
        'gas_field': gas_field,
        'wells': wells,
        'min_date': date_range['min_date'],
        'max_date': date_range['max_date'],
        'number_of_wells': number_of_wells,
        'total_area': total_area,
        'discovery_date': discovery_date,
        'total_cumulative_flow': total_cumulative_flow,
        'total_cumulative_water': total_cumulative_water,
        'total_cumulative_condensate': total_cumulative_condensate,
        'total_latest_flow_rate': total_latest_flow_rate,
    }

    return render(request, 'production/production_field_detail.html', context)


@login_required
def production_well_detail(request, well_id):
    """Show production graphs for a single well. The template will fetch JSON from the
    existing `get_well_data` endpoint and render charts client-side.
    """
    try:
        well = Well.objects.select_related('gas_field').get(id=well_id)
    except Well.DoesNotExist:
        messages.error(request, 'Well not found')
        return redirect('production_fields')

    # Provide a small context; the template uses AJAX to load time-series
    return render(request, 'production/production_well_detail.html', {
        'well': well,
    })

@login_required
def get_well_data(request):
    well_id = request.GET.get('well_id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    try:
        well = Well.objects.select_related('gas_field').get(id=well_id)
    except Well.DoesNotExist:
        return JsonResponse({'error': 'Well not found'}, status=404)
    
    query = ProductionData.objects.filter(well_id=well_id)
    
    if start_date:
        query = query.filter(date__gte=datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(date__lte=datetime.strptime(end_date, '%Y-%m-%d'))
    
    # Base production data
    production_data = query.values(
        'date', 'flow_rate', 'water_production', 'condensate_production'
    ).order_by('date')  # Ensure data is ordered by date
    
    # Convert QuerySet to list for manipulation
    data = list(production_data)
    
    # Calculate cumulative values
    cumulative_flow = 0
    cumulative_water = 0
    cumulative_condensate = 0
    
    for entry in data:
        # Update cumulative values
        cumulative_flow += entry['flow_rate'] if entry['flow_rate'] else 0
        cumulative_water += entry['water_production'] if entry['water_production'] else 0
        cumulative_condensate += entry['condensate_production'] if entry['condensate_production'] else 0
        
        # Add cumulative values to the entry
        entry['cumulative_flow_rate'] = round(cumulative_flow, 2)
        entry['cumulative_water'] = round(cumulative_water, 2)
        entry['cumulative_condensate'] = round(cumulative_condensate, 2)
        
        # Fix date format
        entry['date'] = entry['date'].strftime('%Y-%m-%d')
        
        # Add gas field information
        entry['gas_field'] = {
            'id': well.gas_field.id,
            'name': well.gas_field.name
        }
    
    return JsonResponse(data, safe=False)

# Optional: Add an endpoint to get wells for a specific gas field
@login_required
def get_field_wells(request):
    field_id = request.GET.get('field_id')
    
    try:
        gas_field = GasField.objects.get(id=field_id)
        wells = gas_field.wells.values('id', 'name')
        return JsonResponse(list(wells), safe=False)
    except GasField.DoesNotExist:
        return JsonResponse({'error': 'Gas field not found'}, status=404)

@login_required
def exploration_timeline(request):
    category_id = request.GET.get('category')
    if category_id and category_id != 'all':
        milestones = ExplorationTimeline.objects.filter(category_id=category_id).order_by('year')
    else:
        milestones = ExplorationTimeline.objects.all().order_by('year')
    
    categories = ExplorationCategory.objects.all()
    return render(request, 'visualization/production/exploration_timeline.html', {'milestones': milestones, 'categories': categories})


@login_required
def exploration_timeline_js(request):
    category_id = request.GET.get('category')
    if category_id and category_id != 'all':
        milestones = ExplorationTimeline.objects.filter(category_id=category_id).order_by('year')
    else:
        milestones = ExplorationTimeline.objects.all().order_by('year')
    
    categories = ExplorationCategory.objects.all()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Return JSON response for AJAX requests
        milestones_data = [
            {
                "year": milestone.year,
                "title": milestone.title,
                "description": milestone.description,
                "remarks": milestone.remarks,
                "category": milestone.category.name,
                "category_id": milestone.category.id
            }
            for milestone in milestones
        ]
        return JsonResponse({"milestones": milestones_data})
    
    return render(request, 'visualization/exploration_timejs.html', {
        'milestones': milestones, 
        'categories': categories,
    })


@login_required
def drilling_reports_index(request):
    """Show a list of wells. User clicks a well to navigate to its drilling reports page."""
    wells = Well.objects.all().order_by('name')
    return render(request, 'visualization/drilling_reports_index.html', {'wells': wells})


@login_required
def create_drilling_report(request):
    """Create a new DailyDrillingReport. Only superusers allowed."""
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to create drilling reports.')
        return redirect('drilling_reports_index')

    if request.method == 'POST':
        form = DailyDrillingReportForm(request.POST)
        if form.is_valid():
            report = form.save()
            messages.success(request, 'Drilling report created successfully.')
            # Redirect to the drilling reports listing for the selected well
            return redirect('drilling_reports', well_id=report.well.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = DailyDrillingReportForm()

    return render(request, 'visualization/drilling_reports_create.html', {
        'form': form,
    })


@login_required
def create_drilling_lithology(request):
    """Create a new DrillingLithology entry. Only superusers allowed."""
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to create drilling lithology entries.')
        return redirect('drilling_reports_index')

    initial = {}
    report_id = request.GET.get('report_id')
    if report_id:
        initial['drilling_report'] = report_id

    if request.method == 'POST':
        form = DrillingLithologyForm(request.POST)
        if form.is_valid():
            litho = form.save()
            messages.success(request, 'Drilling lithology saved successfully.')
            # Do not redirect — re-render the same form and show success message.
            # Pre-fill the form with the same drilling report so user can add another interval.
            try:
                initial = {'drilling_report': litho.drilling_report.id}
            except Exception:
                initial = {}
            form = DrillingLithologyForm(initial=initial)
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = DrillingLithologyForm(initial=initial)

    return render(request, 'visualization/drilling_lithology_create.html', {
        'form': form,
    })


@login_required
def upload_pdf_drilling_report(request):
    """Handle PDF upload for drilling report form population."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    if 'pdf_file' not in request.FILES:
        return JsonResponse({'error': 'No PDF file provided'}, status=400)
    
    pdf_file = request.FILES['pdf_file']
    
    # Validate file type
    if not pdf_file.name.lower().endswith('.pdf'):
        return JsonResponse({'error': 'File must be a PDF'}, status=400)
    
    try:
        # Extract text from PDF
        text = parse_pdf_text(pdf_file)
        
        # Extract data - pass filename for well name extraction
        filename = pdf_file.name if hasattr(pdf_file, 'name') else None
        extracted_data = extract_drilling_report_data(text, filename=filename)
        
        # Try to match well name to existing well
        well_id = None
        if 'well_name' in extracted_data:
            try:
                well = Well.objects.get(name__iexact=extracted_data['well_name'])
                well_id = well.id
                extracted_data['well'] = well_id
            except Well.DoesNotExist:
                # Try partial match
                wells = Well.objects.filter(name__icontains=extracted_data['well_name'])
                if wells.count() == 1:
                    well_id = wells.first().id
                    extracted_data['well'] = well_id
        
        return JsonResponse({
            'success': True,
            'data': extracted_data,
            'message': 'PDF parsed successfully'
        })
    except ImportError as e:
        return JsonResponse({
            'error': 'PDF parsing library not installed. Please install PyPDF2 or pdfplumber: pip install PyPDF2'
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'error': f'Error parsing PDF: {str(e)}'
        }, status=500)


@login_required
def upload_pdf_lithology(request):
    """Handle PDF upload for lithology form population."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    if 'pdf_file' not in request.FILES:
        return JsonResponse({'error': 'No PDF file provided'}, status=400)
    
    pdf_file = request.FILES['pdf_file']
    
    # Validate file type
    if not pdf_file.name.lower().endswith('.pdf'):
        return JsonResponse({'error': 'File must be a PDF'}, status=400)
    
    try:
        # Extract text from PDF
        text = parse_pdf_text(pdf_file)
        
        # Extract lithology data
        lithologies = extract_lithology_data(text)
        
        if lithologies:
            # Return all lithologies with metadata
            return JsonResponse({
                'success': True,
                'data': lithologies[0],  # Return first lithology interval for immediate population
                'all_lithologies': lithologies,  # Return all intervals
                'count': len(lithologies),
                'message': f'Found {len(lithologies)} lithology interval(s). Select an interval to populate the form.'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'No lithology data found in PDF. Please check the format.'
            })
    except ImportError as e:
        return JsonResponse({
            'error': 'PDF parsing library not installed. Please install PyPDF2 or pdfplumber: pip install PyPDF2'
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'error': f'Error parsing PDF: {str(e)}'
        }, status=500)

def calculate_drilling_efficiency(reports):
    """Calculate drilling efficiency based on daily progress and operational time"""
    total_depth_progress = 0
    total_time = 0
    
    for report in reports:
        daily_progress = report.depth_end - report.depth_start
        total_depth_progress += daily_progress
        total_time += 24 
        
    if total_time > 0:
        return round(total_depth_progress / total_time * 24, 2)
    return 0

@login_required
def drilling_reports(request, well_id=None):
    # Get filter parameters from request. Prefer the URL parameter `well_id` when provided.
    # Fallback to querystring 'well' for backward compatibility.
    if well_id is None:
        well_id = request.GET.get('well')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    depth_from = request.GET.get('depth_from')
    depth_to = request.GET.get('depth_to')
    
    # Start with all reports and apply filters
    reports = DailyDrillingReport.objects.select_related('well').all()
    
    if well_id:
        reports = reports.filter(well_id=well_id)
    if start_date:
        reports = reports.filter(date__gte=start_date)
    if end_date:
        reports = reports.filter(date__lte=end_date)
    if depth_from:
        reports = reports.filter(depth_start__gte=float(depth_from))
    if depth_to:
        reports = reports.filter(depth_end__lte=float(depth_to))
        
    # Order by date (newest first)
    reports = reports.order_by('-date', '-depth_start')
    
    # Get all wells for the filter dropdown
    wells = Well.objects.all()
    
    # Calculate statistics if a well is selected
    stats = None
    if well_id and reports.exists():
        latest_report = reports.first()
        earliest_report = reports.last()
        total_days = (latest_report.date - earliest_report.date).days or 1
        
        stats = {
            'total_reports': reports.count(),
            'depth_progress': latest_report.depth_end - earliest_report.depth_start,
            'latest_depth': latest_report.depth_end,
            'avg_progress_per_day': (latest_report.depth_end - earliest_report.depth_start) / total_days,
            'drilling_efficiency': calculate_drilling_efficiency(reports)
        }
    
    # Prepare report data with all necessary calculations
    processed_reports = []
    for report in reports.prefetch_related('lithologies'):
        # Process lithologies for this report
        lithologies = []
        for litho in report.lithologies.all():
            # Find dominant lithology based on percentages
            lithology_percentages = {
                'shale': litho.shale_percentage or 0,
                'sand': litho.sand_percentage or 0,
                'clay': litho.clay_percentage or 0,
                'slit': litho.slit_percentage or 0
            }
            # Find the dominant lithology (highest percentage)
            dominant_lithology = max(lithology_percentages, key=lithology_percentages.get)
            
            # Add prognosis comparison for this specific lithology interval
            prognosis_comparison, comparison_type = compare_lithology_with_prognosis(litho, report.well)
            
            lithologies.append({
                'depth_range': f"{litho.depth_from}-{litho.depth_to}m",
                'depth_from': litho.depth_from,
                'depth_to': litho.depth_to,
                'shale': round(litho.shale_percentage or 0, 1),
                'sand': round(litho.sand_percentage or 0, 1),
                'clay': round(litho.clay_percentage or 0, 1),
                'slit': round(litho.slit_percentage or 0, 1),
                'total': round((litho.shale_percentage or 0) + 
                             (litho.sand_percentage or 0) + 
                             (litho.clay_percentage or 0) + 
                             (litho.slit_percentage or 0), 1),
                'dominant_lithology': dominant_lithology,
                'dominant_percentage': round(lithology_percentages[dominant_lithology], 1),
                'prognosis_comparison': prognosis_comparison,
                'comparison_type': comparison_type,
                'description': litho.description
            })
        
        processed_reports.append({
            'id': report.id,
            'well_name': report.well.name,
            'report_no': report.report_no,
            'date': report.date.strftime('%d %b, %Y'),
            'date_iso': report.date.strftime('%Y-%m-%d'),  # Add ISO format for URL
            'depth_start': report.depth_start,
            'depth_end': report.depth_end,
            'depth_start_tvd': report.depth_start_tvd,
            'depth_end_tvd': report.depth_end_tvd,
            'current_operation': report.current_operation,
            'lithologies': lithologies,
            'gas_show': report.gas_show,
            'comments': report.comments,
            'present_activity': report.present_activity,
            'next_program': report.next_program,
            'daily_progress': report.depth_end - report.depth_start
        })
    
    # Get prognosis data for the selected well
    prognosis_data = None
    prognosis_segments = None
    prognosis_range = None
    if well_id:
        try:
            selected_well_obj = Well.objects.get(id=well_id)
            prognosis_data = selected_well_obj.prognoses.all()
            # Prepare prognosis segments for visualization (normalized widths)
            if prognosis_data.exists():
                # Convert Decimal to float and compute overall range
                starts = [float(p.planned_depth_start) for p in prognosis_data]
                ends = [float(p.planned_depth_end) for p in prognosis_data]
                min_depth = min(starts)
                max_depth = max(ends)
                total_range = max(max_depth - min_depth, 1e-6)
                zero_origin_total = max(max_depth, 1e-6)

                # Sort by start depth and build segments
                ordered = sorted(prognosis_data, key=lambda p: float(p.planned_depth_start))
                prognosis_segments = []
                for p in ordered:
                    start = float(p.planned_depth_start)
                    end = float(p.planned_depth_end)
                    length = max(end - start, 0)
                    width_pct = (length / total_range) * 100.0
                    height_pct = (length / zero_origin_total) * 100.0
                    prognosis_segments.append({
                        'from': round(start, 1),
                        'to': round(end, 1),
                        'lithology': p.lithology,
                        'is_target': p.target_depth,
                        'width_pct': width_pct,
                        'height_pct': height_pct,
                        'label': f"{round(start,1)}-{round(end,1)} m"
                    })

                prognosis_range = {
                    'min': round(min_depth, 1),
                    'max': round(max_depth, 1),
                    'top_spacer_pct': (min_depth / zero_origin_total) * 100.0 if max_depth > 0 else 0.0
                }
        except Well.DoesNotExist:
            prognosis_data = None

    context = {
        'reports': processed_reports,
        'wells': wells,
        'selected_well': str(well_id) if well_id else None,
        'start_date': start_date,
        'end_date': end_date,
        'depth_from': depth_from,
        'depth_to': depth_to,
        'stats': stats,
        'prognosis_data': prognosis_data,
        'prognosis_segments': prognosis_segments,
        'prognosis_range': prognosis_range,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'reports': processed_reports,
            'stats': stats
        })
    
    return render(request, 'visualization/drilling_reports.html', context)

@login_required
def generate_drilling_reports_pdf(request):
    """Generate HTML report of drilling reports for a well and specific date"""
    well_id = request.GET.get('well')
    report_date = request.GET.get('date')
    
    if not well_id or not report_date:
        return HttpResponse('Well ID and date are required', status=400)
    
    try:
        parsed_date = datetime.strptime(report_date, '%Y-%m-%d').date()
    except ValueError:
        return HttpResponse('Invalid date format. Use YYYY-MM-DD', status=400)

    report_obj = DailyDrillingReport.objects.select_related('well').filter(
        well_id=well_id,
        date=parsed_date
    ).prefetch_related('lithologies').first()
    
    if not report_obj:
        return HttpResponse('No report found for this well on the specified date', status=404)

    # Calculate days from spud
    days_from_spud = (parsed_date - report_obj.well.spud_date).days if report_obj.well.spud_date else 0
    
    # Calculate progress
    progress_md = report_obj.depth_end - report_obj.depth_start if report_obj.depth_end and report_obj.depth_start else 0
    progress_tvd = report_obj.depth_end_tvd - report_obj.depth_start_tvd if report_obj.depth_end_tvd and report_obj.depth_start_tvd else 0
    
    # Calculate midnight depth (you can adjust this logic as needed)
    midnight_depth = report_obj.depth_end - progress_md if report_obj.depth_end else 0
    
    # Process lithology data
    lithology_data = []
    for litho in report_obj.lithologies.all():
        depth_range = f"{int(litho.depth_from)}-{int(litho.depth_to)}"
        litho_items = []
        
        # Add Sand
        if litho.sand_percentage and litho.sand_percentage > 0:
            sand_desc = litho.description if hasattr(litho, 'description') and litho.description else (
                "Sand: Colorless to white, loose, transparent to translucent, sub-angular to "
                "sub-rounded, medium to fine grained, poorly sorted, predominantly quartz "
                "with some mica & dark color minerals, slightly reacts with HCl."
            )
            if sand_desc == "A/A":
                sand_desc = "A/A"
            
            litho_items.append({
                'type': 'Sand',
                'percentage': int(litho.sand_percentage),
                'description': sand_desc
            })
        
        # Add Silt
        if litho.slit_percentage and litho.slit_percentage > 0:
            silt_desc = "Silt: Milky white to white with dark spotted, highly reacts with HCL."
            if hasattr(litho, 'description') and litho.description == "A/A":
                silt_desc = "A/A"
            
            percentage_display = "Tr" if litho.slit_percentage < 5 else int(litho.slit_percentage)
            litho_items.append({
                'type': 'Silt',
                'percentage': percentage_display,
                'description': silt_desc
            })
        
        # Add Clay
        if litho.clay_percentage and litho.clay_percentage > 0:
            clay_desc = "Clay: Dark gray to gray in color, very soft, reacts with HCL in dry state."
            if hasattr(litho, 'description') and litho.description == "A/A":
                clay_desc = "A/A"
            
            litho_items.append({
                'type': 'Clay',
                'percentage': int(litho.clay_percentage),
                'description': clay_desc
            })
        
        # Add Shale
        if litho.shale_percentage and litho.shale_percentage > 0:
            shale_desc = "Grey to light grey in color, mostly amorphous with little sub blocky in shape, poorly laminated, very soft in wet condition. Reacts and dissolve in HCL."
            if hasattr(litho, 'description') and litho.description == "A/A":
                shale_desc = "A/A"
            
            litho_items.append({
                'type': 'Shale',
                'percentage': int(litho.shale_percentage),
                'description': shale_desc
            })
        
        if litho_items:
            lithology_data.append((depth_range, litho_items))
    
    # Paginate lithology data (e.g., 15 rows per page)
    rows_per_page = 15
    lithology_pages = []
    current_page = []
    current_row_count = 0
    
    for depth_range, litho_items in lithology_data:
        row_count = len(litho_items)
        if current_row_count + row_count > rows_per_page and current_page:
            lithology_pages.append(current_page)
            current_page = []
            current_row_count = 0
        
        current_page.append((depth_range, litho_items))
        current_row_count += row_count
    
    if current_page:
        lithology_pages.append(current_page)
    
    # If no lithology data, create at least one page
    if not lithology_pages:
        lithology_pages = [[]]
    
    context = {
        'report': report_obj,
        'days_from_spud': days_from_spud,
        'progress_md': progress_md,
        'progress_tvd': progress_tvd,
        'midnight_depth': midnight_depth,
        'lithology_pages': lithology_pages,
        'logo_path': 'images/bapex_logo.png',  # Update with actual logo path
    }
    
    return render(request, 'visualization/drilling_reports_pdf.html', context)