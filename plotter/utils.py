def compare_lithology_with_prognosis(lithology, well):
    """
    Compare drilling lithology with well prognosis data.
    Returns a tuple of (comparison_status, match_type)
    """
    # Use a relative import when possible, but fall back to absolute
    # import to avoid "attempted relative import with no known parent package"
    # which can occur in some runtime/import scenarios.
    try:
        from .models import WellPrognosis
    except Exception:
        from plotter.models import WellPrognosis
    
    # Get prognosis data for comparison
    prognosis = WellPrognosis.objects.filter(
        well=well,
        planned_depth_start__lte=lithology.depth_to,
        planned_depth_end__gte=lithology.depth_from
    ).first()
    
    if not prognosis:
        return "No prognosis data available", "info"
        
    # Determine actual formations based on percentages
    actual_formations = []
    if lithology.shale_percentage and lithology.shale_percentage >= 20:
        actual_formations.append('shale')
    if lithology.sand_percentage and lithology.sand_percentage >= 20:
        actual_formations.append('sand')
    if lithology.silt_percentage and lithology.silt_percentage >= 20:
        actual_formations.append('silt')
    if lithology.clay_percentage and lithology.clay_percentage >= 20:
        actual_formations.append('clay')
    
    # Compare with prognosis
    if prognosis.lithology in actual_formations:
        return (
            f"✅ Matches prognosis: {prognosis.lithology.title()}", 
            "success"
        )
    else:
        return (
            f"⚠️ Differs from prognosis: Expected {prognosis.lithology.title()}, " \
            f"found {', '.join(f.title() for f in actual_formations) or 'no significant formations'}", 
            "warning"
        )