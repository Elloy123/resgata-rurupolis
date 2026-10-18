import logging

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from animais.models import Animal
from core.mercadopago_service import (
    MercadoPagoError,
    buscar_preapproval,
    criar_assinatura_apadrinhamento,
    extrair_notificacao,
    mercadopago_configurado,
)

from .forms import VALORES_SUGERIDOS, ApadrinhamentoForm
from .models import Apadrinhamento

logger = logging.getLogger(__name__)

STATUS_MP_PARA_APADRINHAMENTO = {
    'authorized': 'ativo',
    'paused': 'suspenso',
    'cancelled': 'cancelado',
    'pending': 'pendente',
}


def lista_apadrinhamento(request):
    animais = Animal.objects.filter(disponivel_para_apadrinhamento=True).exclude(status='adotado')
    return render(request, 'apadrinhamento/lista.html', {'animais': animais})


def _renderizar_formulario(request, animal, form):
    return render(
        request,
        'apadrinhamento/apadrinhar.html',
        {'animal': animal, 'form': form, 'valores_sugeridos': VALORES_SUGERIDOS},
    )


def apadrinhar_animal(request, slug):
    animal = get_object_or_404(
        Animal.objects.exclude(status='adotado'), slug=slug, disponivel_para_apadrinhamento=True
    )

    if request.method != 'POST':
        return _renderizar_formulario(request, animal, ApadrinhamentoForm())

    form = ApadrinhamentoForm(request.POST)
    if not form.is_valid():
        return _renderizar_formulario(request, animal, form)

    if not mercadopago_configurado():
        logger.error('Tentativa de apadrinhamento sem MERCADOPAGO_ACCESS_TOKEN configurado.')
        messages.warning(
            request,
            'O apadrinhamento on-line está temporariamente indisponível. '
            'Entre em contato com a ONG para apadrinhar este animal.',
        )
        return _renderizar_formulario(request, animal, form)

    apadrinhamento = form.save(commit=False)
    apadrinhamento.animal = animal
    apadrinhamento.save()

    try:
        preapproval = criar_assinatura_apadrinhamento(apadrinhamento)
    except Exception:
        logger.exception(
            'Erro ao criar assinatura no Mercado Pago para apadrinhamento %s', apadrinhamento.pk
        )
        apadrinhamento.delete()
        messages.error(
            request,
            'Não foi possível iniciar a assinatura no momento. Tente novamente em instantes.',
        )
        return _renderizar_formulario(request, animal, form)

    apadrinhamento.mercadopago_preapproval_id = preapproval['id']
    apadrinhamento.save(update_fields=['mercadopago_preapproval_id', 'atualizado_em'])

    return redirect(preapproval['init_point'])


def atualizar_apadrinhamento_pela_assinatura(preapproval_id):
    """Consulta a assinatura direto na API do Mercado Pago (fonte confiável) e
    atualiza o apadrinhamento correspondente. Retorna o apadrinhamento ou None."""
    preapproval = buscar_preapproval(preapproval_id)
    external_reference = str(preapproval.get('external_reference') or '')
    if not external_reference.isdigit():
        logger.warning('Assinatura %s sem external_reference válido: %r', preapproval_id, external_reference)
        return None

    apadrinhamento = Apadrinhamento.objects.filter(pk=int(external_reference)).first()
    if apadrinhamento is None:
        logger.warning('Apadrinhamento %s não encontrado (assinatura %s)', external_reference, preapproval_id)
        return None

    apadrinhamento.status = STATUS_MP_PARA_APADRINHAMENTO.get(
        preapproval.get('status'), apadrinhamento.status
    )
    apadrinhamento.save(update_fields=['status', 'atualizado_em'])
    return apadrinhamento


def apadrinhamento_obrigado(request):
    apadrinhamento = None
    preapproval_id = request.GET.get('preapproval_id')
    if preapproval_id and mercadopago_configurado():
        try:
            apadrinhamento = atualizar_apadrinhamento_pela_assinatura(preapproval_id)
        except Exception:
            logger.exception('Erro ao sincronizar assinatura %s no retorno', preapproval_id)
    return render(request, 'apadrinhamento/obrigado.html', {'apadrinhamento': apadrinhamento})


@csrf_exempt
@require_POST
def webhook_mercadopago(request):
    tipo, preapproval_id = extrair_notificacao(request)

    if tipo in ('subscription_preapproval', 'preapproval') and preapproval_id:
        try:
            atualizar_apadrinhamento_pela_assinatura(preapproval_id)
        except MercadoPagoError:
            logger.exception('Erro ao buscar assinatura %s no Mercado Pago', preapproval_id)

    return HttpResponse(status=200)
