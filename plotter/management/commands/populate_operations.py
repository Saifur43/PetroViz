from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from plotter.models import OperationActivity

class Command(BaseCommand):
    help = 'Populate sample operation activities'

    def handle(self, *args, **options):
        # Clear existing activities
        OperationActivity.objects.all().delete()
        
        # Sample activities data
        activities_data = [
            {
                'title': 'নোয়াখালীর বেগমগঞ্জ গ্যাসক্ষেত্রে নতুন গ্যাসের স্তর আবিষ্কার',
                'description': 'এখানে উত্তোলনযোগ্য গ্যাসের মজুত ১৮০ বিলিয়ন ঘনফুট (বিসিএফ)',
                'location': 'নোয়াখালী, বেগমগঞ্জ',
                'priority': 'high',
                'created_at': timezone.now() - timedelta(hours=2)
            },
            {
                'title': 'ভোলায় ইলিশা-১ গ্যাসকূপে সফল অনুসন্ধান',
                'description': 'এ কূপ থেকে দৈনিক ২০–২২ মিলিয়ন ঘনফুট গ্যাস উত্তোলন করা যাবে',
                'location': 'ভোলা',
                'priority': 'high',
                'created_at': timezone.now() - timedelta(hours=5)
            },
            {
                'title': 'Production Optimization Analysis Completed',
                'description': 'Comprehensive analysis of well performance across all active fields',
                'location': 'Multiple Fields',
                'priority': 'medium',
                'created_at': timezone.now() - timedelta(hours=8)
            },
            {
                'title': 'Equipment Maintenance Schedule Updated',
                'description': 'Annual maintenance schedule for drilling equipment has been updated',
                'location': 'Headquarters',
                'priority': 'low',
                'created_at': timezone.now() - timedelta(days=1)
            },
            {
                'title': 'Environmental Impact Assessment Started',
                'description': 'New environmental assessment for upcoming exploration projects',
                'location': 'Sylhet Division',
                'priority': 'medium',
                'created_at': timezone.now() - timedelta(days=2)
            },
            {
                'title': 'Seismic Survey Data Processing',
                'description': 'Processing of 3D seismic data from recent offshore surveys',
                'location': 'Bay of Bengal',
                'priority': 'high',
                'created_at': timezone.now() - timedelta(days=3)
            },
            {
                'title': 'New Drilling Contract Awarded',
                'description': 'Contract awarded for drilling 5 new exploration wells',
                'location': 'Comilla Basin',
                'priority': 'critical',
                'created_at': timezone.now() - timedelta(days=5)
            },
            {
                'title': 'Pipeline Inspection Completed',
                'description': 'Annual inspection of gas pipeline infrastructure completed successfully',
                'location': 'Ashuganj',
                'priority': 'medium',
                'created_at': timezone.now() - timedelta(days=7)
            }
        ]
        
        # Create operation activities
        for activity_data in activities_data:
            OperationActivity.objects.create(**activity_data)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {len(activities_data)} operation activities'
            )
        )