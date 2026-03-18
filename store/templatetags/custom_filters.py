from django import template

register = template.Library()

@register.filter
def startswith(value, arg):
    """Returns True if the value starts with the arg."""
    return str(value).startswith(str(arg))
