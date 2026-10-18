import logging

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.mercadopago_service import (
    MercadoPagoError,
    buscar_pagamento,
    criar_preferencia_doacao,
    extrair_notificacao,
    mercadopago_configurado,
)

from .forms import DoacaoForm
from .models import CampanhaDoacao, Doacao

logger = logging.getLogger(__name__)

STATUS_MP_PARA_DOACAO = {
    'approved': 'aprovado',
    'authorized': 'pendente',
    'rejected': 'rejeitado',
    'cancelled': 'cancelado',
    'refunded': 'cancelado',
    'charged_back': 'cancelado',
    'pending': 'pendente',
    'in_process': 'pendente',
    'in_mediation': 'pendente',
}


def lista_campanhas(request):
    campanhas = CampanhaDoacao.objects.filter(ativa=True).com_arrecadado()
    return render(request, 'doacoes/lista.html', {'campanhas': campanhas})


def detalhe_campanha(request, slug):
    campanha = get_object_or_404(CampanhaDoacao, slug=slug)
    form = DoacaoForm()
    return render(request, 'doacoes/detalhe.html', {'campanha': campanha, 'form': form})


def _renderizar_formulario(request, form, campanha):
    if campanha:
        return render(request, 'doacoes/detalhe.html', {'campanha': campanha, 'form': form})
    return render(request, 'doacoes/doar.html', {'form': form, 'campanha': None})


def _processar_doacao(request, campanha=None):
    if request.method != 'POST':
        if campanha:
            return redirect('doacoes:detalhe', slug=campanha.slug)
        return render(request, 'doacoes/doar.html', {'form': DoacaoForm(), 'campanha': None})

    form = DoacaoForm(request.POST)
    if not form.is_valid():
        return _renderizar_formulario(request, form, campanha)

    if not mercadopago_configurado():
        logger.error('Tentativa de doação sem MERCADOPAGO_ACCESS_TOKEN configurado.')
        messages.warning(
            request,
            'As doações on-line estão temporariamente indisponíveis. '
            'Você ainda pode contribuir via PIX ou entrando em contato com a ONG.',
        )
        return _renderizar_formulario(request, form, campanha)

    doacao = form.save(commit=False)
    doacao.campanha = campanha
    doacao.save()

    try:
        preferencia = criar_preferencia_doacao(doacao)
    except Exception:
        logger.exception('Erro ao criar preferência de pagamento no Mercado Pago para doação %s', doacao.pk)
        doacao.delete()
        messages.error(
            request,
            'Não foi possível iniciar o pagamento no momento. Tente novamente em instantes.',
        )
        return _renderizar_formulario(request, form, campanha)

    doacao.mercadopago_preference_id = preferencia['id']
    doacao.save(update_fields=['mercadopago_preference_id', 'atualizado_em'])

    return redirect(preferencia['init_point'])


def doar_campanha(request, slug):
    campanha = get_object_or_404(CampanhaDoacao, slug=slug)
    if not campanha.ativa:
        messages.info(request, 'Esta vaquinha foi encerrada, mas você ainda pode fazer uma doação geral.')
        return redirect('doacoes:doar_geral')
    return _processar_doacao(request, campanha=campanha)


def doar_geral(request):
    return _processar_doacao(request, campanha=None)


def atualizar_doacao_pelo_pagamento(payment_id):
    """Consulta o pagamento direto na API do Mercado Pago (fonte confiável) e
    atualiza a doação correspondente. Retorna a doação ou None."""
    pagamento = buscar_pagamento(payment_id)
    external_reference = str(pagamento.get('external_reference') or '')
    if not external_reference.isdigit():
        logger.warning('Pagamento %s sem external_reference válido: %r', payment_id, external_reference)
        return None

    doacao = Doacao.objects.filter(pk=int(external_reference)).first()
    if doacao is None:
        logger.warning('Doação %s não encontrada (pagamento %s)', external_reference, payment_id)
        return None

    doacao.status = STATUS_MP_PARA_DOACAO.get(pagamento.get('status'), doacao.status)
    doacao.mercadopago_payment_id = str(payment_id)
    doacao.save(update_fields=['status', 'mercadopago_payment_id', 'atualizado_em'])
    return doacao


def _sincronizar_retorno(request):
    """Ao voltar do Mercado Pago, o pagamento vem na query string; aproveitamos
    para atualizar o status sem depender só do webhook."""
    payment_id = request.GET.get('payment_id') or request.GET.get('collection_id')
    if not payment_id or payment_id == 'null' or not mercadopago_configurado():
        return None
    try:
        return atualizar_doacao_pelo_pagamento(payment_id)
    except Exception:
        logger.exception('Erro ao sincronizar pagamento %s no retorno', payment_id)
        return None


def doacao_obrigado(request):
    return render(request, 'doacoes/obrigado.html', {'doacao': _sincronizar_retorno(request)})


def doacao_pendente(request):
    return render(request, 'doacoes/pendente.html', {'doacao': _sincronizar_retorno(request)})


def doacao_erro(request):
    _sincronizar_retorno(request)
    return render(request, 'doacoes/erro.html')


@csrf_exempt
@require_POST
def webhook_mercadopago(request):
    tipo, payment_id = extrair_notificacao(request)

    if tipo == 'payment' and payment_id:
        try:
            atualizar_doacao_pelo_pagamento(payment_id)
        except MercadoPagoError:
            logger.exception('Erro ao buscar pagamento %s no Mercado Pago', payment_id)

    return HttpResponse(status=200)
