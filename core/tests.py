import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from animais.models import Animal
from apadrinhamento.models import Apadrinhamento
from doacoes.models import Doacao

from .models import SobreONG, TelefoneUtil
from .templatetags.site_extras import whatsapp_br


class CoreTests(TestCase):
    def test_paginas(self):
        TelefoneUtil.objects.create(nome='Clínica Vet', telefone='(93) 98888-7777', whatsapp=True)
        for nome in ['core:home', 'core:sobre', 'core:telefones']:
            with self.subTest(pagina=nome):
                self.assertEqual(self.client.get(reverse(nome)).status_code, 200)
        resp = self.client.get(reverse('core:telefones'))
        self.assertContains(resp, 'href="tel:93988887777"')
        self.assertContains(resp, 'https://wa.me/5593988887777')

    def test_sobre_ong_e_singleton(self):
        SobreONG(titulo='A').save()
        SobreONG(titulo='B').save()
        self.assertEqual(SobreONG.objects.count(), 1)
        self.assertEqual(SobreONG.get_solo().titulo, 'B')

    def test_whatsapp_br(self):
        self.assertEqual(whatsapp_br('(93) 99999-0000'), '5593999990000')
        self.assertEqual(whatsapp_br('+55 93 99999-0000'), '5593999990000')
        self.assertEqual(whatsapp_br(''), '')

    @override_settings(MERCADOPAGO_ACCESS_TOKEN='TEST-token')
    def test_webhook_unico_encaminha_pagamento_e_assinatura(self):
        animal = Animal.objects.create(nome='Totó', sexo='macho', porte='medio')
        doacao = Doacao.objects.create(nome_doador='A', email_doador='a@a.com', valor=10)
        ap = Apadrinhamento.objects.create(animal=animal, nome_padrinho='J', email_padrinho='j@j.com', valor_mensal=30)
        url = reverse('core:webhook_mercadopago')

        with patch('doacoes.views.buscar_pagamento') as buscar:
            buscar.return_value = {'external_reference': str(doacao.pk), 'status': 'approved'}
            resp = self.client.post(url, json.dumps({'type': 'payment', 'data': {'id': '77'}}), content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        with patch('apadrinhamento.views.buscar_preapproval') as buscar:
            buscar.return_value = {'external_reference': str(ap.pk), 'status': 'authorized'}
            resp = self.client.post(url + '?type=subscription_preapproval&data.id=PRE-1')
        self.assertEqual(resp.status_code, 200)

        doacao.refresh_from_db()
        ap.refresh_from_db()
        self.assertEqual(doacao.status, 'aprovado')
        self.assertEqual(ap.status, 'ativo')

    def test_webhook_unico_ignora_aviso_vazio(self):
        self.assertEqual(self.client.post(reverse('core:webhook_mercadopago')).status_code, 200)

    def test_404_personalizado(self):
        with self.settings(DEBUG=False):
            resp = self.client.get('/pagina-que-nao-existe/')
        self.assertContains(resp, 'Página não encontrada', status_code=404)
