from django.core.management.base import BaseCommand
from plotter.models import Core, WellData
import csv

class Command(BaseCommand):
    help = "Populate Core and WellData models from a CSV file."

    def handle(self, *args, **kwargs):
        CSV_FILE_PATH = r'C:\Users\RnD\Desktop\Petro\petro.csv'
        try:
            with open(CSV_FILE_PATH, 'r') as file:
                reader = csv.DictReader(file)
                success_count = 0
                error_count = 0
                errors = []

                for row in reader:
                    try:
                        well_name = row.get('Well Name', '').strip()
                        core_no = row.get('Core No', '').strip()
                        if not well_name or not core_no.isdigit():
                            raise ValueError(f"Invalid core data: well_name={well_name}, core_no={core_no}")
                        core_no = int(core_no)
                        core, _ = Core.objects.get_or_create(
                            well_name=well_name,
                            core_no=core_no,
                            defaults={'image': None}
                        )
                        WellData.objects.create(
                            well_name = well_name,
                            core=core,
                            core_no=core_no,
                            length=float(row.get('Length', 0) or 0),
                            depth=float(row.get('Depth', 0) or 0),
                            porosity=float(row.get('Porosity', 0) or 0),
                            perm_kair=float(row.get('Perm Kair(mD)', 0) or 0),
                            grain_density=float(row.get('Grain Density', 0) or 0),
                            resistivity=float(row.get('Resistivity', 0) or 0),
                        )
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        errors.append(f"Error processing row: {e}")

                self.stdout.write(f"Data import completed: {success_count} rows successfully imported, {error_count} errors.")
                for error in errors:
                    self.stderr.write(error)
        except FileNotFoundError:
            self.stderr.write("CSV file not found.")
