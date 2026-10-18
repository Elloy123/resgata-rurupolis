"""Integração com o Mercado Pago para doações avulsas (Checkout Pro)
e apadrinhamentos recorrentes (assinaturas / preapproval).
"""
import json
from urllib.parse import urlparse

import mercadopago
from django.conf import settings
from django.urls import reverse


class MercadoPagoError(Exception):
    """Erro de configuração ou de resposta da API do Mercado Pago."""


def mercadopago_configurado():
    return bool(settings.MERCADOPAGO_ACCESS_TOKEN)


def get_sdk():
    if not mercadopago_configurado():
        raise MercadoPagoError(
            'MERCADOPAGO_ACCESS_TOKEN não configurado. Defina essa variável no arquivo .env.'
        )
    return mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)


def _site_publico():
    """True quando SITE_URL é um endereço público (o Mercado Pago rejeita
    notification_url e auto_return apontando para localhost)."""
    host = urlparse(settings.SITE_URL).hostname or ''
    return host not in ('localhost', '127.0.0.1', '0.0.0.0', '')


def _url_absoluta(nome_url):
    return settings.SITE_URL.rstrip('/') + reverse(nome_url)


def _checar_resposta(resposta, operacao):
    status = resposta.get('status')
    dados = resposta.get('response') or {}
    if not status or status >= 400:
        raise MercadoPagoError(f'{operacao} falhou (HTTP {status}): {dados}')
    return dados


def criar_preferencia_doacao(doacao):
    """Cria uma preferência de pagamento único (Checkout Pro) para uma Doacao."""
    sdk = get_sdk()
    titulo = f'Doação - {doacao.campanha.titulo}' if doacao.campanha else 'Doação - Resgata Rurópolis'

    preference_data = {
        'items': [
            {
                'title': titulo,
                'quantity': 1,
                'unit_price': float(doacao.valor),
                'currency_id': 'BRL',
            }
        ],
        'payer': {
            'name': doacao.nome_doador,
            'email': doacao.email_doador,
        },
        'back_urls': {
            'success': _url_absoluta('doacoes:obrigado'),
            'failure': _url_absoluta('doacoes:erro'),
            'pending': _url_absoluta('doacoes:pendente'),
        },
        'external_reference': str(doacao.pk),
    }
    if _site_publico():
        preference_data['auto_return'] = 'approved'
        preference_data['notification_url'] = _url_absoluta('core:webhook_mercadopago')

    resposta = sdk.preference().create(preference_data)
    return _checar_resposta(resposta, 'Criação de preferência')


def criar_assinatura_apadrinhamento(apadrinhamento):
    """Cria uma assinatura recorrente mensal (preapproval) para um Apadrinhamento."""
    sdk = get_sdk()

    preapproval_data = {
        'reason': f'Apadrinhamento de {apadrinhamento.animal.nome} - Resgata Rurópolis',
        'auto_recurring': {
            'frequency': 1,
            'frequency_type': 'months',
            'transaction_amount': float(apadrinhamento.valor_mensal),
            'currency_id': 'BRL',
        },
        'back_url': _url_absoluta('apadrinhamento:obrigado'),
        'payer_email': apadrinhamento.email_padrinho,
        'external_reference': str(apadrinhamento.pk),
        'status': 'pending',
    }
    # Avisos de assinatura chegam pelo webhook cadastrado no painel do Mercado Pago
    # (evento "Planos e assinaturas"), apontando para /webhook/mercadopago/.

    resposta = sdk.preapproval().create(preapproval_data)
    return _checar_resposta(resposta, 'Criação de assinatura')


def buscar_pagamento(payment_id):
    resposta = get_sdk().payment().get(payment_id)
    return _checar_resposta(resposta, f'Consulta do pagamento {payment_id}')


def buscar_preapproval(preapproval_id):
    resposta = get_sdk().preapproval().get(preapproval_id)
    return _checar_resposta(resposta, f'Consulta da assinatura {preapproval_id}')


def extrair_notificacao(request):
    """Lê tipo e id de uma notificação do Mercado Pago, que podem vir na
    query string (IPN / webhooks) ou no corpo JSON (webhooks)."""
    tipo = request.GET.get('type') or request.GET.get('topic')
    recurso_id = request.GET.get('data.id') or request.GET.get('id')
    if not (tipo and recurso_id) and request.body:
        try:
            corpo = json.loads(request.body)
        except ValueError:
            corpo = {}
        if isinstance(corpo, dict):
            tipo = tipo or corpo.get('type') or corpo.get('topic')
            dados = corpo.get('data') if isinstance(corpo.get('data'), dict) else {}
            recurso_id = recurso_id or dados.get('id')
    return tipo, (str(recurso_id) if recurso_id else None)
