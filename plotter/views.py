from django.shortcuts import render
from .models import WellData, Core, GrainSize, Mineralogy, Fossils
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Min, Max
from .models import GasField, Well, ProductionData
from datetime import datetime
from collections import defaultdict
from .models import ExplorationTimeline, ExplorationCategory, OperationActivity
from django.template.loader import get_template

def dashboard(request):
    # Get recent operation activities (limit to 10 most recent)
    recent_activities = OperationActivity.objects.filter(is_active=True)[:10]
    
    context = {
        'recent_activities': recent_activities,
    }
    return render(request, 'visualization/dashboard.html', context)

def credits(request):
    return render(request, 'visualization/credits.html')

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
    return render(request, 'visualization/production_graph.html', context)

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
def get_field_wells(request):
    field_id = request.GET.get('field_id')
    
    try:
        gas_field = GasField.objects.get(id=field_id)
        wells = gas_field.wells.values('id', 'name')
        return JsonResponse(list(wells), safe=False)
    except GasField.DoesNotExist:
        return JsonResponse({'error': 'Gas field not found'}, status=404)

def exploration_timeline(request):
    category_id = request.GET.get('category')
    if category_id and category_id != 'all':
        milestones = ExplorationTimeline.objects.filter(category_id=category_id).order_by('year')
    else:
        milestones = ExplorationTimeline.objects.all().order_by('year')
    
    categories = ExplorationCategory.objects.all()
    return render(request, 'visualization/exploration_timeline.html', {'milestones': milestones, 'categories': categories})



from django.http import JsonResponse

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
    
    # Make sure to add the template tag to the context
    template = get_template('visualization/exploration_timejs.html')
    
    return render(request, 'visualization/exploration_timejs.html', {
        'milestones': milestones, 
        'categories': categories,
    })