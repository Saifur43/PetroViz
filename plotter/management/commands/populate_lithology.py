from django.core.management.base import BaseCommand
from plotter.models import Well, DailyDrillingReport, DrillingLithology
import json
from datetime import datetime

class Command(BaseCommand):
    help = 'Populate drilling lithology data from JSON'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to the JSON file')
        parser.add_argument('well_name', type=str, help='Name of the well')
        parser.add_argument('report_date', type=str, help='Report date (YYYY-MM-DD)')

    def handle(self, *args, **options):
        try:
            # Read JSON file
            with open(options['json_file'], 'r') as file:
                data = json.load(file)

            # Get well
            try:
                well = Well.objects.get(name=options['well_name'])
            except Well.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Well {options["well_name"]} does not exist')
                )
                return

            # Get the drilling report for this date
            try:
                report_date = datetime.strptime(options['report_date'], '%Y-%m-%d').date()
                report = DailyDrillingReport.objects.get(
                    well=well,
                    date=report_date
                )
            except DailyDrillingReport.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        f'No drilling report found for well {well.name} on {report_date}'
                    )
                )
                return

            # Process lithology data
            lithology_data = data.get('lithology_data', [])
            created_count = 0

            for litho in lithology_data:
                depth_start = float(litho['depth_start_m'])
                depth_end = float(litho['depth_end_m'])
                
                # Initialize percentages dictionary
                percentages = {
                    'shale': 0,
                    'sand': 0,
                    'clay': 0,
                    'slit': 0  # Note: 'slit' is used as per your model
                }
                
                # Combine descriptions for all lithologies at this depth
                descriptions = []

                # Process each lithology composition
                for composition in litho['lithology']:
                    litho_type = composition['type'].lower()
                    
                    # Handle percentage conversion
                    if isinstance(composition['percentage'], (int, float)):
                        percentage = float(composition['percentage'])
                    elif composition['percentage'] == 'Trace':
                        percentage = 1  # Assign a small value for trace amounts
                    else:
                        percentage = 0
                    
                    # Map the lithology type to the correct field
                    if litho_type in percentages:
                        percentages[litho_type] = percentage
                    
                    # Add description if available
                    if composition.get('description'):
                        descriptions.append(f"{litho_type.capitalize()}: {composition['description']}")

                # Create lithology entry
                lithology = DrillingLithology.objects.create(
                    drilling_report=report,
                    depth_from=depth_start,
                    depth_to=depth_end,
                    shale_percentage=percentages['shale'],
                    sand_percentage=percentages['sand'],
                    clay_percentage=percentages['clay'],
                    slit_percentage=percentages['slit'],
                    description='\n\n'.join(descriptions) if descriptions else None
                )
                
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created lithology entry for depth {depth_start}-{depth_end}m'
                    )
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created {created_count} lithology entries'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            )