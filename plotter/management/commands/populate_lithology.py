from django.core.management.base import BaseCommand
from plotter.models import Well, DailyDrillingReport, DrillingLithology
import json
from datetime import datetime
import re


def _safe_float(value, default=0.0):
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        # remove commas and non-numeric chars except dot and minus
        s = str(value).strip()
        s = s.replace(',', '')
        m = re.search(r"[-+]?[0-9]*\.?[0-9]+", s)
        return float(m.group(0)) if m else default
    except Exception:
        return default


class Command(BaseCommand):
    help = 'Populate drilling reports and lithology data for Srikail-5 well from all_reports_combined.json'

    def handle(self, *args, **options):
        json_file_path = 'plotter/management/commands/all_reports_combined.json'
        try:
            with open(json_file_path, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'JSON file not found: {json_file_path}'))
            return
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Invalid JSON file: {e}'))
            return

        well_name = 'Srikail-5'

        reports = data.get('reports', []) or []
        target_reports = [r for r in reports if r.get('well_name') == well_name]
        if not target_reports:
            self.stdout.write(self.style.ERROR(f'No data found in JSON for well: {well_name}'))
            return

        # Ensure well exists (do not attempt to create because Well requires a gas_field)
        try:
            well = Well.objects.get(name=well_name)
        except Well.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Well "{well_name}" does not exist in database. Create it first.'))
            return

        created_reports = 0
        created_lithologies = 0

        for rep in target_reports:
            meta = rep.get('report_metadata', {}) or {}
            # parse report date from report_metadata 'Report Date' if present
            report_date_str = meta.get('Report Date') or rep.get('report_date')
            report_date = None
            if report_date_str:
                for fmt in ('%d-%m-%Y', '%d-%m-%y', '%Y-%m-%d'):
                    try:
                        report_date = datetime.strptime(report_date_str.strip(), fmt).date()
                        break
                    except Exception:
                        continue

            # derive depths
            depth_start = _safe_float(meta.get('Previous Depth MD'))
            # prefer Present Depth MD as depth_end
            depth_end = _safe_float(meta.get('Present Depth MD')) or _safe_float(meta.get('Previous Depth MD'))

            # use source_file as an identifier if needed
            source_file = rep.get('source_file')

            # get or create report by well + date (prefer date) else use source_file to avoid duplicates
            report = None
            try:
                if report_date:
                    report, rep_created = DailyDrillingReport.objects.get_or_create(
                        well=well,
                        date=report_date,
                        defaults={
                            'report_no': None,
                            'depth_start': depth_start,
                            'depth_end': depth_end,
                            'depth_start_tvd': _safe_float(meta.get('Previous Depth TVD')),
                            'depth_end_tvd': _safe_float(meta.get('Present Depth TVD')),
                            'current_operation': meta.get('Next Program') or meta.get('current_operation', ''),
                            'present_activity': '',
                            'csg': meta.get('CSG') or meta.get('Csg') or '',
                            'last_csg': meta.get('Last CSG') or meta.get('Last Csg') or '',
                            'next_program': meta.get('Next Program') or '',
                            'gas_show': '',
                            'comments': f"Source: {source_file}" if source_file else ''
                        }
                    )
                else:
                    # no date -> try to match by source_file stored in comments
                    report_qs = DailyDrillingReport.objects.filter(well=well, comments__icontains=source_file) if source_file else DailyDrillingReport.objects.filter(well=well)
                    report = report_qs.first()
                    rep_created = False if report else False
                    if not report:
                        report = DailyDrillingReport.objects.create(
                            well=well,
                            date=None,
                            report_no=None,
                            depth_start=depth_start,
                            depth_end=depth_end,
                            comments=f"Source: {source_file}" if source_file else ''
                        )
                        rep_created = True

                if rep_created:
                    created_reports += 1
                    self.stdout.write(self.style.SUCCESS(f'Created report for {well_name} date={report.date} source={source_file}'))
                else:
                    self.stdout.write(f'Using existing report for {well_name} date={report.date} source={source_file}')

            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Failed to create/get report (source={source_file}): {e}'))
                continue

            # process lithology entries
            litho_list = rep.get('lithology_data', []) or []
            for lith_block in litho_list:
                try:
                    depth_from = _safe_float(lith_block.get('depth_start_m'))
                    depth_to = _safe_float(lith_block.get('depth_end_m'))

                    # compute percentage fields
                    pct_fields = {
                        'shale_percentage': 0.0,
                        'sand_percentage': 0.0,
                        'clay_percentage': 0.0,
                        'slit_percentage': 0.0,
                        'coal_percentage': 0.0,
                        'limestone_percentage': 0.0
                    }
                    descs = []

                    for comp in lith_block.get('lithology', []) or []:
                        t = (comp.get('type') or '').strip().lower()
                        raw_pct = comp.get('percentage')
                        if isinstance(raw_pct, str) and raw_pct.lower() == 'trace':
                            pct = 1.0
                        else:
                            try:
                                pct = float(raw_pct)
                            except Exception:
                                pct = 0.0

                        if 'sand' in t:
                            pct_fields['sand_percentage'] = pct
                        elif 'clay' in t:
                            pct_fields['clay_percentage'] = pct
                        elif 'silt' in t or 'slit' in t:
                            pct_fields['slit_percentage'] = pct
                        elif 'shale' in t:
                            pct_fields['shale_percentage'] = pct
                        elif 'coal' in t:
                            pct_fields['coal_percentage'] = pct
                        elif 'limestone' in t or 'lime' in t:
                            pct_fields['limestone_percentage'] = pct
                        else:
                            # unknown type, add to description
                            if t:
                                descs.append(f"{comp.get('type')}: {comp.get('description','')}")
                                continue

                        if comp.get('description'):
                            descs.append(f"{comp.get('type')}: {comp.get('description')}")

                    # build description string
                    description = '\n\n'.join(descs) if descs else ''

                    lith_defaults = {
                        **pct_fields,
                        'shale_description': '',
                        'sand_description': '',
                        'clay_description': '',
                        'slit_description': '',
                        'coal_description': '',
                        'limestone_description': '',
                        'description': description
                    }

                    lith_obj, lith_created = DrillingLithology.objects.get_or_create(
                        drilling_report=report,
                        depth_from=depth_from,
                        depth_to=depth_to,
                        defaults=lith_defaults
                    )
                    if lith_created:
                        created_lithologies += 1
                        self.stdout.write(self.style.SUCCESS(f'Created lithology {depth_from}-{depth_to}m'))
                    else:
                        self.stdout.write(f'Using existing lithology {depth_from}-{depth_to}m')

                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Error creating lithology: {e}'))
                    continue

        self.stdout.write(self.style.SUCCESS(f'Completed. Reports created: {created_reports}, Lithologies created: {created_lithologies}'))