import uuid
from decimal import Decimal

from django.db import models

from core.utils import formatar_reais, slug_unico


class Produto(models.Model):
    CATEGORIA_CHOICES = [
        ('roupa', 'Roupas'),
        ('calcado', 'Calçados'),
        ('acessorio', 'Acessórios'),
        ('casa', 'Casa e decoração'),
        ('brinquedo', 'Brinquedos'),
        ('pet', 'Itens para pets'),
        ('artesanato', 'Artesanato'),
        ('outro', 'Outros'),
    ]

    nome = models.CharField(max_length=120)
    slug = models.SlugField(max_length=150, unique=True, blank=True)
    descricao = models.TextField(blank=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='outro')
    tamanho = models.CharField(max_length=30, blank=True, help_text='Ex: "M", "38", "Infantil 6 anos"')
    estado = models.CharField(max_length=60, blank=True, help_text='Ex: "Novo", "Seminovo", "Usado - bom estado"')
    preco = models.DecimalField('Preço', max_digits=8, decimal_places=2)
    foto = models.ImageField(upload_to='bazar/', blank=True, null=True)
    estoque = models.PositiveIntegerField(
        default=1,
        help_text='Quantas unidades existem. Use 1 para peças únicas. Desce sozinho quando alguém faz um pedido.',
    )
    ativo = models.BooleanField(default=True, help_text='Desmarque para esconder o produto do site.')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Produto do bazar'
        verbose_name_plural = 'Produtos do bazar'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.nome} - R$ {self.preco}'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slug_unico(self, self.nome)
        super().save(*args, **kwargs)

    @property
    def esgotado(self):
        return self.estoque == 0


class FotoProduto(models.Model):
    produto = models.ForeignKey(Produto, related_name='fotos_extras', on_delete=models.CASCADE)
    imagem = models.ImageField(upload_to='bazar/galeria/')

    class Meta:
        verbose_name = 'Foto extra'
        verbose_name_plural = 'Fotos extras'

    def __str__(self):
        return f'Foto de {self.produto.nome}'


class Pedido(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente (aguardando pagamento/retirada)'),
        ('concluido', 'Concluído (pago e retirado)'),
        ('cancelado', 'Cancelado (produtos voltam ao estoque)'),
    ]

    codigo = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    nome = models.CharField(max_length=150)
    telefone = models.CharField(max_length=30)
    observacao = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Pedido do bazar'
        verbose_name_plural = 'Pedidos do bazar'
        ordering = ['-criado_em']

    def __str__(self):
        return f'Pedido {self.numero} - {self.nome}'

    @property
    def numero(self):
        return f'B{self.pk:04d}'

    @property
    def total(self):
        return sum((i.subtotal for i in self.itens.all()), Decimal('0.00'))

    def mensagem_whatsapp(self):
        linhas = [f'Olá! Fiz o pedido {self.numero} no bazar do site:']
        linhas += [f'- {i.quantidade}x {i.nome} ({formatar_reais(i.subtotal)})' for i in self.itens.all()]
        linhas.append(f'Total: {formatar_reais(self.total)}')
        if self.observacao:
            linhas.append(f'Obs: {self.observacao}')
        linhas.append(f'Nome: {self.nome}')
        linhas.append('Como faço o pagamento e a retirada?')
        return '\n'.join(linhas)


class PedidoItem(models.Model):
    pedido = models.ForeignKey(Pedido, related_name='itens', on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, related_name='pedidos', on_delete=models.SET_NULL, null=True)
    # Nome e preço copiados no momento do pedido, para não mudarem se o produto for editado
    nome = models.CharField(max_length=120)
    preco_unitario = models.DecimalField(max_digits=8, decimal_places=2)
    quantidade = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'Item do pedido'
        verbose_name_plural = 'Itens do pedido'

    def __str__(self):
        return f'{self.quantidade}x {self.nome}'

    @property
    def subtotal(self):
        return self.preco_unitario * self.quantidade
