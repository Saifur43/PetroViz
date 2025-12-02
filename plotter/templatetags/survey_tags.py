from django import template
from plotter.models import Well

register = template.Library()


@register.inclusion_tag('daily_reports/includes/survey_tools.html', takes_context=True)
def survey_tools(context):
    return {
        'wells': Well.objects.all().order_by('name'),
        'request': context.get('request'),
    }

