from django.db import models


class Core(models.Model):
    core_no = models.IntegerField()
    well_name = models.CharField(max_length=100)  # Associate with a specific well
    image = models.ImageField(upload_to='core_images/', null=True, blank=True)

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

    def __str__(self):
        return f"{self.well_name} - Core {self.core_no}"
