from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import EncomendaForm
from .models import Encomenda, EncomendaItem, Evento


def lista_eventos(request):
    context = {'eventos': Evento.objects.proximos().prefetch_related('itens')}
    return render(request, 'eventos/lista.html', context)


def detalhe_evento(request, slug):
    evento = get_object_or_404(Evento, slug=slug, ativo=True)
    itens = evento.itens.filter(disponivel=True)
    form = EncomendaForm(request.POST or None, itens=itens)

    if request.method == 'POST':
        if not evento.encomendas_abertas:
            messages.error(request, 'As encomendas para este evento estão encerradas.')
            return redirect('eventos:detalhe', slug=evento.slug)
        if form.is_valid():
            with transaction.atomic():
                encomenda = Encomenda.objects.create(
                    evento=evento,
                    nome=form.cleaned_data['nome'],
                    telefone=form.cleaned_data['telefone'],
                    observacao=form.cleaned_data['observacao'],
                )
                EncomendaItem.objects.bulk_create([
                    EncomendaItem(
                        encomenda=encomenda, item=item, nome=item.nome,
                        preco_unitario=item.preco, quantidade=quantidade,
                    )
                    for item, quantidade in form.quantidades()
                ])
            return redirect('eventos:encomenda', codigo=encomenda.codigo)

    context = {
        'evento': evento,
        'itens': itens,
        'itens_esgotados': evento.itens.filter(disponivel=False),
        'form': form,
    }
    return render(request, 'eventos/detalhe.html', context)


def confirmacao_encomenda(request, codigo):
    encomenda = get_object_or_404(
        Encomenda.objects.select_related('evento').prefetch_related('itens'), codigo=codigo
    )
    return render(request, 'eventos/confirmacao_encomenda.html', {'encomenda': encomenda})
