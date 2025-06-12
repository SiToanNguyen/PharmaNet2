# home/templatetags/custom_filters.py
from datetime import date, datetime
from django import template
from django.utils.dateformat import DateFormat

register = template.Library()

@register.filter
def get_attr(obj, attr_path):
    """
    Template filter to get nested attributes like 'product.manufacturer.name'
    """
    try:
        for attr in attr_path.split('.'):
            obj = getattr(obj, attr)
        return obj
    except (AttributeError, TypeError):
        return ''

@register.filter
def replace_id(url, obj_id):
    """
    Replaces '0' in a URL with the actual object ID for dynamic URLs.
    """
    return url.replace('0', str(obj_id))

@register.filter
def format_field(value):
    """
    Change first_name to First Name
    """
    return value.replace("_", " ").title()

@register.filter
def pluralize(value):
    """
    Simple pluralize filter: Adds 's' or 'ies' to a word.
    """
    if value.endswith("y"):
        return value[:-1] + "ies"
    elif value.endswith("s"):
        return value  # Already plural
    else:
        return value + "s"

@register.filter
def dict_get(d, key):
    """
    Template filter to safely get a value from a dictionary.
    """ 
    return d.get(key, None)

@register.filter
def uk_date(value):
    """
    Formats date/datetime as '22 June 1979'
    """
    if isinstance(value, (date, datetime)):
        return DateFormat(value).format('j F Y')
    return value