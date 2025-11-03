from django.core.management.base import BaseCommand
from plotter.models import Well, DailyDrillingReport
import json
from datetime import datetime

class Command(BaseCommand):
    help = 'Populate daily drilling reports from consolidated JSON'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to the consolidated JSON file')

    def handle(self, *args, **options):
        try:
            # Read JSON file
            with open(options['json_file'], 'r') as file:
                data = json.load(file)

            # Get or create well
            well_name = data.get('well_name')
            if not well_name:
                self.stdout.write(self.style.ERROR('Well name not found in JSON'))
                return

            well, created = Well.objects.get_or_create(name=well_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created new well: {well.name}'))

            reports_created = 0
            reports_skipped = 0

            # Process each report
            for report_entry in data.get('reports', []):
                report_data = report_entry.get('data', {})
                
                # Skip if no depth data (indicating no drilling activity)
                drilling_progress = report_data.get('drilling_progress', {})
                if drilling_progress.get('from_depth') is None or drilling_progress.get('to_depth') is None:
                    reports_skipped += 1
                    continue

                # Parse date from report
                try:
                    report_date = datetime.strptime(report_data['report_date'], '%d-%m-%Y').date()
                except (KeyError, ValueError):
                    self.stdout.write(self.style.WARNING(f'Invalid date format in report {report_data.get("report_number")}'))
                    continue

                # Create comment with available information
                comment_parts = []
                
                # Add drilling parameters if available
                drilling_params = report_data.get('drilling_parameters', {})
                if any(drilling_params.values()):
                    comment_parts.extend([
                        "Drilling Parameters:",
                        f"- WOB: {drilling_params.get('wob', 'N/A')}",
                        f"- RPM: {drilling_params.get('rpm', 'N/A')}"
                    ])

                # Add mud properties if available
                mud_props = report_data.get('mud_properties', {})
                if any(mud_props.values()):
                    comment_parts.extend([
                        "\nMud Properties:",
                        f"- Density In/Out: {mud_props.get('density_in', 'N/A')}/{mud_props.get('density_out', 'N/A')}",
                        f"- Viscosity In/Out: {mud_props.get('viscosity_in', 'N/A')}/{mud_props.get('viscosity_out', 'N/A')}"
                    ])

                # Add drilling breakdown if available
                breakdown = report_data.get('drilling_breakdown', {})
                if any(breakdown.values()):
                    comment_parts.extend([
                        "\nOperations Breakdown:",
                        f"- Actual Drilling: {breakdown.get('actual_drilling', 'N/A')}",
                        f"- Sliding: {breakdown.get('sliding', 'N/A')}",
                        f"- Reaming/Connection: {breakdown.get('reaming_connection', 'N/A')}"
                    ])

                # Add summary
                if report_data.get('summary'):
                    comment_parts.extend(["\nSummary:", report_data['summary']])

                # Create daily drilling report
                report = DailyDrillingReport.objects.create(
                    well=well,
                    date=report_date,
                    depth_start=drilling_progress['from_depth'],
                    depth_end=drilling_progress['to_depth'],
                    current_operation=report_data.get('html_output', ''),
                    comments='\n'.join(comment_parts) if comment_parts else None
                )

                reports_created += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created report #{report_data.get("report_number")} - {report_date}\n'
                        f'Depth: {report.depth_start}m to {report.depth_end}m\n'
                        f'Progress: {report.depth_end - report.depth_start}m'
                    )
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f'\nProcessing completed:\n'
                    f'- Reports created: {reports_created}\n'
                    f'- Reports skipped (no drilling): {reports_skipped}\n'
                    f'- Total reports processed: {reports_created + reports_skipped}'
                )
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))