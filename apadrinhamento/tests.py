from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from animais.models import Animal
from core.mercadopago_service import MercadoPagoError

from .models import Apadrinhamento

DADOS = {
    'nome_padrinho': 'João',
    'email_padrinho': 'joao@example.com',
    'telefone_padrinho': '(93) 99999-0000',
    'valor_mensal': '50',
}


@override_settings(MERCADOPAGO_ACCESS_TOKEN='TEST-token')
class ApadrinhamentoTests(TestCase):
    def setUp(self):
        self.animal = Animal.objects.create(nome='Totó', sexo='macho', porte='medio')
        self.url = reverse('apadrinhamento:apadrinhar', args=[self.animal.slug])

    def test_paginas(self):
        self.assertContains(self.client.get(reverse('apadrinhamento:lista')), 'Totó')
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.client.get(reverse('apadrinhamento:obrigado')).status_code, 200)

    def test_animal_adotado_nao_pode_ser_apadrinhado(self):
        self.animal.status = 'adotado'
        self.animal.save()
        self.assertEqual(self.client.get(self.url).status_code, 404)

    @patch('apadrinhamento.views.criar_assinatura_apadrinhamento')
    def test_redireciona_para_assinatura(self, criar):
        criar.return_value = {'id': 'PRE-1', 'init_point': 'https://mp.example/assinatura'}
        resp = self.client.post(self.url, DADOS)
        self.assertRedirects(resp, 'https://mp.example/assinatura', fetch_redirect_response=False)
        self.assertEqual(Apadrinhamento.objects.get().mercadopago_preapproval_id, 'PRE-1')

    @patch('apadrinhamento.views.criar_assinatura_apadrinhamento', side_effect=MercadoPagoError('x'))
    def test_falha_nao_deixa_registro_orfao(self, _criar):
        resp = self.client.post(self.url, DADOS)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Apadrinhamento.objects.exists())

    def test_valor_minimo(self):
        resp = self.client.post(self.url, {**DADOS, 'valor_mensal': '5'})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Apadrinhamento.objects.exists())

    @patch('apadrinhamento.views.buscar_preapproval')
    def test_webhook_ativa_apadrinhamento(self, buscar):
        ap = Apadrinhamento.objects.create(animal=self.animal, nome_padrinho='J', email_padrinho='j@j.com', valor_mensal=30)
        buscar.return_value = {'external_reference': str(ap.pk), 'status': 'authorized'}
        resp = self.client.post(
            reverse('apadrinhamento:webhook_mercadopago') + '?type=subscription_preapproval&data.id=PRE-9'
        )
        self.assertEqual(resp.status_code, 200)
        ap.refresh_from_db()
        self.assertEqual(ap.status, 'ativo')

    @patch('apadrinhamento.views.buscar_preapproval')
    def test_retorno_sincroniza(self, buscar):
        ap = Apadrinhamento.objects.create(animal=self.animal, nome_padrinho='J', email_padrinho='j@j.com', valor_mensal=30)
        buscar.return_value = {'external_reference': str(ap.pk), 'status': 'authorized'}
        resp = self.client.get(reverse('apadrinhamento:obrigado') + '?preapproval_id=PRE-9')
        self.assertContains(resp, 'Totó')
        ap.refresh_from_db()
        self.assertEqual(ap.status, 'ativo')
