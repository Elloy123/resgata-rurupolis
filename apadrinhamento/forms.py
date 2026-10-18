from django import forms

from .models import Apadrinhamento

VALORES_SUGERIDOS = [30, 50, 100, 200]


class ApadrinhamentoForm(forms.ModelForm):
    valor_mensal = forms.DecimalField(
        min_value=10,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Ex: 50,00'}),
        label='Valor da contribuição mensal (R$)',
    )

    class Meta:
        model = Apadrinhamento
        fields = ['nome_padrinho', 'email_padrinho', 'telefone_padrinho', 'valor_mensal']
        labels = {
            'nome_padrinho': 'Seu nome',
            'email_padrinho': 'Seu e-mail',
            'telefone_padrinho': 'Seu telefone / WhatsApp',
        }
        widgets = {
            'nome_padrinho': forms.TextInput(attrs={'class': 'form-control'}),
            'email_padrinho': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone_padrinho': forms.TextInput(attrs={'class': 'form-control'}),
        }
