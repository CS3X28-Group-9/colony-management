from django import template

register = template.Library()


@register.filter
def get_item(d, key):
    return d.get(key, "")


@register.filter
def contains(iterable, item):
    """Check if an item is in an iterable."""
    if iterable is None:
        return False
    return item in iterable
