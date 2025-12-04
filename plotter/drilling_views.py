from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db.models import Min, Max, Sum, Avg, Count
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from .utils import compare_lithology_with_prognosis
import os
import importlib.util
from .models import (
    Well,
    DailyDrillingReport, WellPrognosis, DrillingLithology, GasShowMeasurement,
    WellSurveyStation, DrillingStats
)
from decimal import Decimal
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
def drilling_reports_index(request):
    """Show a list of wells. User clicks a well to navigate to its drilling reports page."""
    wells = Well.objects.all().order_by('name')
    return render(request, 'visualization/drilling_reports_index.html', {'wells': wells})


@login_required
def drilling_reports_list(request, well_id):
    """Show a list of drilling reports for a specific well."""
    # Get the well object
    well = get_object_or_404(Well, pk=well_id)
    
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    depth_from = request.GET.get('depth_from')
    depth_to = request.GET.get('depth_to')
    gas_show = request.GET.get('gas_show')
    
    # Start with reports for this well only
    reports_qs = DailyDrillingReport.objects.select_related('well').filter(well_id=well_id)
    
    # Apply date filters
    if start_date:
        reports_qs = reports_qs.filter(date__gte=start_date)
    if end_date:
        reports_qs = reports_qs.filter(date__lte=end_date)
    
    # Apply depth range filters
    if depth_from:
        try:
            depth_from_float = float(depth_from)
            reports_qs = reports_qs.filter(depth_end__gte=depth_from_float)
        except (ValueError, TypeError):
            pass
    if depth_to:
        try:
            depth_to_float = float(depth_to)
            reports_qs = reports_qs.filter(depth_start__lte=depth_to_float)
        except (ValueError, TypeError):
            pass
    
    # Apply gas show filter
    if gas_show == 'yes':
        reports_qs = reports_qs.filter(gas_show=True)
    elif gas_show == 'no':
        reports_qs = reports_qs.filter(gas_show=False)
    
    # Order by date (newest first)
    reports_qs = reports_qs.order_by('-date', '-depth_start')
    
    # Process reports for template
    reports = []
    for report in reports_qs:
        reports.append({
            'id': report.id,
            'well_id': report.well.id,
            'well_name': report.well.name,
            'report_no': report.report_no,
            'date': report.date.strftime('%d %b, %Y') if report.date else '—',
            'date_iso': report.date.strftime('%Y-%m-%d') if report.date else '',
            'depth_start': report.depth_start,
            'depth_end': report.depth_end,
            'depth_start_tvd': report.depth_start_tvd,
            'depth_end_tvd': report.depth_end_tvd,
            'present_activity': report.present_activity,
            'current_operation': report.current_operation,
            'gas_show': report.gas_show,
        })
    
    context = {
        'reports': reports,
        'well': well,
        'well_id': well_id,
        'start_date': start_date,
        'end_date': end_date,
        'depth_from': depth_from,
        'depth_to': depth_to,
        'gas_show': gas_show,
    }
    
    return render(request, 'visualization/drilling_reports.html', context)


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

            # Handle optional GasShowMeasurement rows submitted with the form
            try:
                row_count = int(request.POST.get('gas_show_row_count', '0') or 0)
            except ValueError:
                row_count = 0

            created_rows = 0
            for i in range(row_count):
                prefix = f'gas_show_{i}_'
                formation = request.POST.get(prefix + 'formation', '').strip()
                depth = request.POST.get(prefix + 'depth_m')

                # Skip completely empty rows
                if not formation and not depth:
                    continue

                try:
                    depth_val = float(depth) if depth not in (None, '',) else None
                except (TypeError, ValueError):
                    depth_val = None

                GasShowMeasurement.objects.create(
                    drilling_report=report,
                    formation=formation or '',
                    depth_m=depth_val or 0.0,
                    max_percent=request.POST.get(prefix + 'max_percent') or 0.0,
                    bg_percent=request.POST.get(prefix + 'bg_percent') or 0.0,
                    above_bg_percent=request.POST.get(prefix + 'above_bg_percent') or 0.0,
                    c1_percent=request.POST.get(prefix + 'c1_percent') or 0.0,
                    c2_percent=request.POST.get(prefix + 'c2_percent') or 0.0,
                    c3_percent=request.POST.get(prefix + 'c3_percent') or 0.0,
                    ic4_percent=request.POST.get(prefix + 'ic4_percent') or 0.0,
                    nc5_percent=request.POST.get(prefix + 'nc5_percent') or 0.0,
                    remarks=request.POST.get(prefix + 'remarks', '').strip() or None,
                )
                created_rows += 1

            # If any rows were created, make sure gas_show is flagged on the report
            if created_rows and not report.gas_show:
                report.gas_show = True
                report.save(update_fields=['gas_show'])

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


