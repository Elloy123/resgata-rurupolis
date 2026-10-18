import re

from django import template

register = template.Library()


@register.filter
def apenas_digitos(valor):
    return re.sub(r'\D', '', valor or '')


@register.filter
def whatsapp_br(valor):
    """Número no formato do wa.me: só dígitos, com o DDI 55 do Brasil."""
    digitos = apenas_digitos(valor).lstrip('0')
    if not digitos:
        return ''
    if digitos.startswith('55') and len(digitos) >= 12:
        return digitos
    return f'55{digitos}'
