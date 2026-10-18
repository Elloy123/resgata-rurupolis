from django.contrib import admin
from django.utils.html import format_html_join

from .models import Encomenda, EncomendaItem, Evento, ItemCardapio, resumo_encomendas


class ItemCardapioInline(admin.TabularInline):
    model = ItemCardapio
    extra = 2
    fields = ('nome', 'descricao', 'preco', 'disponivel', 'ordem')


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'data', 'hora_inicio', 'local', 'aceita_encomendas', 'ativo', 'qtd_encomendas')
    list_filter = ('ativo', 'aceita_encomendas')
    search_fields = ('titulo', 'descricao', 'local')
    prepopulated_fields = {'slug': ('titulo',)}
    date_hierarchy = 'data'
    inlines = [ItemCardapioInline]
    readonly_fields = ('resumo_para_cozinha',)
    fieldsets = (
        (None, {'fields': ('titulo', 'slug', 'descricao', 'imagem')}),
        ('Quando e onde', {'fields': ('data', 'hora_inicio', 'hora_fim', 'local')}),
        ('Publicação', {'fields': ('aceita_encomendas', 'ativo')}),
        ('Encomendas', {'fields': ('resumo_para_cozinha',)}),
    )

    @admin.display(description='Encomendas')
    def qtd_encomendas(self, obj):
        return obj.encomendas.exclude(status='cancelada').count()

    @admin.display(description='Total encomendado por item (sem as canceladas)')
    def resumo_para_cozinha(self, obj):
        if not obj.pk:
            return '—'
        linhas = list(resumo_encomendas(obj))
        if not linhas:
            return 'Nenhuma encomenda ainda.'
        return format_html_join('', '<div><strong>{}</strong> × {}</div>', ((l['total'], l['nome']) for l in linhas))


class EncomendaItemInline(admin.TabularInline):
    model = EncomendaItem
    extra = 0
    fields = ('nome', 'quantidade', 'preco_unitario')
    readonly_fields = ('nome', 'quantidade', 'preco_unitario')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Encomenda)
class EncomendaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'nome', 'telefone', 'evento', 'resumo_itens', 'valor_total', 'status', 'criado_em')
    list_filter = ('status', 'evento')
    list_editable = ('status',)
    search_fields = ('nome', 'telefone')
    list_select_related = ('evento',)
    readonly_fields = ('evento', 'nome', 'telefone', 'observacao', 'criado_em')
    inlines = [EncomendaItemInline]

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
