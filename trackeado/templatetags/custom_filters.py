from django import template
import humanize
from django.utils.safestring import mark_safe

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