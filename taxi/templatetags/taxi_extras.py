from django import template

register = template.Library()

@register.filter
def getattr_bool(obj, attr):
    return bool(getattr(obj, attr, False))
