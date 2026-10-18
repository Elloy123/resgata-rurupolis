from django import forms

from core.utils import ContatoForm

MAX_QUANTIDADE_POR_ITEM = 50


class EncomendaForm(ContatoForm):
    def __init__(self, *args, itens=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['observacao'].widget.attrs['placeholder'] = 'Ex: retiro às 12h, sem cebola'
        self.itens = list(itens)
        for item in self.itens:
            self.fields[self.nome_campo(item)] = forms.IntegerField(
                label=item.nome, min_value=0, max_value=MAX_QUANTIDADE_POR_ITEM, initial=0, required=False,
                widget=forms.NumberInput(attrs={
                    'class': 'form-control text-center qtd-item', 'data-preco': f'{item.preco:.2f}',
                    'aria-label': f'Quantidade de {item.nome}',
                }),
            )

    @staticmethod
    def nome_campo(item):
        return f'qtd_{item.pk}'

    def campos_contato(self):
        return [self[nome] for nome in ('nome', 'telefone', 'observacao')]

    def linhas_cardapio(self):
        return [(item, self[self.nome_campo(item)]) for item in self.itens]

    def quantidades(self):
        """Lista de (item, quantidade) com quantidade > 0. Só após is_valid()."""
        pares = [(item, self.cleaned_data.get(self.nome_campo(item)) or 0) for item in self.itens]
        return [(item, qtd) for item, qtd in pares if qtd > 0]

    def clean(self):
        cleaned = super().clean()
        if not self.errors and not self.quantidades():
            raise forms.ValidationError('Escolha a quantidade de pelo menos um item do cardápio.')
        return cleaned