@login_required
def survey_tools(request):
    """Display survey tools page with upload and conversion forms."""
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to access survey tools.')
        return redirect('drilling_reports_index')
    
    wells = Well.objects.all().order_by('name')
    
    return render(request, 'daily_reports/survey_tools.html', {
        'wells': wells,
    })


@login_required
@require_POST
def upload_well_survey(request):
    """Upload a text-based directional survey and rebuild the well survey stations."""
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to upload surveys.')
        return redirect('survey_tools')

    well_id = request.POST.get('well')
    survey_file = request.FILES.get('survey_file')

    if not well_id or not survey_file:
        messages.error(request, 'Please select a well and a survey file.')
        return redirect('survey_tools')

    well = get_object_or_404(Well, id=well_id)

    try:
        text = survey_file.read().decode('utf-8', errors='ignore')
        well.import_survey_from_text(text)
        messages.success(request, f'Survey uploaded successfully for {well.name}')
    except Exception as exc:
        messages.error(request, f'Failed to import survey: {exc}')

    return redirect('survey_tools')


@login_required
@require_POST
def convert_depth(request):
    """Convert MD to TVD or vice versa using stored survey data."""
    well_id = request.POST.get('well_id')
    md_value = request.POST.get('md')
    tvd_value = request.POST.get('tvd')

    if not well_id:
        return JsonResponse({'error': 'Well is required.'}, status=400)

    well = get_object_or_404(Well, id=well_id)

    if md_value:
        try:
            md_val = float(md_value)
        except ValueError:
            return JsonResponse({'error': 'Invalid MD provided.'}, status=400)
        tvd = well.md_to_tvd(md_val)
        if tvd is None:
            return JsonResponse({'error': 'Survey data unavailable for this well.'}, status=400)
        return JsonResponse({'md': round(md_val, 3), 'tvd': round(tvd, 3)})

    if tvd_value:
        try:
            tvd_val = float(tvd_value)
        except ValueError:
            return JsonResponse({'error': 'Invalid TVD provided.'}, status=400)
        md = well.tvd_to_md(tvd_val)
        if md is None:
            return JsonResponse({'error': 'Survey data unavailable for this well.'}, status=400)
        return JsonResponse({'md': round(md, 3), 'tvd': round(tvd_val, 3)})

    return JsonResponse({'error': 'Provide either MD or TVD to convert.'}, status=400)


