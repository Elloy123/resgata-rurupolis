import uuid
from decimal import Decimal

from django.db import models
from django.db.models import Sum
from django.utils import timezone

from core.utils import formatar_reais, slug_unico


class EventoQuerySet(models.QuerySet):
    def proximos(self):
        """Eventos ativos de hoje em diante, do mais próximo para o mais distante."""
        hoje = timezone.localdate()
        return self.filter(ativo=True, data__gte=hoje).order_by('data', 'hora_inicio')


class Evento(models.Model):
    titulo = models.CharField(max_length=150, help_text='Ex: "Feijoada beneficente"')
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    descricao = models.TextField(blank=True)
    imagem = models.ImageField(upload_to='eventos/', blank=True, null=True)
    data = models.DateField()
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fim = models.TimeField(null=True, blank=True)
    local = models.CharField(max_length=255, blank=True, help_text='Ex: "Sede da ONG, Rua X, 123"')
    aceita_encomendas = models.BooleanField(
        default=True,
        help_text='Se marcado, o público pode encomendar os itens do cardápio pelo site antes do evento.',
    )
    ativo = models.BooleanField(default=True, help_text='Desmarque para esconder o evento do site.')
    criado_em = models.DateTimeField(auto_now_add=True)

    objects = EventoQuerySet.as_manager()

    class Meta:
        verbose_name = 'Evento'
        verbose_name_plural = 'Eventos'
        ordering = ['-data']

    def __str__(self):
        return f'{self.titulo} ({self.data:%d/%m/%Y})'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slug_unico(self, self.titulo)
        super().save(*args, **kwargs)

    @property
    def ja_passou(self):
        return self.data < timezone.localdate()

    @property
    def encomendas_abertas(self):
        return self.ativo and self.aceita_encomendas and not self.ja_passou


class ItemCardapio(models.Model):
    evento = models.ForeignKey(Evento, related_name='itens', on_delete=models.CASCADE)
    nome = models.CharField(max_length=120, help_text='Ex: "Marmita de feijoada"')
    descricao = models.CharField(max_length=255, blank=True)
    preco = models.DecimalField(max_digits=8, decimal_places=2)
    disponivel = models.BooleanField(default=True, help_text='Desmarque quando esgotar.')
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Item do cardápio'
        verbose_name_plural = 'Itens do cardápio'
        ordering = ['ordem', 'nome']

    def __str__(self):
        return f'{self.nome} - R$ {self.preco}'


class Encomenda(models.Model):
    STATUS_CHOICES = [
        ('nova', 'Nova'),
        ('confirmada', 'Confirmada'),
        ('entregue', 'Entregue / retirada'),
        ('cancelada', 'Cancelada'),
    ]

    codigo = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    evento = models.ForeignKey(Evento, related_name='encomendas', on_delete=models.CASCADE)
    nome = models.CharField(max_length=150)
    telefone = models.CharField(max_length=30)
    observacao = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='nova')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Encomenda'
        verbose_name_plural = 'Encomendas'
        ordering = ['-criado_em']

    def __str__(self):
        return f'Encomenda de {self.nome} - {self.evento.titulo}'

    @property
    def numero(self):
        return f'E{self.pk:04d}'

    @property
    def total(self):
        return sum((i.subtotal for i in self.itens.all()), Decimal('0.00'))

    def mensagem_whatsapp(self):
        linhas = [
            f'Olá! Fiz a encomenda {self.numero} pelo site para o evento "{self.evento.titulo}" '
            f'({self.evento.data:%d/%m/%Y}):',
        ]
        linhas += [f'- {i.quantidade}x {i.nome}' for i in self.itens.all()]
        linhas.append(f'Total: {formatar_reais(self.total)}')
        if self.observacao:
            linhas.append(f'Obs: {self.observacao}')
        linhas.append(f'Nome: {self.nome}')
        return '\n'.join(linhas)


class EncomendaItem(models.Model):
    encomenda = models.ForeignKey(Encomenda, related_name='itens', on_delete=models.CASCADE)
    item = models.ForeignKey(ItemCardapio, related_name='encomendados', on_delete=models.SET_NULL, null=True)
    # Nome e preço copiados no momento da encomenda, para não mudarem se o cardápio for editado
    nome = models.CharField(max_length=120)
    preco_unitario = models.DecimalField(max_digits=8, decimal_places=2)
    quantidade = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'Item da encomenda'
        verbose_name_plural = 'Itens da encomenda'

    def __str__(self):
        return f'{self.quantidade}x {self.nome}'

    @property
    def subtotal(self):
        return self.preco_unitario * self.quantidade


def resumo_encomendas(evento):
    """Quantidade total encomendada de cada item (sem as canceladas), para a cozinha."""
    return (
        EncomendaItem.objects.filter(encomenda__evento=evento)
        .exclude(encomenda__status='cancelada')
        .values('nome')
        .annotate(total=Sum('quantidade'))
        .order_by('nome')
    )
