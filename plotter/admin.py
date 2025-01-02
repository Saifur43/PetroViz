from django.contrib import admin
from .models import Core, WellData

class CoreAdmin(admin.ModelAdmin):
    list_display = ('core_no', 'get_well_name', 'image')  # Display core_no, well name, and image

    def get_well_name(self, obj):
        return obj.welldata_set.first().well_name if obj.welldata_set.exists() else 'No well'
    get_well_name.short_description = 'Well Name'  # Custom column header

class WellDataAdmin(admin.ModelAdmin):
    list_display = ('well_name', 'depth', 'core_no', 'porosity', 'perm_kair', 'resistivity')  # Example fields to display

# Register the models
admin.site.register(Core, CoreAdmin)
admin.site.register(WellData, WellDataAdmin)
