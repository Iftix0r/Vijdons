from django import template
from django.utils import timezone

register = template.Library()

@register.filter
def getattr_bool(obj, attr):
    return bool(getattr(obj, attr, False))

@register.simple_tag
def seconds_since(dt):
    if not dt:
        return 999999
    return int((timezone.now() - dt).total_seconds())

@register.filter
def floatdot(value):
    """Float ni har doim nuqta bilan qaytaradi (URL uchun)."""
    try:
        return str(float(value)).replace(',', '.')
    except (ValueError, TypeError):
        return value
    try:
        return int(value) // int(arg)
    except (ValueError, ZeroDivisionError):
        return 0
