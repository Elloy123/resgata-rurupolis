from django.contrib import admin

from .models import CampanhaDoacao, Doacao


class DoacaoInline(admin.TabularInline):
    model = Doacao
    extra = 0
    fields = ('nome_doador', 'email_doador', 'valor', 'status', 'criado_em')
    readonly_fields = ('nome_doador', 'email_doador', 'valor', 'criado_em')
    can_delete = False
    show_change_link = True


@admin.register(CampanhaDoacao)
class CampanhaDoacaoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'meta_valor', 'valor_arrecadado', 'percentual_atingido', 'ativa', 'criado_em')
    list_filter = ('ativa',)
    search_fields = ('titulo', 'descricao')
    prepopulated_fields = {'slug': ('titulo',)}
    inlines = [DoacaoInline]

    def get_queryset(self, request):
        return super().get_queryset(request).com_arrecadado()

    @admin.display(description='Arrecadado (R$)', ordering='total_arrecadado')
    def valor_arrecadado(self, obj):
        return obj.valor_arrecadado

    @admin.display(description='% da meta')
    def percentual_atingido(self, obj):
        return f'{obj.percentual_atingido}%'


@admin.register(Doacao)
class DoacaoAdmin(admin.ModelAdmin):
    list_display = ('nome_doador', 'campanha', 'valor', 'status', 'criado_em')
    list_select_related = ('campanha',)
    date_hierarchy = 'criado_em'
    list_filter = ('status', 'campanha')
    search_fields = ('nome_doador', 'email_doador', 'mercadopago_payment_id')
    readonly_fields = ('mercadopago_preference_id', 'mercadopago_payment_id', 'criado_em', 'atualizado_em')
