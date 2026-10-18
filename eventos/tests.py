from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Encomenda, Evento, ItemCardapio, resumo_encomendas

CONTATO = {'nome': 'Ana', 'telefone': '(93) 99999-0000'}


def criar_evento(dias=3, **kwargs):
    return Evento.objects.create(
        titulo=kwargs.pop('titulo', 'Feijoada beneficente'),
        data=timezone.localdate() + timedelta(days=dias),
        **kwargs,
    )


class EventoTests(TestCase):
    def setUp(self):
        self.evento = criar_evento(local='Sede da ONG')
        self.marmita = ItemCardapio.objects.create(evento=self.evento, nome='Marmita', preco=Decimal('25'))
        self.bolo = ItemCardapio.objects.create(evento=self.evento, nome='Bolo', preco=Decimal('15'))
        self.url = reverse('eventos:detalhe', args=[self.evento.slug])

    def test_proximos_ignora_passados_e_inativos(self):
        criar_evento(dias=-1, titulo='Passado')
        criar_evento(dias=1, titulo='Oculto', ativo=False)
        amanha = criar_evento(dias=1, titulo='Amanhã')
        self.assertEqual(list(Evento.objects.proximos()), [amanha, self.evento])

    def test_paginas(self):
        self.assertContains(self.client.get(reverse('eventos:lista')), 'Feijoada beneficente')
        resp = self.client.get(self.url)
        self.assertContains(resp, 'Marmita')
        self.assertContains(resp, 'Fazer encomenda')

    def test_home_divulga_proximo_evento(self):
        resp = self.client.get(reverse('core:home'))
        self.assertContains(resp, 'Próximo evento')
        self.assertContains(resp, self.url)

    def test_encomenda_salva_itens_com_preco_do_momento(self):
        dados = {**CONTATO, f'qtd_{self.marmita.pk}': '2', f'qtd_{self.bolo.pk}': '1', 'observacao': 'Retiro 12h'}
        resp = self.client.post(self.url, dados)
        encomenda = Encomenda.objects.get()
        self.assertRedirects(resp, reverse('eventos:encomenda', args=[encomenda.codigo]))
        self.assertEqual(encomenda.total, Decimal('65'))

        self.marmita.preco = Decimal('99')
        self.marmita.save()
        self.assertEqual(Encomenda.objects.get().total, Decimal('65'))

        resp = self.client.get(reverse('eventos:encomenda', args=[encomenda.codigo]))
        self.assertContains(resp, '2× Marmita')
        self.assertContains(resp, 'R$ 65,00')
        self.assertIn('2x Marmita', encomenda.mensagem_whatsapp())
        self.assertIn('Total: R$ 65,00', encomenda.mensagem_whatsapp())

    def test_encomenda_sem_itens_e_recusada(self):
        resp = self.client.post(self.url, {**CONTATO, f'qtd_{self.marmita.pk}': '0'})
        self.assertContains(resp, 'pelo menos um item')
        self.assertFalse(Encomenda.objects.exists())

    def test_telefone_invalido(self):
        resp = self.client.post(self.url, {'nome': 'Ana', 'telefone': '123', f'qtd_{self.marmita.pk}': '1'})
        self.assertContains(resp, 'Informe um telefone com DDD')
        self.assertFalse(Encomenda.objects.exists())

    def test_item_esgotado_nao_pode_ser_encomendado(self):
        self.marmita.disponivel = False
        self.marmita.save()
        self.client.post(self.url, {**CONTATO, f'qtd_{self.marmita.pk}': '3', f'qtd_{self.bolo.pk}': '1'})
        self.assertEqual([i.nome for i in Encomenda.objects.get().itens.all()], ['Bolo'])

    def test_evento_passado_nao_aceita_encomenda(self):
        self.evento.data = timezone.localdate() - timedelta(days=1)
        self.evento.save()
        resp = self.client.post(self.url, {**CONTATO, f'qtd_{self.marmita.pk}': '1'})
        self.assertRedirects(resp, self.url)
        self.assertFalse(Encomenda.objects.exists())
        self.assertContains(self.client.get(self.url), 'já aconteceu')

    def test_resumo_para_cozinha_ignora_canceladas(self):
        for qtd, status in [(2, 'nova'), (3, 'confirmada'), (10, 'cancelada')]:
            self.client.post(self.url, {**CONTATO, f'qtd_{self.marmita.pk}': str(qtd)})
            Encomenda.objects.filter(pk=Encomenda.objects.latest('pk').pk).update(status=status)
        self.assertEqual(list(resumo_encomendas(self.evento)), [{'nome': 'Marmita', 'total': 5}])

    def test_admin_abre_paginas(self):
        User.objects.create_superuser('admin_teste', 'a@a.com', 'senha-forte-123')
        self.client.login(username='admin_teste', password='senha-forte-123')
        for url in [
            reverse('admin:eventos_evento_change', args=[self.evento.pk]),
            reverse('admin:eventos_evento_add'),
            reverse('admin:eventos_encomenda_changelist'),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
