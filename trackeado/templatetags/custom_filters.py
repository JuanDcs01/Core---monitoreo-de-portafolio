from django import template

register = template.Library()

@register.filter
def holding_type(type):
    if type == 'EQUITY':
        return 'Acción'
    elif type == 'ETF':
        return 'ETF'
    elif type == 'CRYPTOCURRENCY':
        return 'Cripto'