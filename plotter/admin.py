from django.contrib import admin
from .models import Core, WellData, ExplorationCategory
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
import pandas as pd
from .models import Well, ProductionData, GasField, ExplorationTimeline, OperationActivity, Fossils, GrainSize, Mineralogy


class CoreAdmin(admin.ModelAdmin):
    list_display = ('core_no', 'get_well_name', 'image')  # Display core_no, well name, and image

    def get_well_name(self, obj):
        return obj.welldata_set.first().well_name if obj.welldata_set.exists() else 'No well'
    get_well_name.short_description = 'Well Name'  # Custom column header

class WellDataAdmin(admin.ModelAdmin):
    list_display = ('well_name', 'depth', 'core_no', 'porosity', 'perm_kair', 'resistivity')  # Example fields to display



class GasFieldAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'discovery_date', 'total_area', 'get_well_count', 'get_field_production']
    search_fields = ['name', 'location']
    
    def get_well_count(self, obj):
        return obj.wells.count()
    get_well_count.short_description = 'Number of Wells'
    
    def get_field_production(self, obj):
        total = sum(well.production_data.order_by('-date').first().cumulative_flow_rate 
                   for well in obj.wells.all() 
                   if well.production_data.exists())
        return f"{total:.2f}"
    get_field_production.short_description = 'Total Field Production'

class WellAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'gas_field', 'get_total_production']
    search_fields = ['name', 'location']
    list_filter = ['gas_field']
    change_list_template = 'admin/change_list.html'  # Custom template for adding upload button
    
    def get_total_production(self, obj):
        latest_data = obj.production_data.order_by('-date').first()
        return f"{latest_data.cumulative_flow_rate:.2f}" if latest_data else "0"
    get_total_production.short_description = 'Total Production'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-production-data/', self.upload_data_view, name='well_upload_production'),
        ]
        return custom_urls + urls
    
    def upload_data_view(self, request):
        if request.method == 'POST':
            try:
                excel_file = request.FILES['excel_file']
                df = pd.read_excel(excel_file)
                
                # Process the data
                for _, row in df.iterrows():
                    # Get or create gas field
                    gas_field_name = row.get('gas_field', 'Default Field')
                    gas_field, _ = GasField.objects.get_or_create(
                        name=gas_field_name,
                        defaults={'location': row.get('field_location', '')}
                    )
                    
                    # Get or create well with gas field
                    well, _ = Well.objects.get_or_create(
                        name=row['well_name'],
                        defaults={
                            'location': row.get('location', ''),
                            'gas_field': gas_field
                        }
                    )
                    
                    ProductionData.objects.update_or_create(
                        well=well,
                        date=row['date'],
                        defaults={
                            'flow_rate': row['flow_rate'],
                            'cumulative_flow_rate': row['cumulative_flow_rate'],
                            'water_production': row['water'],
                            'condensate_production': row['condensate']
                        }
                    )
                
                messages.success(request, 'Data uploaded successfully!')
                return redirect('..')
                
            except Exception as e:
                messages.error(request, f'Error uploading data: {str(e)}')
            
        return render(request, 'admin/upload_form.html')

class ProductionDataAdmin(admin.ModelAdmin):
    list_display = ['well', 'get_gas_field', 'date', 'flow_rate', 'cumulative_flow_rate', 
                   'water_production', 'condensate_production']
    list_filter = ['well__gas_field', 'well', 'date']
    search_fields = ['well__name', 'well__gas_field__name']
    
    def get_gas_field(self, obj):
        return obj.well.gas_field
    get_gas_field.short_description = 'Gas Field'
    get_gas_field.admin_order_field = 'well__gas_field'

# Register the models
admin.site.register(GasField, GasFieldAdmin)
admin.site.register(Well, WellAdmin)
admin.site.register(ProductionData, ProductionDataAdmin)
admin.site.register(Core, CoreAdmin)
admin.site.register(WellData, WellDataAdmin)
admin.site.register(ExplorationTimeline)
admin.site.register(ExplorationCategory)
admin.site.register(OperationActivity)
admin.site.register(Fossils)
admin.site.register(GrainSize)  
admin.site.register(Mineralogy)
