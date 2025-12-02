from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta


class Core(models.Model):
    core_no = models.IntegerField()
    well_name = models.CharField(max_length=100)  # Associate with a specific well
    image = models.ImageField(upload_to='core_images/', null=True, blank=True)
    litho_image = models.ImageField(upload_to='litho_images/', null=True, blank=True)

    class Meta:
        unique_together = ('well_name', 'core_no')  # Ensure unique core numbers per well

    def __str__(self):
        return f"{self.well_name} - Core {self.core_no}"

class WellData(models.Model):
    well_name = models.CharField(max_length=100)
    core = models.ForeignKey(Core, related_name='welldata_set', on_delete=models.CASCADE)
    core_no = models.IntegerField() 
    length = models.FloatField(null=True, blank=True)
    depth = models.FloatField(null=True, blank=True)
    porosity = models.FloatField(null=True, blank=True)
    perm_kair = models.FloatField(null=True, blank=True)
    grain_density = models.FloatField(null=True, blank=True)
    resistivity = models.FloatField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Petro Analysis'
        verbose_name_plural = 'Petro Analyses'

    def clean(self):
        if self.core_no != self.core.core_no:
            raise ValidationError("Core number in WellData must match the core number in Core.")

    def __str__(self):
        return f"{self.well_name} - Core {self.core_no}"


class GasField(models.Model):
    name = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=200, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    discovery_date = models.DateField(null=True, blank=True)
    total_area = models.FloatField(null=True, blank=True, help_text="Area in square kilometers")
    
    def __str__(self):
        return self.name
    
    def get_total_production(self):
        """Returns total gas production across all wells in the field"""
        return sum(
            well.production_data.aggregate(models.Sum('flow_rate'))['flow_rate__sum'] or 0
            for well in self.wells.all()
        )

class Well(models.Model):
    name = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=200, null=True, blank=True)
    type = models.CharField(max_length=200, null=True, blank=True)
    rig = models.CharField(max_length=200, null=True, blank=True)
    spud_date = models.DateField(null=True, blank=True)
    
    gas_field = models.ForeignKey(
        
        GasField,
        on_delete=models.CASCADE,
        related_name='wells'
    )
    
    def __str__(self):
        return self.name

class ProductionData(models.Model):
    well = models.ForeignKey(Well, on_delete=models.CASCADE, related_name='production_data')
    date = models.DateField()
    flow_rate = models.FloatField()
    cumulative_flow_rate = models.FloatField()
    water_production = models.FloatField()
    condensate_production = models.FloatField()
    
    class Meta:
        ordering = ['date']
        unique_together = ['well', 'date']
        
    def __str__(self):
        return f"{self.well.name} - {self.date}"

class ExplorationCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class ExplorationTimeline(models.Model):
    year = models.IntegerField()
    title = models.CharField(max_length=255)
    category = models.ForeignKey(ExplorationCategory, on_delete=models.CASCADE, related_name='timelines')
    description = models.TextField()
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.year} - {self.title}"

