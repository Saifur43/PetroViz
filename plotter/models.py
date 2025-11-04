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
    report_no = models.IntegerField(max_length=255)
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
    gas_show = models.TextField(blank=True, null=True, help_text="Description of gas shows if any")
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


class DrillingLithology(models.Model):
    drilling_report = models.ForeignKey(DailyDrillingReport, on_delete=models.CASCADE, related_name='lithologies')
    depth_from = models.FloatField(help_text="Start depth in meters")
    depth_to = models.FloatField(help_text="End depth in meters")
    shale_percentage = models.FloatField(default=0, help_text="Percentage of shale")
    sand_percentage = models.FloatField(default=0, help_text="Percentage of sand")
    clay_percentage = models.FloatField(default=0, help_text="Percentage of clay")
    slit_percentage = models.FloatField(default=0, help_text="Percentage of slit")
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
    created_at = models.DateTimeField(auto_now_add=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    location = models.CharField(max_length=200, null=True, blank=True)
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