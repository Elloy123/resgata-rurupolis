from decimal import Decimal

from django.db import models
from django.db.models import Q, Sum
from django.utils.functional import cached_property
from django.utils.text import slugify


class CampanhaQuerySet(models.QuerySet):
    def com_arrecadado(self):
        """Calcula o total arrecadado numa única consulta (evita N+1 nas listagens)."""
        return self.annotate(
            total_arrecadado=Sum('doacoes__valor', filter=Q(doacoes__status='aprovado'))
        )


class CampanhaDoacao(models.Model):
    titulo = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    descricao = models.TextField(blank=True)
    imagem = models.ImageField(upload_to='campanhas/', blank=True, null=True)
    meta_valor = models.DecimalField(max_digits=10, decimal_places=2)
    ativa = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    objects = CampanhaQuerySet.as_manager()

    class Meta:
        verbose_name = 'Campanha (vaquinha)'
        verbose_name_plural = 'Campanhas (vaquinhas)'
        ordering = ['-criado_em']

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.titulo)
            slug = base_slug
            i = 1
            while CampanhaDoacao.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f'{base_slug}-{i}'
            self.slug = slug
        super().save(*args, **kwargs)

    @cached_property
    def valor_arrecadado(self):
        if hasattr(self, 'total_arrecadado'):
            return self.total_arrecadado or Decimal('0.00')
        total = self.doacoes.filter(status='aprovado').aggregate(total=Sum('valor'))['total']
        return total or Decimal('0.00')

    @property
    def percentual_atingido(self):
        if not self.meta_valor:
            return 0
        pct = (self.valor_arrecadado / self.meta_valor) * 100
        return min(round(pct), 100)


class Doacao(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
        ('cancelado', 'Cancelado'),
    ]

    campanha = models.ForeignKey(
        CampanhaDoacao, related_name='doacoes', on_delete=models.SET_NULL, null=True, blank=True,
        help_text='Deixe em branco para uma doação geral à ONG.',
    )
    nome_doador = models.CharField(max_length=150)
    email_doador = models.EmailField()
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    mercadopago_preference_id = models.CharField(max_length=100, blank=True)
    mercadopago_payment_id = models.CharField(max_length=100, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Doação'
        verbose_name_plural = 'Doações'
        ordering = ['-criado_em']

    def __str__(self):
        alvo = self.campanha.titulo if self.campanha else 'Doação geral'
        return f'{self.nome_doador} - R$ {self.valor} ({alvo})'
