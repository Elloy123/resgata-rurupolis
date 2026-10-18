import json
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from core.mercadopago_service import MercadoPagoError

from .models import CampanhaDoacao, Doacao

DADOS_DOACAO = {'nome_doador': 'Maria', 'email_doador': 'maria@example.com', 'valor': '50.00'}


class CampanhaModelTests(TestCase):
    def setUp(self):
        self.campanha = CampanhaDoacao.objects.create(titulo='Castração em massa', meta_valor=Decimal('1000'))
        Doacao.objects.create(campanha=self.campanha, nome_doador='A', email_doador='a@a.com', valor=300, status='aprovado')
        Doacao.objects.create(campanha=self.campanha, nome_doador='B', email_doador='b@b.com', valor=500, status='pendente')

    def test_slug_gerado_e_unico(self):
        outra = CampanhaDoacao.objects.create(titulo='Castração em massa', meta_valor=10)
        self.assertEqual(self.campanha.slug, 'castracao-em-massa')
        self.assertEqual(outra.slug, 'castracao-em-massa-2')

    def test_soma_apenas_doacoes_aprovadas(self):
        self.assertEqual(self.campanha.valor_arrecadado, Decimal('300'))
        self.assertEqual(self.campanha.percentual_atingido, 30)

    def test_anotacao_igual_ao_calculo_direto(self):
        anotada = CampanhaDoacao.objects.com_arrecadado().get(pk=self.campanha.pk)
        self.assertEqual(anotada.valor_arrecadado, Decimal('300'))

    def test_percentual_limitado_a_100(self):
        Doacao.objects.create(campanha=self.campanha, nome_doador='C', email_doador='c@c.com', valor=5000, status='aprovado')
        campanha = CampanhaDoacao.objects.get(pk=self.campanha.pk)
        self.assertEqual(campanha.percentual_atingido, 100)


