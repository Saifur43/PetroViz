from django.db import models
from django.core.exceptions import ValidationError


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