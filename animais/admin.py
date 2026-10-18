from django.contrib import admin

from .models import Animal, FotoAnimal


class FotoAnimalInline(admin.TabularInline):
    model = FotoAnimal
    extra = 1


@admin.register(Animal)
class AnimalAdmin(admin.ModelAdmin):
    list_display = ('nome', 'especie', 'sexo', 'porte', 'status', 'disponivel_para_apadrinhamento', 'data_cadastro')
    list_filter = ('especie', 'sexo', 'porte', 'status', 'disponivel_para_apadrinhamento')
    search_fields = ('nome', 'raca', 'descricao')
    prepopulated_fields = {'slug': ('nome',)}
    inlines = [FotoAnimalInline]