@login_required
@require_POST
def populate_prognosis_md(request):
    """Populate MD depth fields for all WellPrognosis entries of a specific well using TVD to MD conversion."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    well_id = request.POST.get('well_id')
    if not well_id:
        return JsonResponse({'error': 'Well ID is required.'}, status=400)
    
    well = get_object_or_404(Well, id=well_id)
    
    # Check if well has survey data
    if not well.survey_stations.exists():
        return JsonResponse({'error': 'Survey data not available for this well. Please upload survey data first.'}, status=400)
    
    try:
        prognoses = WellPrognosis.objects.filter(well=well)
        updated_count = 0
        errors = []
        
        for prognosis in prognoses:
            try:
                # Convert TVD start to MD
                if prognosis.planned_depth_start:
                    md_start = well.tvd_to_md(float(prognosis.planned_depth_start))
                    if md_start is not None:
                        prognosis.md_depth_start = Decimal(str(round(md_start, 2)))
                
                # Convert TVD end to MD
                if prognosis.planned_depth_end:
                    md_end = well.tvd_to_md(float(prognosis.planned_depth_end))
                    if md_end is not None:
                        prognosis.md_depth_end = Decimal(str(round(md_end, 2)))
                
                prognosis.save(update_fields=['md_depth_start', 'md_depth_end'])
                updated_count += 1
            except Exception as e:
                errors.append(f"Error updating prognosis {prognosis.id}: {str(e)}")
        
        if errors:
            return JsonResponse({
                'success': True,
                'updated_count': updated_count,
                'total_count': prognoses.count(),
                'warnings': errors,
                'message': f'Updated {updated_count} of {prognoses.count()} prognosis entries. Some errors occurred.'
            })
        else:
            return JsonResponse({
                'success': True,
                'updated_count': updated_count,
                'total_count': prognoses.count(),
                'message': f'Successfully updated MD depths for {updated_count} prognosis entries.'
            })
    except Exception as e:
        return JsonResponse({'error': f'Failed to populate MD depths: {str(e)}'}, status=500)


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

    filtered_reports = reports
        
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
        
        # Get latest drilling stats for this well
        latest_drilling_stats = None
        try:
            latest_drilling_stats = DrillingStats.objects.filter(well_id=well_id).order_by('-id').first()
        except Exception:
            pass
        
        # Prepare stats with drilling stats data
        stats = {
            'total_reports': reports.count(),
            'latest_depth': latest_report.depth_end,
            'drilling_efficiency': calculate_drilling_efficiency(reports),
        }
        
        # Add drilling stats if available
        if latest_drilling_stats:
            stats['rop_latest'] = latest_drilling_stats.rop_latest
            stats['mud_weight_latest'] = latest_drilling_stats.mud_weight_latest
            if latest_drilling_stats.present_event:
                stats['present_event'] = latest_drilling_stats.get_present_event_display()
            if latest_drilling_stats.present_formation:
                stats['present_formation'] = latest_drilling_stats.get_present_formation_display()
    
    # Build gas show summary for the current report selection
    gas_show_summary = None
    gas_show_measurements_all = []
    report_ids = list(filtered_reports.values_list('id', flat=True))
    if report_ids:
        gas_measurements_qs = GasShowMeasurement.objects.filter(
            drilling_report_id__in=report_ids
        ).select_related('drilling_report__well')
        if gas_measurements_qs.exists():
            summary_data = gas_measurements_qs.aggregate(
                total_count=Count('id'),
                max_peak=Max('max_percent'),
                avg_above_bg=Avg('above_bg_percent')
            )
            latest_measurement = (
                gas_measurements_qs
                .select_related('drilling_report__well')
                .order_by('-drilling_report__date', '-start_depth_m')
                .first()
            )
            gas_show_summary = {
                'total_count': summary_data.get('total_count', 0),
                'max_peak': summary_data.get('max_peak'),
                'avg_above_bg': summary_data.get('avg_above_bg'),
                'latest': latest_measurement,
            }

            # Flatten all gas show measurements for modal display
            for gsm in gas_measurements_qs.order_by('drilling_report__date', 'start_depth_m'):
                gas_show_measurements_all.append({
                    'report_id': gsm.drilling_report_id,
                    'well_name': gsm.drilling_report.well.name,
                    'report_date': gsm.drilling_report.date,
                    'start_depth_m': gsm.start_depth_m,
                    'end_depth_m': gsm.end_depth_m,
                    'formation': gsm.formation,
                    'max_percent': gsm.max_percent,
                    'bg_percent': gsm.bg_percent,
                    'above_bg_percent': gsm.above_bg_percent,
                    'c1_percent': gsm.c1_percent,
                    'c2_percent': gsm.c2_percent,
                    'c3_percent': gsm.c3_percent,
                    'ic4_percent': gsm.ic4_percent,
                    'nc5_percent': gsm.nc5_percent,
                    'remarks': gsm.remarks,
                })
    
    # Prepare report data with all necessary calculations
    processed_reports = []
    for report in reports.prefetch_related('lithologies', 'gas_show_measurements'):
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
        
        gas_show_measurements = []
        for gsm in report.gas_show_measurements.all():
            gas_show_measurements.append({
                'formation': gsm.formation,
                'start_depth_m': gsm.start_depth_m,
                'end_depth_m': gsm.end_depth_m,
                'max_percent': gsm.max_percent,
                'bg_percent': gsm.bg_percent,
                'above_bg_percent': gsm.above_bg_percent,
                'c1_percent': gsm.c1_percent,
                'c2_percent': gsm.c2_percent,
                'c3_percent': gsm.c3_percent,
                'ic4_percent': gsm.ic4_percent,
                'nc5_percent': gsm.nc5_percent,
                'remarks': gsm.remarks,
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
            'gas_show': bool(report.gas_show or gas_show_measurements),
            'comments': report.comments,
            'present_activity': report.present_activity,
            'next_program': report.next_program,
            'daily_progress': report.depth_end - report.depth_start,
            'gas_show_measurements': gas_show_measurements,
            'gas_show_peak': max((gsm['max_percent'] for gsm in gas_show_measurements), default=None) if gas_show_measurements else None,
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
                # Use MD depths if available, convert TVD to MD if MD not available
                # This ensures alignment with lithology data which is in MD
                starts = []
                ends = []
                for p in prognosis_data:
                    # Prefer MD depth, convert TVD to MD if MD not available
                    start_md = None
                    if p.md_depth_start is not None:
                        start_md = float(p.md_depth_start)
                    elif p.planned_depth_start is not None and selected_well_obj.survey_stations.exists():
                        # Convert TVD to MD using survey data
                        start_md = selected_well_obj.tvd_to_md(float(p.planned_depth_start))
                    
                    if start_md is not None:
                        starts.append(start_md)
                    
                    end_md = None
                    if p.md_depth_end is not None:
                        end_md = float(p.md_depth_end)
                    elif p.planned_depth_end is not None and selected_well_obj.survey_stations.exists():
                        # Convert TVD to MD using survey data
                        end_md = selected_well_obj.tvd_to_md(float(p.planned_depth_end))
                    
                    if end_md is not None:
                        ends.append(end_md)
                
                if starts and ends:
                    min_depth = min(starts)
                    max_depth = max(ends)
                    total_range = max(max_depth - min_depth, 1e-6)
                    zero_origin_total = max(max_depth, 1e-6)

                    # Build segments - all in MD, with gap handling
                    raw_segments = []
                    for p in prognosis_data:
                        # Use MD depth if available, convert TVD to MD if needed
                        start = None
                        if p.md_depth_start is not None:
                            start = float(p.md_depth_start)
                        elif p.planned_depth_start is not None and selected_well_obj.survey_stations.exists():
                            start = selected_well_obj.tvd_to_md(float(p.planned_depth_start))
                        
                        if start is None:
                            continue  # Skip if no depth data or conversion failed
                        
                        end = None
                        if p.md_depth_end is not None:
                            end = float(p.md_depth_end)
                        elif p.planned_depth_end is not None and selected_well_obj.survey_stations.exists():
                            end = selected_well_obj.tvd_to_md(float(p.planned_depth_end))
                        
                        if end is None:
                            continue  # Skip if no depth data or conversion failed
                        
                        raw_segments.append({
                            'from': round(start, 1),
                            'to': round(end, 1),
                            'lithology': p.lithology,
                            'is_target': p.target_depth,
                        })
                    
                    # Sort segments by start depth
                    raw_segments.sort(key=lambda s: s['from'])
                    
                    # Build final segments with gap handling
                    prognosis_segments = []
                    current_depth = min_depth
                    
                    for seg in raw_segments:
                        start = seg['from']
                        end = seg['to']
                        
                        # If there's a gap before this segment, add a gap segment
                        if current_depth < start:
                            gap_length = start - current_depth
                            gap_height_pct = (gap_length / zero_origin_total) * 100.0
                            prognosis_segments.append({
                                'from': round(current_depth, 1),
                                'to': round(start, 1),
                                'lithology': 'unknown',
                                'is_gap': True,
                                'is_target': False,
                                'height_pct': gap_height_pct,
                                'label': f"{round(current_depth,1)}-{round(start,1)} m (No data)"
                            })
                        
                        # Add the actual segment
                        length = max(end - start, 0)
                        width_pct = (length / total_range) * 100.0
                        height_pct = (length / zero_origin_total) * 100.0
                        prognosis_segments.append({
                            'from': round(start, 1),
                            'to': round(end, 1),
                            'lithology': seg['lithology'],
                            'is_target': seg['is_target'],
                            'is_gap': False,
                            'width_pct': width_pct,
                            'height_pct': height_pct,
                            'label': f"{round(start,1)}-{round(end,1)} m"
                        })
                        
                        current_depth = max(current_depth, end)
                    
                    # Add gap at the end if needed
                    if current_depth < max_depth:
                        gap_length = max_depth - current_depth
                        gap_height_pct = (gap_length / zero_origin_total) * 100.0
                        prognosis_segments.append({
                            'from': round(current_depth, 1),
                            'to': round(max_depth, 1),
                            'lithology': 'unknown',
                            'is_gap': True,
                            'is_target': False,
                            'height_pct': gap_height_pct,
                            'label': f"{round(current_depth,1)}-{round(max_depth,1)} m (No data)"
                        })

                    if prognosis_segments:
                        prognosis_range = {
                            'min': round(min_depth, 1),
                            'max': round(max_depth, 1),
                            'top_spacer_pct': (min_depth / zero_origin_total) * 100.0 if max_depth > 0 else 0.0
                        }
        except Well.DoesNotExist:
            prognosis_data = None

    # Get well trajectory data (3D: MD, TVD, Northing, Easting) from survey stations
    trajectory_data = None
    latest_depth_point = None
    if well_id:
        try:
            selected_well_obj = Well.objects.get(id=well_id)
            survey_stations = selected_well_obj.survey_stations.all().order_by('md')
            if survey_stations.exists():
                trajectory_data = [
                    {
                        'md': float(station.md),
                        'tvd': float(station.tvd) if station.tvd is not None else float(station.md),
                        'northing': float(station.northing) if station.northing is not None else 0.0,
                        'easting': float(station.easting) if station.easting is not None else 0.0
                    }
                    for station in survey_stations
                ]
                
                # Calculate latest depth point if we have latest depth from reports
                if stats and stats.get('latest_depth'):
                    latest_md = float(stats['latest_depth'])
                    stations_list = list(survey_stations)
                    
                    # If latest MD is beyond last station, interpolate/extrapolate
                    if latest_md > stations_list[-1].md:
                        # Extrapolate using last two stations
                        if len(stations_list) >= 2:
                            last = stations_list[-1]
                            prev = stations_list[-2]
                            
                            # Calculate direction vector from previous to last station
                            delta_md = last.md - prev.md
                            if delta_md > 0:
                                ratio = (latest_md - last.md) / delta_md
                                
                                latest_depth_point = {
                                    'md': latest_md,
                                    'tvd': float(last.tvd) + ratio * (float(last.tvd) - float(prev.tvd)) if last.tvd and prev.tvd else latest_md,
                                    'northing': float(last.northing) + ratio * (float(last.northing) - float(prev.northing)) if last.northing and prev.northing else 0.0,
                                    'easting': float(last.easting) + ratio * (float(last.easting) - float(prev.easting)) if last.easting and prev.easting else 0.0
                                }
                            else:
                                # Use last station if can't extrapolate
                                latest_depth_point = {
                                    'md': latest_md,
                                    'tvd': float(last.tvd) if last.tvd is not None else latest_md,
                                    'northing': float(last.northing) if last.northing is not None else 0.0,
                                    'easting': float(last.easting) if last.easting is not None else 0.0
                                }
                        else:
                            # Only one station, use it
                            last = stations_list[0]
                            latest_depth_point = {
                                'md': latest_md,
                                'tvd': float(last.tvd) if last.tvd is not None else latest_md,
                                'northing': float(last.northing) if last.northing is not None else 0.0,
                                'easting': float(last.easting) if last.easting is not None else 0.0
                            }
                    else:
                        # Interpolate between stations
                        for idx in range(1, len(stations_list)):
                            current = stations_list[idx]
                            prev = stations_list[idx - 1]
                            if latest_md <= current.md:
                                if current.md == prev.md:
                                    latest_depth_point = {
                                        'md': latest_md,
                                        'tvd': float(current.tvd) if current.tvd is not None else latest_md,
                                        'northing': float(current.northing) if current.northing is not None else 0.0,
                                        'easting': float(current.easting) if current.easting is not None else 0.0
                                    }
                                else:
                                    ratio = (latest_md - prev.md) / (current.md - prev.md)
                                    latest_depth_point = {
                                        'md': latest_md,
                                        'tvd': float(prev.tvd or prev.md) + ratio * (float(current.tvd or current.md) - float(prev.tvd or prev.md)),
                                        'northing': float(prev.northing or 0.0) + ratio * (float(current.northing or 0.0) - float(prev.northing or 0.0)),
                                        'easting': float(prev.easting or 0.0) + ratio * (float(current.easting or 0.0) - float(prev.easting or 0.0))
                                    }
                                break
                        # If not found, use last station
                        if not latest_depth_point:
                            last = stations_list[-1]
                            latest_depth_point = {
                                'md': latest_md,
                                'tvd': float(last.tvd) if last.tvd is not None else latest_md,
                                'northing': float(last.northing) if last.northing is not None else 0.0,
                                'easting': float(last.easting) if last.easting is not None else 0.0
                            }
        except Well.DoesNotExist:
            trajectory_data = None

    # Get lithology data for the selected well - gather all lithology entries
    lithology_segments = None
    lithology_range = None
    if well_id:
        try:
            selected_well_obj = Well.objects.get(id=well_id)
            # Get all lithology entries for this well across all reports
            all_lithologies = DrillingLithology.objects.filter(
                drilling_report__well_id=well_id
            ).order_by('depth_from', 'depth_to')
            
            if all_lithologies.exists():
                # Convert to list and process
                lithology_list = list(all_lithologies)
                
                # Find overall depth range
                starts = [float(l.depth_from) for l in lithology_list]
                ends = [float(l.depth_to) for l in lithology_list]
                min_depth = min(starts) if starts else 0
                max_depth = max(ends) if ends else 0
                
                # Use latest depth from stats if available, otherwise use max from lithology
                if stats and stats.get('latest_depth'):
                    max_depth = max(max_depth, float(stats['latest_depth']))
                
                total_range = max(max_depth - min_depth, 1e-6)
                zero_origin_total = max(max_depth, 1e-6)
                
                # Build segments - handle gaps by creating empty segments
                lithology_segments = []
                current_depth = min_depth
                
                for litho in lithology_list:
                    start = float(litho.depth_from)
                    end = float(litho.depth_to)
                    
                    # If there's a gap before this lithology, add an empty segment
                    if current_depth < start:
                        gap_length = start - current_depth
                        gap_height_pct = (gap_length / zero_origin_total) * 100.0
                        lithology_segments.append({
                            'from': round(current_depth, 1),
                            'to': round(start, 1),
                            'lithology': 'unknown',
                            'is_gap': True,
                            'height_pct': gap_height_pct,
                            'label': f"{round(current_depth,1)}-{round(start,1)} m (No data)"
                        })
                    
                    # Get all lithology percentages
                    lithology_percentages = {
                        'sand': float(litho.sand_percentage or 0),
                        'clay': float(litho.clay_percentage or 0),
                        'shale': float(litho.shale_percentage or 0),
                        'slit': float(litho.slit_percentage or 0),
                        'coal': float(litho.coal_percentage or 0),
                        'limestone': float(litho.limestone_percentage or 0),
                    }
                    
                    # Calculate total percentage
                    total_pct = sum(lithology_percentages.values())
                    
                    # Only add segment if there's significant lithology data
                    if total_pct > 0:
                        length = max(end - start, 0)
                        segment_height_pct = (length / zero_origin_total) * 100.0
                        
                        # Create breakdown segments for each lithology type
                        # Order by percentage (highest first) for visual stacking
                        sorted_lithos = sorted(
                            [(k, v) for k, v in lithology_percentages.items() if v > 0],
                            key=lambda x: x[1],
                            reverse=True
                        )
                        
                        # Create a container segment with sub-segments
                        segment_data = {
                            'from': round(start, 1),
                            'to': round(end, 1),
                            'is_gap': False,
                            'height_pct': segment_height_pct,
                            'label': f"{round(start,1)}-{round(end,1)} m",
                            'breakdown': []
                        }
                        
                        # Add each lithology type as a sub-segment
                        for litho_type, pct in sorted_lithos:
                            if pct > 0:
                                segment_data['breakdown'].append({
                                    'type': litho_type,
                                    'percentage': round(pct, 1),
                                    'height_pct': (pct / total_pct) * 100.0 if total_pct > 0 else 0
                                })
                        
                        segment_data['percentages'] = {
                            'sand': round(lithology_percentages['sand'], 1),
                            'clay': round(lithology_percentages['clay'], 1),
                            'shale': round(lithology_percentages['shale'], 1),
                            'slit': round(lithology_percentages['slit'], 1),
                            'coal': round(lithology_percentages['coal'], 1),
                            'limestone': round(lithology_percentages['limestone'], 1),
                        }
                        
                        lithology_segments.append(segment_data)
                    
                    current_depth = max(current_depth, end)
                
                # Add gap at the end if needed
                if current_depth < max_depth:
                    gap_length = max_depth - current_depth
                    gap_height_pct = (gap_length / zero_origin_total) * 100.0
                    lithology_segments.append({
                        'from': round(current_depth, 1),
                        'to': round(max_depth, 1),
                        'lithology': 'unknown',
                        'is_gap': True,
                        'height_pct': gap_height_pct,
                        'label': f"{round(current_depth,1)}-{round(max_depth,1)} m (No data)"
                    })
                
                lithology_range = {
                    'min': round(min_depth, 1),
                    'max': round(max_depth, 1),
                    'top_spacer_pct': (min_depth / zero_origin_total) * 100.0 if max_depth > 0 else 0.0
                }
        except Well.DoesNotExist:
            lithology_segments = None

    # Calculate combined depth range for shared visualization
    combined_range = None
    if well_id:
        # Collect all depth ranges
        depth_mins = []
        depth_maxs = []
        
        if prognosis_range:
            depth_mins.append(prognosis_range['min'])
            depth_maxs.append(prognosis_range['max'])
        
        if lithology_range:
            depth_mins.append(lithology_range['min'])
            depth_maxs.append(lithology_range['max'])
        
        if stats and stats.get('latest_depth'):
            depth_maxs.append(float(stats['latest_depth']))
        
        if depth_mins and depth_maxs:
            combined_min = min(depth_mins)
            combined_max = max(depth_maxs)
            combined_total = max(combined_max, 1e-6)
            
            combined_range = {
                'min': round(combined_min, 1),
                'max': round(combined_max, 1),
                'top_spacer_pct': (combined_min / combined_total) * 100.0 if combined_max > 0 else 0.0
            }
            
            # Recalculate height percentages and positions for prognosis segments using combined range
            if prognosis_segments:
                # Sort segments by start depth to ensure proper ordering
                prognosis_segments.sort(key=lambda s: s['from'])
                prev_end = combined_min
                for seg in prognosis_segments:
                    start = seg['from']
                    end = seg['to']
                    length = max(end - start, 0)
                    
                    # Calculate height percentage based on length
                    seg['height_pct_combined'] = (length / combined_total) * 100.0
                    
                    # If there's a gap before this segment, we need to account for it
                    # The spacer at the top handles the offset from 0 to combined_min
                    # Any gaps between segments will be handled by the sequential stacking
                    if start > prev_end:
                        # There's a gap - this will create a visual gap in the chart
                        # We could add a gap segment here, but for now we'll let it be handled by spacing
                        pass
                    prev_end = max(prev_end, end)
            
            # Recalculate height percentages and positions for lithology segments using combined range
            if lithology_segments:
                # Lithology segments already include gap segments, so we just need to recalc heights
                for seg in lithology_segments:
                    start = seg['from']
                    end = seg['to']
                    length = max(end - start, 0)
                    seg['height_pct_combined'] = (length / combined_total) * 100.0

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
        'lithology_segments': lithology_segments,
        'lithology_range': lithology_range,
        'combined_range': combined_range,
        'gas_show_summary': gas_show_summary,
        'gas_show_measurements_all': gas_show_measurements_all,
        'trajectory_data': trajectory_data,
        'latest_depth': stats['latest_depth'] if stats else None,
        'latest_depth_point': latest_depth_point,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'reports': processed_reports,
            'stats': stats
        })
    
    return render(request, 'visualization/drilling_reports_dashboard.html', context)


@login_required
def gas_show_measurements_view(request, report_id):
    """Return structured GasShowMeasurement data for a specific drilling report."""
    report = get_object_or_404(
        DailyDrillingReport.objects.select_related('well').prefetch_related('gas_show_measurements'),
        pk=report_id
    )
    measurements = [{
        'formation': gsm.formation,
        'start_depth_m': gsm.start_depth_m,
        'end_depth_m': gsm.end_depth_m,
        'max_percent': gsm.max_percent,
        'bg_percent': gsm.bg_percent,
        'above_bg_percent': gsm.above_bg_percent,
        'c1_percent': gsm.c1_percent,
        'c2_percent': gsm.c2_percent,
        'c3_percent': gsm.c3_percent,
        'ic4_percent': gsm.ic4_percent,
        'nc5_percent': gsm.nc5_percent,
        'remarks': gsm.remarks,
    } for gsm in report.gas_show_measurements.all()]
    
    return JsonResponse({
        'report': {
            'id': report.id,
            'well': report.well.name,
            'date': report.date.strftime('%Y-%m-%d') if report.date else None,
        },
        'measurements': measurements,
        'has_measurements': bool(measurements),
    })


@login_required
def drilling_report_detail(request, report_id):
    """Return detailed view of a single drilling report."""
    report = get_object_or_404(
        DailyDrillingReport.objects.select_related('well').prefetch_related('lithologies', 'gas_show_measurements'),
        pk=report_id
    )
    
    # Process lithologies
    lithologies = []
    for litho in report.lithologies.all():
        lithology_percentages = {
            'shale': litho.shale_percentage or 0,
            'sand': litho.sand_percentage or 0,
            'clay': litho.clay_percentage or 0,
            'slit': litho.slit_percentage or 0
        }
        dominant_lithology = max(lithology_percentages, key=lithology_percentages.get)
        
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
    
    # Process gas show measurements
    gas_show_measurements = []
    for gsm in report.gas_show_measurements.all():
        gas_show_measurements.append({
            'formation': gsm.formation,
            'start_depth_m': gsm.start_depth_m,
            'end_depth_m': gsm.end_depth_m,
            'max_percent': gsm.max_percent,
            'bg_percent': gsm.bg_percent,
            'above_bg_percent': gsm.above_bg_percent,
            'c1_percent': gsm.c1_percent,
            'c2_percent': gsm.c2_percent,
            'c3_percent': gsm.c3_percent,
            'ic4_percent': gsm.ic4_percent,
            'nc5_percent': gsm.nc5_percent,
            'remarks': gsm.remarks,
        })
    
    processed_report = {
        'id': report.id,
        'well_id': report.well.id,
        'well_name': report.well.name,
        'report_no': report.report_no,
        'date': report.date.strftime('%d %b, %Y') if report.date else '—',
        'date_iso': report.date.strftime('%Y-%m-%d') if report.date else '',
        'depth_start': report.depth_start,
        'depth_end': report.depth_end,
        'depth_start_tvd': report.depth_start_tvd,
        'depth_end_tvd': report.depth_end_tvd,
        'current_operation': report.current_operation,
        'present_activity': report.present_activity,
        'next_program': report.next_program,
        'gas_show': report.gas_show,
        'comments': report.comments,
        'lithologies': lithologies,
        'gas_show_measurements': gas_show_measurements,
        'gas_show_peak': max((gsm['max_percent'] for gsm in gas_show_measurements), default=None) if gas_show_measurements else None,
        'daily_progress': report.depth_end - report.depth_start,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'report': processed_report})
    
    context = {
        'report': processed_report,
        'selected_well': str(report.well.id),
    }
    
    return render(request, 'visualization/drilling_report_detail.html', context)


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

