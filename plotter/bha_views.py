from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.template.loader import render_to_string
from .models import BHA, BHAComponent, BHAComponentPosition, DailyDrillingReport
from .forms import BHAForm, BHAComponentPositionForm
import json
from io import BytesIO
from xhtml2pdf import pisa
from django.http import HttpResponse

@login_required
def bha_list(request):
    """Display list of all BHAs"""
    bhas = BHA.objects.select_related('drilling_report', 'drilling_report__well').all()
    active_bhas_count = BHA.objects.filter(is_active=True).count()
    return render(request, 'plotter/bha/list.html', {
        'bhas': bhas,
        'active_bhas_count': active_bhas_count
    })

@login_required
def bha_detail(request, bha_id):
    """Display detailed view of a BHA with visualization"""
    bha = get_object_or_404(BHA.objects.select_related('drilling_report'), id=bha_id)
    components = list(bha.component_positions.select_related('component').order_by('position'))

    total_len = sum((pos.length or 0) for pos in components)

    component_data = []
    cumulative_length = 0
    for position in components:
        # stored value in DB is the distance from the top to the start of this component
        stored_from_top = (position.distance_from_bit or 0)
        length_val = (position.length or 0)

        # distance from bit to the start of this component
        distance_from_bit_display = None
        if total_len is not None:
            distance_from_bit_display = round(max(0.0, total_len - stored_from_top - length_val), 6)

        cumulative_length += length_val

        component_data.append({
            'component': position.component,
            'position': position.position,
            # expose corrected distance for template display
            'distance_from_bit': distance_from_bit_display,
            'cumulative_length': cumulative_length,
            'svg': position.render_svg(),
            'length': length_val,
            'outer_diameter': position.outer_diameter,
            'inner_diameter': position.inner_diameter,
            'weight': position.weight
        })

    context = {
        'bha': bha,
        'components': component_data,
        'total_length': total_len
    }
    return render(request, 'plotter/bha/detail.html', context)

@login_required
def bha_create(request):
    """Create a new BHA"""
    if request.method == 'POST':
        form = BHAForm(request.POST)
        if form.is_valid():
            bha = form.save()
            return redirect('bha_detail', bha_id=bha.id)
    else:
        form = BHAForm()
    
    return render(request, 'plotter/bha/form.html', {'form': form, 'title': 'Create New BHA'})

@login_required
def bha_edit(request, bha_id):
    """Edit existing BHA"""
    bha = get_object_or_404(BHA, id=bha_id)
    
    if request.method == 'POST':
        form = BHAForm(request.POST, instance=bha)
        if form.is_valid():
            form.save()
            return redirect('bha_detail', bha_id=bha.id)
    else:
        form = BHAForm(instance=bha)
    
    return render(request, 'plotter/bha/form.html', {
        'form': form,
        'bha': bha,
        'title': 'Edit BHA'
    })

@login_required
def bha_designer(request):
    """Interactive page to create a BHA and its component positions in one screen."""
    components = BHAComponent.objects.all().order_by('name')
    reports = DailyDrillingReport.objects.select_related('well').order_by('-date')

    if request.method == 'POST':
        # Create the BHA
        name = request.POST.get('bha_name')
        report_id = request.POST.get('report_id')
        if not (name and report_id):
            return JsonResponse({'success': False, 'error': 'Missing BHA name or report'}, status=400)

        report = get_object_or_404(DailyDrillingReport, id=report_id)
        bha = BHA.objects.create(name=name, drilling_report=report, notes=request.POST.get('bha_text', ''))

        # Parse row-wise posted arrays
        comp_ids = request.POST.getlist('row_component')
        singles = request.POST.getlist('row_singles')
        ods = request.POST.getlist('row_od')
        lengths = request.POST.getlist('row_length')
        weights = request.POST.getlist('row_weight')
        texts = request.POST.getlist('row_text')

        position_index = 1
        distance_from_bit = 0.0
        for i, comp_id in enumerate(comp_ids):
            if not comp_id:
                continue
            try:
                comp = BHAComponent.objects.get(id=int(comp_id))
            except (BHAComponent.DoesNotExist, ValueError):
                continue

            count = int(singles[i] or 1)
            for _ in range(max(1, count)):
                length_val = float(lengths[i] or 0)
                od_val = float(ods[i] or 0)
                weight_val = float(weights[i] or 0)

                BHAComponentPosition.objects.create(
                    bha=bha,
                    component=comp,
                    position=position_index,
                    distance_from_bit=distance_from_bit,
                    length=length_val,
                    outer_diameter=od_val,
                    inner_diameter=None,
                    weight=weight_val,
                )
                position_index += 1
                distance_from_bit += length_val

        bha.calculate_totals()

        return redirect('bha_detail', bha_id=bha.id)

    return render(request, 'plotter/bha/designer.html', {
        'components': components,
        'reports': reports,
    })

