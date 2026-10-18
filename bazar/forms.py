from core.utils import ContatoForm


class FinalizarPedidoForm(ContatoForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['observacao'].widget.attrs['placeholder'] = 'Ex: prefiro retirar no sábado de manhã'
