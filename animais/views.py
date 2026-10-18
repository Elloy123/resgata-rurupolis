from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from .models import Animal

ANIMAIS_POR_PAGINA = 12


def lista_animais(request):
    animais = Animal.objects.exclude(status='adotado')

    especie = request.GET.get('especie', '')
    porte = request.GET.get('porte', '')
    sexo = request.GET.get('sexo', '')

    if especie:
        animais = animais.filter(especie=especie)
    if porte:
        animais = animais.filter(porte=porte)
    if sexo:
        animais = animais.filter(sexo=sexo)

    pagina = Paginator(animais, ANIMAIS_POR_PAGINA).get_page(request.GET.get('pagina'))

    filtros = request.GET.copy()
    filtros.pop('pagina', None)

    context = {
        'animais': pagina,
        'pagina': pagina,
        'filtros_querystring': filtros.urlencode(),
        'especie_selecionada': especie,
        'porte_selecionado': porte,
        'sexo_selecionado': sexo,
        'especie_choices': Animal.ESPECIE_CHOICES,
        'porte_choices': Animal.PORTE_CHOICES,
        'sexo_choices': Animal.SEXO_CHOICES,
    }
    return render(request, 'animais/lista.html', context)


def detalhe_animal(request, slug):
    animal = get_object_or_404(Animal.objects.prefetch_related('fotos_extras'), slug=slug)
    context = {'animal': animal, 'fotos_extras': list(animal.fotos_extras.all())}
    return render(request, 'animais/detalhe.html', context)
