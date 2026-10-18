from django.db import models

from animais.models import Animal


class Apadrinhamento(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente (aguardando confirmação de pagamento)'),
        ('ativo', 'Ativo'),
        ('suspenso', 'Suspenso (pagamento atrasado)'),
        ('cancelado', 'Cancelado'),
    ]

    animal = models.ForeignKey(Animal, related_name='apadrinhamentos', on_delete=models.CASCADE)
    nome_padrinho = models.CharField(max_length=150)
    email_padrinho = models.EmailField()
    telefone_padrinho = models.CharField(max_length=30, blank=True)
    valor_mensal = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    mercadopago_preapproval_id = models.CharField(max_length=100, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Apadrinhamento'
        verbose_name_plural = 'Apadrinhamentos'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.nome_padrinho} apadrinha {self.animal.nome} (R$ {self.valor_mensal}/mês)'
