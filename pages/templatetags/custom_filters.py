from django import template

register = template.Library()

@register.filter
def index(sequence, position):
    try:
        return sequence[position]
    except IndexError:
        return None

@register.filter
def get_item(dictionary, key):
    try:
        return dictionary.get(key)
    except (TypeError, AttributeError):
        return None

@register.filter
def has_key(dict_obj, key):
    return key in dict_obj
