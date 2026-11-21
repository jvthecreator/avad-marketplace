from django import template

register = template.Library()

@register.filter
def mask_cpf(cpf):
    if cpf and len(cpf) >= 11:
        return f"***.***.{cpf[-6:-3]}-{cpf[-2:]}"
    return cpf

@register.filter
def stars_range(value):
    try:
        return range(int(value))
    except (ValueError, TypeError):
        return range(0)

@register.filter
def empty_stars_range(value):
    try:
        return range(5 - int(value))
    except (ValueError, TypeError):
        return range(5)

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def subtract(value, arg):
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def to_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0

@register.filter
def get_item(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None
