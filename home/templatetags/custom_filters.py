from django import template

register = template.Library()

@register.filter
def get_attr(obj, attr):
    """Gets the attribute of an object dynamically."""
    return getattr(obj, attr, '')

@register.filter
def replace_id(url, obj_id):
    """Replaces '0' in a URL with the actual object ID for dynamic URLs."""
    return url.replace('0', str(obj_id))

@register.filter
def format_field(value):
    """Change first_name to First Name"""
    return value.replace("_", " ").title()

@register.filter
def pluralize(value):
    """Simple pluralize filter: Adds 's' or 'ies' to a word."""
    if value.endswith("y"):
        return value[:-1] + "ies"
    elif value.endswith("s"):
        return value  # Already plural
    else:
        return value + "s"