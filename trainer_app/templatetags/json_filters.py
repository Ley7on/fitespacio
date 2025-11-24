import json
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def jsonify(value):
    """Convierte un valor Python a JSON para usar en JavaScript"""
    return mark_safe(json.dumps(value))