from django import template

register = template.Library()

@register.filter
def inr_to_eur(value):
    try:
        return round(value / 89)
    except:
        return value
