import re

from django import forms
from django.utils.text import slugify


def slug_unico(instancia, texto):
    """Gera um slug a partir do texto, sem repetir o de outro registro do mesmo modelo."""
    base_slug = slugify(texto) or 'item'
    slug = base_slug
    i = 1
    modelo = type(instancia)
    while modelo.objects.filter(slug=slug).exclude(pk=instancia.pk).exists():
        i += 1
        slug = f'{base_slug}-{i}'
    return slug


def apenas_digitos(valor):
    return re.sub(r'\D', '', valor or '')


def formatar_reais(valor):
    """Decimal('1234.5') -> 'R$ 1.234,50' (para mensagens de texto, fora dos templates)."""
    texto = f'{valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'R$ {texto}'


class ContatoForm(forms.Form):
    """Nome + telefone/WhatsApp, usado nas encomendas de eventos e nos pedidos do bazar."""

    nome = forms.CharField(
        label='Seu nome', max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'name'}),
    )
    telefone = forms.CharField(
        label='Seu WhatsApp / telefone', max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'autocomplete': 'tel', 'inputmode': 'tel',
            'placeholder': '(93) 99999-0000',
        }),
    )
    observacao = forms.CharField(
        label='Observação (opcional)', max_length=255, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )

    def clean_telefone(self):
        valor = self.cleaned_data['telefone']
        if not 10 <= len(apenas_digitos(valor)) <= 13:
            raise forms.ValidationError('Informe um telefone com DDD, ex: (93) 99999-0000.')
        return valor.strip()
