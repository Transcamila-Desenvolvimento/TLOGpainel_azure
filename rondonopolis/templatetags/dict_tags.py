# rondonopolis/templatetags/dict_tags.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter(name='is_equal')
def is_equal(value, arg):
    """Retorna True se str(value) == str(arg), usado para contornar problemas de sintaxe no template."""
    return str(value) == str(arg)