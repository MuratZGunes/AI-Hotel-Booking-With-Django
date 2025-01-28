from django import template
from django.utils.dateformat import format
import locale

register = template.Library()

@register.filter
def turkce_tarih(value):
    try:
        locale.setlocale(locale.LC_TIME, 'tr_TR.UTF-8')
        return format(value, 'j F Y l H:i')
    except:
        return value 