import logging

from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from animais.models import Animal
from apadrinhamento.views import atualizar_apadrinhamento_pela_assinatura
from eventos.models import Evento
from doacoes.models import CampanhaDoacao
from doacoes.views import atualizar_doacao_pelo_pagamento

from .mercadopago_service import MercadoPagoError, extrair_notificacao
from .models import SobreONG, TelefoneUtil

logger = logging.getLogger(__name__)


def home(request):
    context = {
        'animais_destaque': Animal.objects.filter(status='disponivel')[:4],
        'campanhas_destaque': CampanhaDoacao.objects.filter(ativa=True).com_arrecadado()[:3],
        'proximo_evento': Evento.objects.proximos().first(),
    }
    return render(request, 'core/home.html', context)


def sobre(request):
    context = {'sobre': SobreONG.get_solo()}
    return render(request, 'core/sobre.html', context)


def telefones_uteis(request):
    context = {'telefones': TelefoneUtil.objects.all()}
    return render(request, 'core/telefones.html', context)


@csrf_exempt
@require_POST
def webhook_mercadopago(request):
    """Webhook único para cadastrar no painel do Mercado Pago (que aceita só uma URL
    por aplicação). Encaminha avisos de pagamento para as doações e avisos de
    assinatura para os apadrinhamentos. O status é sempre consultado na API do
    Mercado Pago, nunca lido do corpo da notificação."""
    tipo, recurso_id = extrair_notificacao(request)
    if not recurso_id:
        return HttpResponse(status=200)

    try:
        if tipo == 'payment':
            atualizar_doacao_pelo_pagamento(recurso_id)
        elif tipo in ('subscription_preapproval', 'preapproval'):
            atualizar_apadrinhamento_pela_assinatura(recurso_id)
    except MercadoPagoError:
        logger.exception('Erro ao processar notificação %s %s do Mercado Pago', tipo, recurso_id)

    return HttpResponse(status=200)
