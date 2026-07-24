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
    try:
        return str(float(value)).replace(',', '.')
    except (ValueError, TypeError):
        return value

@register.filter
def div(value, arg):
    try:
        return int(value) // int(arg)
    except (ValueError, ZeroDivisionError):
        return 0

# Telegram'ning avatar rang tizimidagi kabi — ismga qarab har doim bir xil
# (lekin turli odamlar uchun turlicha) gradient fon tanlaydi.
_AVATAR_GRADIENTS = [
    ('#FF885E', '#FF516A'),
    ('#FFCD6A', '#FFA85C'),
    ('#82B1FF', '#665FFF'),
    ('#A0DE7E', '#54CB68'),
    ('#53EDD6', '#28C9B7'),
    ('#72D5FD', '#2A9EF1'),
    ('#E0A2F3', '#D669ED'),
]

@register.filter
def avatar_gradient(name):
    name = (name or '').strip()
    idx = sum(ord(c) for c in name) % len(_AVATAR_GRADIENTS) if name else 0
    c1, c2 = _AVATAR_GRADIENTS[idx]
    return f'linear-gradient(135deg, {c1}, {c2})'