class DailyDrillingReport(models.Model):
    well = models.ForeignKey(Well, on_delete=models.CASCADE, related_name='drilling_reports')
    report_no = models.IntegerField(blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    depth_start = models.FloatField(help_text="start depth (MD) in meters")
    depth_end = models.FloatField(help_text="end depth (MD) in meters")
    depth_start_tvd = models.FloatField(help_text="start depth (TVD) in meters", blank=True, null=True)
    depth_end_tvd = models.FloatField(help_text="end depth (TVD) in meters", blank=True, null=True)
    current_operation = models.TextField(blank=True, null=True)
    present_activity = models.TextField(blank=True, null=True)
    csg = models.TextField(blank=True, null=True)
    last_csg = models.TextField(blank=True, null=True)
    next_program = models.TextField(blank=True, null=True)
    gas_show = models.BooleanField(default=False, help_text="Indicates if any gas show was observed during this report")
    comments = models.TextField(blank=True, null=True)
    
    @property
    def daily_progress(self):
        return self.depth_end - self.depth_start if self.depth_end and self.depth_start else None
    
    class Meta:
        ordering = ['date', 'depth_start']
        verbose_name = 'Daily Drilling Report'
        verbose_name_plural = 'Daily Drilling Reports'
        
    def __str__(self):
        return f"{self.well.name} - {self.date} ({self.depth_start}-{self.depth_end}m)"


class GasShowMeasurement(models.Model):
    drilling_report = models.ForeignKey(
        DailyDrillingReport,
        on_delete=models.CASCADE,
        related_name='gas_show_measurements',
    )
    formation = models.CharField(max_length=100, help_text="Formation where the gas show was observed")
    start_depth_m = models.FloatField(help_text="Start depth in meters")
    end_depth_m = models.FloatField(help_text="End depth in meters")
    max_percent = models.FloatField(help_text="Maximum gas percentage")
    bg_percent = models.FloatField(help_text="Background gas percentage")
    above_bg_percent = models.FloatField(help_text="Gas percentage above background")
    c1_percent = models.FloatField(help_text="Methane (C1) percentage")
    c2_percent = models.FloatField(help_text="Ethane (C2) percentage")
    c3_percent = models.FloatField(help_text="Propane (C3) percentage")
    ic4_percent = models.FloatField(help_text="Iso-butane (iC4) percentage")
    nc5_percent = models.FloatField(help_text="Normal pentane (nC5) percentage")
    remarks = models.TextField(blank=True, null=True, help_text="Additional notes for this gas show entry")

    class Meta:
        ordering = ['drilling_report', 'start_depth_m']
        verbose_name = 'Gas Show Measurement'
        verbose_name_plural = 'Gas Show Measurements'

    def __str__(self):
        return f"{self.drilling_report.well.name} - {self.formation} @ {self.start_depth_m}-{self.end_depth_m}m"


class DrillingLithology(models.Model):
    drilling_report = models.ForeignKey(DailyDrillingReport, on_delete=models.CASCADE, related_name='lithologies')
    depth_from = models.FloatField(help_text="Start depth in meters")
    depth_to = models.FloatField(help_text="End depth in meters")
    shale_percentage = models.FloatField(default=0, help_text="Percentage of shale")
    shale_description = models.CharField(max_length=200, blank=True, null=True, help_text="Description of shale type")
    sand_percentage = models.FloatField(default=0, help_text="Percentage of sand")
    sand_description = models.CharField(max_length=200, blank=True, null=True, help_text="Description of sand type")   
    clay_percentage = models.FloatField(default=0, help_text="Percentage of clay")
    clay_description = models.CharField(max_length=200, blank=True, null=True, help_text="Description of clay type")
    slit_percentage = models.FloatField(default=0, help_text="Percentage of slit")
    slit_description = models.CharField(max_length=200, blank=True, null=True, help_text="Description of slit type")
    coal_percentage = models.FloatField(default=0, help_text="Percentage of coal")
    coal_description = models.CharField(max_length=200, blank=True, null=True, help_text="Description of coal type")
    limestone_percentage = models.FloatField(default=0, help_text="Percentage of limestone")
    limestone_description = models.CharField(max_length=200, blank=True, null=True, help_text="Description of limestone type")
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['depth_from']
        verbose_name = 'Drilling Lithology'
        verbose_name_plural = 'Drilling Lithologies'
        
    def __str__(self):
        return f"{self.drilling_report.well.name} - {self.drilling_report.date} ({self.depth_from}-{self.depth_to}m)"
    
    def clean(self):
        total_percentage = (
            self.shale_percentage + 
            self.sand_percentage + 
            self.clay_percentage + 
            self.slit_percentage
        )
        if total_percentage > 100:
            raise ValidationError("Lithology percentages cannot exceed 100%")

class OperationActivity(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    location = models.CharField(max_length=200, null=True, blank=True)
    image = models.ImageField(upload_to='operation_images/', null=True, blank=True, help_text="Image related to the operation activity")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Operation Activity'
        verbose_name_plural = 'Operation Activities'
    
    def __str__(self):
        return f"{self.title} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def get_time_ago(self):
        """Returns a human-readable time difference"""
        
        now = timezone.now()
        diff = now - self.created_at
        
        if diff < timedelta(minutes=1):
            return "Just now"
        elif diff < timedelta(hours=1):
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif diff < timedelta(days=1):
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff < timedelta(days=30):
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        else:
            return self.created_at.strftime('%Y-%m-%d')


class GrainSize(models.Model):
    """Grain size analysis data connected to Core samples"""
    core = models.ForeignKey(Core, on_delete=models.CASCADE, related_name='grain_sizes')
    sampling_depth_start = models.FloatField(help_text="Start sampling depth in meters")
    sampling_depth_end = models.FloatField(help_text="End sampling depth in meters")
    lithology = models.CharField(max_length=100, help_text="Rock type or lithology description")
    gravel_percent = models.FloatField(null=True, blank=True, help_text="Gravel percentage")
    coarse_sand_percent = models.FloatField(null=True, blank=True, help_text="Coarse sand percentage")
    medium_sand_percent = models.FloatField(null=True, blank=True, help_text="Medium sand percentage")
    fine_sand_percent = models.FloatField(null=True, blank=True, help_text="Fine sand percentage")
    very_fine_sand_percent = models.FloatField(null=True, blank=True, help_text="Very fine sand percentage")
    silt_percent = models.FloatField(null=True, blank=True, help_text="Silt percentage")
    clay_percent = models.FloatField(null=True, blank=True, help_text="Clay percentage")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sampling_depth_start']
        unique_together = ['core', 'sampling_depth_start', 'sampling_depth_end']
        verbose_name = 'Grain Size Analysis'
        verbose_name_plural = 'Grain Size Analyses'
    
    def clean(self):
        """Validate that percentages don't exceed 100% total and depth range is valid"""
        if self.sampling_depth_start >= self.sampling_depth_end:
            raise ValidationError("Start depth must be less than end depth.")
            
        total_percent = sum(filter(None, [
            self.gravel_percent or 0,
            self.coarse_sand_percent or 0,
            self.medium_sand_percent or 0,
            self.fine_sand_percent or 0,
            self.very_fine_sand_percent or 0,
            self.silt_percent or 0,
            self.clay_percent or 0,
        ]))
        
        if total_percent > 100:
            raise ValidationError(f"Total percentages cannot exceed 100%. Current total: {total_percent}%")
    
    def __str__(self):
        return f"{self.core} - {self.sampling_depth_start}-{self.sampling_depth_end}m - {self.lithology}"
    
    @property
    def total_percentage(self):
        """Calculate total percentage of all grain size components"""
        return sum(filter(None, [
            self.gravel_percent or 0,
            self.coarse_sand_percent or 0,
            self.medium_sand_percent or 0,
            self.fine_sand_percent or 0,
            self.very_fine_sand_percent or 0,
            self.silt_percent or 0,
            self.clay_percent or 0,
        ]))

    @property
    def depth_midpoint(self):
        """Calculate midpoint of depth range"""
        return (self.sampling_depth_start + self.sampling_depth_end) / 2


class Mineralogy(models.Model):
    """Mineralogy analysis data connected to Core samples"""
    ANALYSIS_TYPE_CHOICES = [
        ('bulk', 'Bulk Mineralogy'),
        ('clay', 'Clay Mineralogy'),
    ]
    
    MINERAL_CHOICES = [
        # Common bulk minerals
        ('quartz', 'Quartz'),
        ('albite', 'Albite'),
        ('muscovite', 'Muscovite'),
        ('clinochlore', 'Clinochlore'),
        ('rutile', 'Rutile'),
        ('calcite', 'Calcite'),
        ('dolomite', 'Dolomite'),
        ('feldspar', 'Feldspar'),
        ('plagioclase', 'Plagioclase'),
        ('biotite', 'Biotite'),
        ('chlorite', 'Chlorite'),
        ('pyrite', 'Pyrite'),
        ('siderite', 'Siderite'),
        ('ankerite', 'Ankerite'),
        # Clay minerals
        ('kaolinite', 'Kaolinite'),
        ('illite', 'Illite'),
        ('smectite', 'Smectite'),
        ('montmorillonite', 'Montmorillonite'),
        ('vermiculite', 'Vermiculite'),
        ('glauconite', 'Glauconite'),
        ('other', 'Other'),
    ]
    
    core = models.ForeignKey(Core, on_delete=models.CASCADE, related_name='mineralogy_analyses')
    sampling_depth_start = models.FloatField(help_text="Start sampling depth in meters")
    sampling_depth_end = models.FloatField(help_text="End sampling depth in meters")
    analysis_type = models.CharField(max_length=10, choices=ANALYSIS_TYPE_CHOICES, help_text="Type of mineralogy analysis")
    mineral_name = models.CharField(max_length=50, choices=MINERAL_CHOICES, help_text="Name of the identified mineral")
    percentage = models.FloatField(null=True, blank=True, help_text="Percentage of this mineral in the sample")
    other_mineral_name = models.CharField(max_length=100, null=True, blank=True, help_text="Custom mineral name if 'other' is selected")
    analysis_method = models.CharField(max_length=100, null=True, blank=True, help_text="Analysis method used (e.g., XRD, XRF)")
    notes = models.TextField(null=True, blank=True, help_text="Additional notes about the mineral analysis")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sampling_depth_start', 'analysis_type', '-percentage']
        verbose_name = 'Mineralogy Analysis'
        verbose_name_plural = 'Mineralogy Analyses'
    
    def clean(self):
        """Validate mineral name for 'other' category and depth range"""
        if self.sampling_depth_start >= self.sampling_depth_end:
            raise ValidationError("Start depth must be less than end depth.")
            
        if self.mineral_name == 'other' and not self.other_mineral_name:
            raise ValidationError("Please specify the mineral name when 'Other' is selected.")
        
        if self.percentage and (self.percentage < 0 or self.percentage > 100):
            raise ValidationError("Percentage must be between 0 and 100.")
    
    def __str__(self):
        mineral_display = self.other_mineral_name if self.mineral_name == 'other' else self.get_mineral_name_display()
        return f"{self.core} - {self.sampling_depth_start}-{self.sampling_depth_end}m - {mineral_display} ({self.get_analysis_type_display()})"
    
    @property
    def display_mineral_name(self):
        """Return the appropriate mineral name for display"""
        return self.other_mineral_name if self.mineral_name == 'other' else self.get_mineral_name_display()

    @property
    def depth_midpoint(self):
        """Calculate midpoint of depth range"""
        return (self.sampling_depth_start + self.sampling_depth_end) / 2


class Fossils(models.Model):
    """Fossil data connected to Core samples"""
    FOSSIL_TYPE_CHOICES = [
        ('foraminifera', 'Foraminifera'),
        ('nannofossils', 'Nannofossils'),
        ('dinoflagellates', 'Dinoflagellates'),
        ('pollen_spores', 'Pollen & Spores'),
        ('ostracods', 'Ostracods'),
        ('radiolaria', 'Radiolaria'),
        ('diatoms', 'Diatoms'),
        ('mollusks', 'Mollusks'),
        ('brachiopods', 'Brachiopods'),
        ('echinoderms', 'Echinoderms'),
        ('trilobites', 'Trilobites'),
        ('corals', 'Corals'),
        ('bryozoans', 'Bryozoans'),
        ('plant_remains', 'Plant Remains'),
        ('trace_fossils', 'Trace Fossils'),
        ('other', 'Other'),
    ]
    
    ABUNDANCE_CHOICES = [
        ('absent', 'Absent'),
        ('rare', 'Rare'),
        ('few', 'Few'),
        ('common', 'Common'),
        ('abundant', 'Abundant'),
        ('very_abundant', 'Very Abundant'),
    ]
    
    PRESERVATION_CHOICES = [
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('moderate', 'Moderate'),
        ('poor', 'Poor'),
        ('very_poor', 'Very Poor'),
    ]
    
    core = models.ForeignKey(Core, on_delete=models.CASCADE, related_name='fossils')
    sampling_depth_start = models.FloatField(help_text="Start sampling depth in meters")
    sampling_depth_end = models.FloatField(help_text="End sampling depth in meters")
    fossil_type = models.CharField(max_length=20, choices=FOSSIL_TYPE_CHOICES, help_text="Type of fossil identified")
    species_name = models.CharField(max_length=200, null=True, blank=True, help_text="Scientific name of the species")
    abundance = models.CharField(max_length=15, choices=ABUNDANCE_CHOICES, default='absent', help_text="Relative abundance of the fossil")
    preservation = models.CharField(max_length=10, choices=PRESERVATION_CHOICES, null=True, blank=True, help_text="Quality of fossil preservation")
    age_indication = models.CharField(max_length=100, null=True, blank=True, help_text="Geological age indication (e.g., Miocene, Pliocene)")
    environmental_indication = models.CharField(max_length=200, null=True, blank=True, help_text="Paleoenvironmental indication")
    other_fossil_type = models.CharField(max_length=100, null=True, blank=True, help_text="Custom fossil type if 'other' is selected")
    notes = models.TextField(null=True, blank=True, help_text="Additional notes about the fossil")
    image = models.ImageField(upload_to='fossil_images/', null=True, blank=True, help_text="Image of the fossil")
    identified_by = models.CharField(max_length=100, null=True, blank=True, help_text="Name of the paleontologist who identified the fossil")
    identification_date = models.DateField(null=True, blank=True, help_text="Date of fossil identification")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sampling_depth_start', 'fossil_type']
        verbose_name = 'Fossil'
        verbose_name_plural = 'Fossils'
    
    def clean(self):
        """Validate fossil type for 'other' category and depth range"""
        if self.sampling_depth_start >= self.sampling_depth_end:
            raise ValidationError("Start depth must be less than end depth.")
            
        if self.fossil_type == 'other' and not self.other_fossil_type:
            raise ValidationError("Please specify the fossil type when 'Other' is selected.")
    
    def __str__(self):
        fossil_display = self.other_fossil_type if self.fossil_type == 'other' else self.get_fossil_type_display()
        species_info = f" - {self.species_name}" if self.species_name else ""
        return f"{self.core} - {self.sampling_depth_start}-{self.sampling_depth_end}m - {fossil_display}{species_info}"
    
    @property
    def display_fossil_type(self):
        """Return the appropriate fossil type for display"""
        return self.other_fossil_type if self.fossil_type == 'other' else self.get_fossil_type_display()

    @property
    def depth_midpoint(self):
        """Calculate midpoint of depth range"""
        return (self.sampling_depth_start + self.sampling_depth_end) / 2
    
    
class BHAComponent(models.Model):
    """Model for individual BHA components like bits, stabilizers, drill collars etc."""
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=50, choices=[
        ('bit', 'Drill Bit'),
        ('stabilizer', 'Stabilizer'),
        ('drill_collar', 'Drill Collar'),
        ('heavy_weight', 'Heavy Weight Drill Pipe'),
        ('drill_pipe', 'Drill Pipe'),
        ('jar', 'Jar'),
        ('mwd', 'MWD Tool'),
        ('motor', 'Downhole Motor'),
        ('reamer', 'Reamer'),
        ('cross_over', 'Cross-over Sub'),
        ('other', 'Other')
    ])
    connection_type = models.CharField(max_length=50, help_text="Type of thread connection", null=True, blank=True)
    svg_template = models.TextField(help_text="SVG template for component visualization")
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.type})"
        
    def get_scaled_svg(self, scale_factor=1.0):
        """
        Returns the SVG template with proper scaling applied.
        The SVG template should contain placeholders:
        - {length} - component length in meters
        - {outer_diameter} - outer diameter in inches
        - {inner_diameter} - inner diameter in inches
        - {scale_factor} - scaling factor for visualization
        """
        try:
            # Prefer per-position render via BHAComponentPosition.render_svg; fall back safely
            length = (getattr(self, 'length', 0) or 0) * scale_factor
            od_value = getattr(self, 'outer_diameter', 0)
            id_value = getattr(self, 'inner_diameter', 0)
            outer_diameter = (od_value or 0) * scale_factor
            inner_diameter = (id_value or 0) * scale_factor
            return self.svg_template.format(
                length=length,
                outer_diameter=outer_diameter,
                inner_diameter=inner_diameter,
                scale_factor=scale_factor
            )
        except (KeyError, ValueError) as e:
            return f'<text x="10" y="20" class="error">Error rendering SVG: {str(e)}</text>'
            
    def validate_connection_compatibility(self, other_component):
        """
        Validates if this component can be connected to another component.
        Returns (bool, str) tuple: (is_compatible, error_message)
        """
        if not other_component:
            return True, ""
            
        # Check connection types
        if self.connection_type != other_component.connection_type:
            return False, f"Connection type mismatch: {self.connection_type} ≠ {other_component.connection_type}"
            
        # Diameter checks are done at position level; if defaults exist, verify softly
        self_od = getattr(self, 'outer_diameter', None)
        other_od = getattr(other_component, 'outer_diameter', None)
        if self_od is not None and other_od is not None:
            if abs(self_od - other_od) > 0.5:  # 0.5 inch tolerance
                return False, f"Diameter mismatch: {self_od}\" ≠ {other_od}\""
            
        return True, ""

