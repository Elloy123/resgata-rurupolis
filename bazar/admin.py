from django.contrib import admin
from django.db import transaction
from django.utils.html import format_html

from .carrinho import devolver_ao_estoque
from .models import FotoProduto, Pedido, PedidoItem, Produto


class FotoProdutoInline(admin.TabularInline):
    model = FotoProduto
    extra = 1


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('miniatura', 'nome', 'categoria', 'tamanho', 'preco', 'estoque', 'ativo', 'criado_em')
    list_display_links = ('miniatura', 'nome')
    list_editable = ('preco', 'estoque', 'ativo')
    list_filter = ('ativo', 'categoria')
    search_fields = ('nome', 'descricao')
    prepopulated_fields = {'slug': ('nome',)}
    inlines = [FotoProdutoInline]
    fieldsets = (
        (None, {'fields': ('nome', 'slug', 'foto', 'preco', 'estoque', 'ativo')}),
        ('Detalhes', {'fields': ('categoria', 'tamanho', 'estado', 'descricao')}),
    )

    @admin.display(description='Foto')
    def miniatura(self, obj):
        if not obj.foto:
            return '—'
        return format_html(
            '<img src="{}" style="width:48px;height:48px;object-fit:cover;border-radius:6px">', obj.foto.url
        )


class PedidoItemInline(admin.TabularInline):
    model = PedidoItem
    extra = 0
    fields = ('nome', 'quantidade', 'preco_unitario')
    readonly_fields = ('nome', 'quantidade', 'preco_unitario')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('numero', 'nome', 'telefone', 'resumo_itens', 'valor_total', 'status', 'criado_em')
    list_filter = ('status',)
    search_fields = ('nome', 'telefone', 'itens__nome')
    # Status muda só pelas ações, para o estoque acompanhar corretamente
    readonly_fields = ('nome', 'telefone', 'observacao', 'status', 'criado_em')
    inlines = [PedidoItemInline]
    actions = ['concluir', 'cancelar']

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('itens')

    @admin.display(description='Nº')
    def numero(self, obj):
        return obj.numero

    @admin.display(description='Itens')
    def resumo_itens(self, obj):
        return ', '.join(str(i) for i in obj.itens.all())

    @admin.display(description='Total (R$)')
    def valor_total(self, obj):
        return obj.total

    @admin.action(description='Concluir (pago e retirado)')
    def concluir(self, request, queryset):
        quantidade = queryset.filter(status='pendente').update(status='concluido')
        self.message_user(request, f'{quantidade} pedido(s) concluído(s).')

    @admin.action(description='Cancelar (produtos voltam ao estoque)')
    def cancelar(self, request, queryset):
        pedidos = list(queryset.filter(status='pendente').prefetch_related('itens'))
        with transaction.atomic():
            for pedido in pedidos:
                devolver_ao_estoque(pedido)
                pedido.status = 'cancelado'
                pedido.save(update_fields=['status'])
        self.message_user(request, f'{len(pedidos)} pedido(s) cancelado(s); produtos de volta ao estoque.')

    def delete_queryset(self, request, queryset):
        # Excluir um pedido pendente também devolve os produtos ao estoque
        with transaction.atomic():
            for pedido in queryset.filter(status='pendente').prefetch_related('itens'):
                devolver_ao_estoque(pedido)
            super().delete_queryset(request, queryset)

    def delete_model(self, request, obj):
        with transaction.atomic():
            if obj.status == 'pendente':
                devolver_ao_estoque(obj)
            super().delete_model(request, obj)
