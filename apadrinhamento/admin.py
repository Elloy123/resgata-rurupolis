from django.contrib import admin

from .models import Apadrinhamento


@admin.register(Apadrinhamento)
class ApadrinhamentoAdmin(admin.ModelAdmin):
    list_display = ('nome_padrinho', 'animal', 'valor_mensal', 'status', 'criado_em')
    list_filter = ('status',)
    list_select_related = ('animal',)
    date_hierarchy = 'criado_em'
    search_fields = ('nome_padrinho', 'email_padrinho', 'animal__nome', 'mercadopago_preapproval_id')
    readonly_fields = ('mercadopago_preapproval_id', 'criado_em', 'atualizado_em')
