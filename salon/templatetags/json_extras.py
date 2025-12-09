import json
from django import template

register = template.Library()

@register.filter
def json_loads(value):
    """Safely parse a JSON string into a Python object."""
    try:
        return json.loads(value)
    except Exception:
        return []
