from django import template
import humanize
from django.utils.safestring import mark_safe
from decimal import Decimal

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

@register.filter
def market_state(value):

    if value in ['POST', 'POSTPOST', 'PREPRE']:
        return mark_safe('<i class="b bi-moon-stars-fill text-primary"></i>')
    if value == 'PRE':
        return mark_safe('<i class="bi bi-brightness-alt-high-fill text-warning">')

    return ''

@register.filter
def round_number(value):

    return round(Decimal(value), 2)

@register.filter
def no_trailing_zeros(value):

    if Decimal(value) < 1e-15:
        return '0.00'

    value = str(value)

    int = value[:value.find('.')]
    decimal = value[value.find('.') + 1:][:16]

    for x in range(len(decimal) -1, -1, -1):

        if decimal[x] != '0':
            return int + '.' + decimal[:x + 1]

    return value