@override_settings(MERCADOPAGO_ACCESS_TOKEN='TEST-token', SITE_URL='http://127.0.0.1:8000')
class DoacaoViewsTests(TestCase):
    def setUp(self):
        self.campanha = CampanhaDoacao.objects.create(titulo='Ração', meta_valor=500)

    def test_paginas_publicas(self):
        for url in [
            reverse('doacoes:lista'),
            reverse('doacoes:detalhe', args=[self.campanha.slug]),
            reverse('doacoes:doar_geral'),
            reverse('doacoes:obrigado'),
            reverse('doacoes:pendente'),
            reverse('doacoes:erro'),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    @patch('doacoes.views.criar_preferencia_doacao')
    def test_doacao_redireciona_para_mercado_pago(self, criar):
        criar.return_value = {'id': 'PREF-1', 'init_point': 'https://mp.example/checkout'}
        resp = self.client.post(reverse('doacoes:doar', args=[self.campanha.slug]), DADOS_DOACAO)
        self.assertRedirects(resp, 'https://mp.example/checkout', fetch_redirect_response=False)
        doacao = Doacao.objects.get()
        self.assertEqual(doacao.campanha, self.campanha)
        self.assertEqual(doacao.mercadopago_preference_id, 'PREF-1')

    @patch('doacoes.views.criar_preferencia_doacao', side_effect=MercadoPagoError('falhou'))
    def test_falha_no_mercado_pago_nao_deixa_doacao_orfa(self, _criar):
        resp = self.client.post(reverse('doacoes:doar_geral'), DADOS_DOACAO)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Doacao.objects.exists())
        self.assertContains(resp, 'Não foi possível iniciar o pagamento')

    @override_settings(MERCADOPAGO_ACCESS_TOKEN='')
    def test_sem_token_mostra_aviso_e_nao_salva(self):
        resp = self.client.post(reverse('doacoes:doar_geral'), DADOS_DOACAO)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Doacao.objects.exists())
        self.assertContains(resp, 'temporariamente indisponíveis')

    def test_valor_invalido(self):
        resp = self.client.post(reverse('doacoes:doar_geral'), {**DADOS_DOACAO, 'valor': '0'})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Doacao.objects.exists())

    def test_campanha_inativa_nao_recebe_doacao(self):
        self.campanha.ativa = False
        self.campanha.save()
        resp = self.client.post(reverse('doacoes:doar', args=[self.campanha.slug]), DADOS_DOACAO)
        self.assertRedirects(resp, reverse('doacoes:doar_geral'))
        self.assertFalse(Doacao.objects.exists())

    @patch('doacoes.views.buscar_pagamento')
    def test_webhook_atualiza_status(self, buscar):
        doacao = Doacao.objects.create(campanha=self.campanha, nome_doador='A', email_doador='a@a.com', valor=10)
        buscar.return_value = {'external_reference': str(doacao.pk), 'status': 'approved'}
        resp = self.client.post(
            reverse('doacoes:webhook_mercadopago'),
            data=json.dumps({'type': 'payment', 'data': {'id': '999'}}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        buscar.assert_called_once_with('999')
        doacao.refresh_from_db()
        self.assertEqual(doacao.status, 'aprovado')
        self.assertEqual(doacao.mercadopago_payment_id, '999')

    @patch('doacoes.views.buscar_pagamento')
    def test_webhook_com_referencia_invalida_nao_quebra(self, buscar):
        buscar.return_value = {'external_reference': 'abc', 'status': 'approved'}
        resp = self.client.post(reverse('doacoes:webhook_mercadopago') + '?type=payment&data.id=1')
        self.assertEqual(resp.status_code, 200)

    @patch('doacoes.views.buscar_pagamento')
    def test_retorno_sincroniza_status(self, buscar):
        doacao = Doacao.objects.create(nome_doador='Ana', email_doador='a@a.com', valor=25)
        buscar.return_value = {'external_reference': str(doacao.pk), 'status': 'approved'}
        resp = self.client.get(reverse('doacoes:obrigado') + '?payment_id=123&status=approved')
        self.assertContains(resp, 'foi confirmada')
        doacao.refresh_from_db()
        self.assertEqual(doacao.status, 'aprovado')


class PreferenciaTests(TestCase):
    @override_settings(MERCADOPAGO_ACCESS_TOKEN='TEST-token', SITE_URL='http://127.0.0.1:8000')
    @patch('core.mercadopago_service.mercadopago.SDK')
    def test_localhost_nao_envia_webhook_nem_auto_return(self, sdk):
        from core.mercadopago_service import criar_preferencia_doacao

        sdk.return_value.preference.return_value.create.return_value = {
            'status': 201, 'response': {'id': 'X', 'init_point': 'https://mp'}
        }
        doacao = Doacao.objects.create(nome_doador='A', email_doador='a@a.com', valor=10)
        criar_preferencia_doacao(doacao)
        dados = sdk.return_value.preference.return_value.create.call_args.args[0]
        self.assertNotIn('notification_url', dados)
        self.assertNotIn('auto_return', dados)
        self.assertEqual(dados['back_urls']['success'], 'http://127.0.0.1:8000/vaquinhas/obrigado/')

    @override_settings(MERCADOPAGO_ACCESS_TOKEN='TEST-token', SITE_URL='https://resgata.org')
    @patch('core.mercadopago_service.mercadopago.SDK')
    def test_site_publico_envia_webhook(self, sdk):
        from core.mercadopago_service import criar_preferencia_doacao

        sdk.return_value.preference.return_value.create.return_value = {
            'status': 201, 'response': {'id': 'X', 'init_point': 'https://mp'}
        }
        doacao = Doacao.objects.create(nome_doador='A', email_doador='a@a.com', valor=10)
        criar_preferencia_doacao(doacao)
        dados = sdk.return_value.preference.return_value.create.call_args.args[0]
        self.assertEqual(dados['notification_url'], 'https://resgata.org/webhook/mercadopago/')
        self.assertEqual(dados['auto_return'], 'approved')

    @override_settings(MERCADOPAGO_ACCESS_TOKEN='TEST-token')
    @patch('core.mercadopago_service.mercadopago.SDK')
    def test_erro_da_api_vira_excecao(self, sdk):
        from core.mercadopago_service import criar_preferencia_doacao

        sdk.return_value.preference.return_value.create.return_value = {
            'status': 400, 'response': {'message': 'invalid'}
        }
        doacao = Doacao.objects.create(nome_doador='A', email_doador='a@a.com', valor=10)
        with self.assertRaises(MercadoPagoError):
            criar_preferencia_doacao(doacao)