class BHA(models.Model):
    """Model for complete Bottom Hole Assembly configurations"""
    name = models.CharField(max_length=200)
    drilling_report = models.ForeignKey(DailyDrillingReport, on_delete=models.CASCADE, related_name='bha_configurations')
    components = models.ManyToManyField(BHAComponent, through='BHAComponentPosition')
    total_length = models.FloatField(help_text="Total length in meters", null=True, blank=True)
    total_weight = models.FloatField(help_text="Total weight in kg", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def calculate_totals(self):
        """Calculate total length and weight of the assembly using per-position values"""
        positions = self.component_positions.all().select_related('component')
        self.total_length = sum((pos.length or 0) for pos in positions)
        self.total_weight = sum((pos.weight or 0) for pos in positions)
        self.save()

    def __str__(self):
        return f"{self.name} - {self.drilling_report.well.name} ({self.drilling_report.date})"

class BHAComponentPosition(models.Model):
    """Through model to track position of components in a BHA"""
    bha = models.ForeignKey(BHA, on_delete=models.CASCADE, related_name='component_positions')
    component = models.ForeignKey(BHAComponent, on_delete=models.CASCADE)
    position = models.PositiveIntegerField(help_text="Position from bottom up (1 being the lowest)")
    distance_from_bit = models.FloatField(help_text="Distance from bit in meters")
    length = models.FloatField(help_text="Length in meters")
    outer_diameter = models.FloatField(help_text="Outer diameter in inches")
    inner_diameter = models.FloatField(help_text="Inner diameter in inches", null=True, blank=True)
    weight = models.FloatField(help_text="Weight in kg", null=True, blank=True)
    
    class Meta:
        ordering = ['position']
        unique_together = ['bha', 'position']

    def __str__(self):
        return f"{self.component.name} at position {self.position} in {self.bha.name}"

    def render_svg(self, scale_factor=1.0):
        """Render the component's SVG using this position's dimensions"""
        try:
            return self.component.svg_template.format(
                length=self.length * scale_factor,
                outer_diameter=self.outer_diameter * scale_factor,
                inner_diameter=(self.inner_diameter or 0) * scale_factor,
                scale_factor=scale_factor
            )
        except (KeyError, ValueError) as e:
            return f'<text x="10" y="20" class="error">Error rendering SVG: {str(e)}</text>'

class WellPrognosis(models.Model):
    
    FORMATION_CHOICES = [
        ('sand', 'sand'),
        ('lime', 'lime'),
        ('shale', 'shale'),
        ('slit', 'slit'),
        ('dolomite', 'dolomite'),
        ('coal', 'coal'),
        ('clay', 'clay'),
        # Add more formations as needed
    ]
    
    well = models.ForeignKey(Well, on_delete=models.CASCADE, related_name='prognoses')
    planned_depth_start = models.DecimalField(max_digits=10, decimal_places=2, help_text="Planned start depth (m)")
    planned_depth_end = models.DecimalField(max_digits=10, decimal_places=2, help_text="Planned end depth (m)")
    lithology = models.CharField(max_length=50, choices=FORMATION_CHOICES, help_text="Expected lithology at this depth")
    target_depth = models.BooleanField(default=False, help_text="Is this a target depth?")
    casing_size = models.CharField(max_length=50, blank=True, null=True)
    drilling_fluid = models.CharField(max_length=100, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['planned_depth_start']

    def __str__(self):
        return f"{self.well.name} - {self.planned_depth_start}m ({self.lithology})"