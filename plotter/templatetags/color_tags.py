from django import template
import colorsys

register = template.Library()

@register.filter
def colorize(value):
    # Generate distinct colors using the new theme palette
    colors = [
        "#1353A3",  # Primary Blue
        "#CA7007",  # Secondary Orange
        "#257358",  # Tertiary Green
        "#0D4080",  # Darker Blue variant
        "#B85A06",  # Darker Orange variant
        "#1F5A47",  # Darker Green variant
        "#4A7BC8",  # Lighter Blue variant
        "#E8932A",  # Lighter Orange variant
        "#4A9B7A",  # Lighter Green variant
        "#2B4A7A"   # Deep Blue variant
    ]
    return colors[int(value) % len(colors)] 