from django import forms

from .models import Doacao


class DoacaoForm(forms.ModelForm):
    valor = forms.DecimalField(
        min_value=1,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Ex: 50,00'}),
        label='Valor da doação (R$)',
    )

    class Meta:
        model = Doacao
        fields = ['nome_doador', 'email_doador', 'valor']
        labels = {
            'nome_doador': 'Seu nome',
            'email_doador': 'Seu e-mail',
        }
        widgets = {
            'nome_doador': forms.TextInput(attrs={'class': 'form-control'}),
            'email_doador': forms.EmailInput(attrs={'class': 'form-control'}),
        }
