from django import template
import humanize

register = template.Library()

@register.filter
def holding_type(type):
    if type == 'EQUITY':
        return 'Acción'
    elif type == 'ETF':
        return 'ETF'
    elif type == 'CRYPTOCURRENCY':
        return 'Cripto'

@register.filter
def recommendation(value):

    if value == 'strong_buy':
        return 'Compra fuerte'
    elif value == 'buy':
        return 'Compra'
    elif value == 'hold':
        return 'Mantener'
    elif value == 'sell':
        return 'Vender'
    elif value == 'strong_sell':
        return 'Venta fuerte'

@register.filter
def metric(data):

    return humanize.metric(data)