@login_required
def bha_edit_designer(request, bha_id):
    """Edit an existing BHA using the same grid experience as the designer page."""
    bha = get_object_or_404(BHA.objects.select_related('drilling_report'), id=bha_id)
    components = BHAComponent.objects.all().order_by('name')
    reports = DailyDrillingReport.objects.select_related('well').order_by('-date')

    if request.method == 'POST':
        # Update high-level BHA fields
        bha.name = request.POST.get('bha_name') or bha.name
        new_report_id = request.POST.get('report_id')
        if new_report_id:
            bha.drilling_report = get_object_or_404(DailyDrillingReport, id=new_report_id)
        bha.notes = request.POST.get('bha_text', bha.notes)
        bha.save()

        # Replace component positions with new submission
        bha.component_positions.all().delete()

        comp_ids = request.POST.getlist('row_component')
        singles = request.POST.getlist('row_singles')
        ods = request.POST.getlist('row_od')
        lengths = request.POST.getlist('row_length')
        weights = request.POST.getlist('row_weight')

        position_index = 1
        distance_from_bit = 0.0
        for i, comp_id in enumerate(comp_ids):
            if not comp_id:
                continue
            try:
                comp = BHAComponent.objects.get(id=int(comp_id))
            except (BHAComponent.DoesNotExist, ValueError):
                continue

            count = int(singles[i] or 1)
            for _ in range(max(1, count)):
                length_val = float(lengths[i] or 0)
                od_val = float(ods[i] or 0)
                weight_val = float(weights[i] or 0)

                BHAComponentPosition.objects.create(
                    bha=bha,
                    component=comp,
                    position=position_index,
                    distance_from_bit=distance_from_bit,
                    length=length_val,
                    outer_diameter=od_val,
                    inner_diameter=None,
                    weight=weight_val,
                )
                position_index += 1
                distance_from_bit += length_val

        bha.calculate_totals()
        return redirect('bha_detail', bha_id=bha.id)

    # Prefill rows from existing positions
    rows = []
    for pos in bha.component_positions.select_related('component').order_by('position'):
        rows.append({
            'component_id': pos.component.id,
            'singles': 1,
            'od': pos.outer_diameter,
            'length': pos.length,
            'weight': pos.weight or '',
        })

    return render(request, 'plotter/bha/designer_edit.html', {
        'bha': bha,
        'components': components,
        'reports': reports,
        'rows': json.dumps(rows),
    })

@login_required
def add_component(request, bha_id):
    """Add a component to a BHA"""
    bha = get_object_or_404(BHA, id=bha_id)
    
    if request.method == 'POST':
        form = BHAComponentPositionForm(request.POST)
        if form.is_valid():
            component_position = form.save(commit=False)
            component_position.bha = bha
            component_position.save()
            
            # Recalculate BHA totals
            bha.calculate_totals()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'component_html': render_to_string(
                        'plotter/bha/component_row.html',
                        {'position': component_position}
                    )
                })
            return redirect('bha_detail', bha_id=bha.id)
    else:
        form = BHAComponentPositionForm()
    
    context = {
        'form': form,
        'bha': bha,
        'title': 'Add Component'
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'form_html': render_to_string('plotter/bha/component_form.html', context)
        })
    return render(request, 'plotter/bha/component_form.html', context)

@login_required
def validate_component_compatibility(request):
    """AJAX endpoint to validate component compatibility"""
    prev_component_id = request.GET.get('prev_component')
    next_component_id = request.GET.get('next_component')
    
    if not all([prev_component_id, next_component_id]):
        return JsonResponse({'valid': False, 'error': 'Missing component information'})
    
    try:
        prev_component = BHAComponent.objects.get(id=prev_component_id)
        next_component = BHAComponent.objects.get(id=next_component_id)
        # Optional: accept explicit diameters for per-position validation
        prev_od_param = request.GET.get('prev_od')
        next_od_param = request.GET.get('next_od')
        
        # Check connection compatibility
        if prev_component.connection_type != next_component.connection_type:
            return JsonResponse({
                'valid': False,
                'error': f'Connection type mismatch: {prev_component.connection_type} ≠ {next_component.connection_type}'
            })
        
        # Choose diameters: prefer provided per-position values
        try:
            prev_od = float(prev_od_param) if prev_od_param is not None else (getattr(prev_component, 'outer_diameter', 0) or 0)
            next_od = float(next_od_param) if next_od_param is not None else (getattr(next_component, 'outer_diameter', 0) or 0)
        except ValueError:
            return JsonResponse({'valid': False, 'error': 'Invalid diameter values provided'})

        # Check diameter compatibility (upper cannot be larger than lower)
        if prev_od < next_od:
            return JsonResponse({
                'valid': False,
                'error': 'Upper component diameter larger than lower component'
            })
        
        return JsonResponse({'valid': True})
        
    except BHAComponent.DoesNotExist:
        return JsonResponse({'valid': False, 'error': 'Component not found'})


@login_required
def bha_export_pdf(request, bha_id):
    """Export a BHA detail page (visual summary + components table) as a PDF."""
    bha = get_object_or_404(BHA.objects.select_related('drilling_report', 'drilling_report__well'), id=bha_id)
    positions = bha.component_positions.select_related('component').order_by('position')

    # Build rows for table
    rows = []
    cumulative_length = 0
    for pos in positions:
        cumulative_length += (pos.length or 0)
        rows.append({
            'position': pos.position,
            'name': pos.component.name,
            'type': pos.component.get_type_display(),
            'length': pos.length,
            'outer_diameter': pos.outer_diameter,
            'weight': pos.weight,
            'distance_from_bit': pos.distance_from_bit,
            'cumulative_length': cumulative_length,
        })

    context = {
        'bha': bha,
        'rows': rows,
        'total_length': bha.total_length,
        'total_weight': bha.total_weight,
    }

    html = render_to_string('plotter/bha/pdf.html', context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="bha_{bha.id}.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error generating PDF', status=500)
    return response