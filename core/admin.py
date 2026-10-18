from django.contrib import admin

from .models import SobreONG, TelefoneUtil

admin.site.site_header = 'Resgata Rurópolis - Administração'
admin.site.site_title = 'Resgata Rurópolis'
admin.site.index_title = 'Painel de gestão'


@admin.register(TelefoneUtil)
class TelefoneUtilAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria', 'telefone', 'whatsapp', 'ordem')
    list_filter = ('categoria', 'whatsapp')
    search_fields = ('nome', 'telefone', 'descricao')
    list_editable = ('ordem',)


@admin.register(SobreONG)
class SobreONGAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'email_contato', 'telefone_contato', 'atualizado_em')

    def has_add_permission(self, request):
        return not SobreONG.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
