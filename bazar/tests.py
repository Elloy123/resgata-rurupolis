from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import SobreONG

from .carrinho import CHAVE_SESSAO
from .models import Pedido, Produto

CONTATO = {'nome': 'Ana', 'telefone': '(93) 99999-0000'}


class BazarTests(TestCase):
    def setUp(self):
        self.vestido = Produto.objects.create(nome='Vestido floral', preco=Decimal('20'), categoria='roupa', tamanho='M')
        self.caneca = Produto.objects.create(nome='Caneca da ONG', preco=Decimal('15'), categoria='casa', estoque=5)

    def adicionar(self, produto, quantidade=1):
        return self.client.post(reverse('bazar:adicionar', args=[produto.pk]), {'quantidade': quantidade})

    def carrinho(self):
        return self.client.session.get(CHAVE_SESSAO, {})

    def test_lista_mostra_cards_com_preco_e_esconde_esgotados(self):
        Produto.objects.create(nome='Tênis esgotado', preco=10, estoque=0)
        Produto.objects.create(nome='Oculto', preco=10, ativo=False)
        resp = self.client.get(reverse('bazar:lista'))
        self.assertContains(resp, 'Vestido floral')
        self.assertContains(resp, 'R$ 20,00')
        self.assertContains(resp, 'Adicionar ao carrinho')
        self.assertNotContains(resp, 'Tênis esgotado')
        self.assertNotContains(resp, 'Oculto')
        self.assertNotContains(self.client.get(reverse('bazar:lista'), {'categoria': 'casa'}), 'Vestido floral')

    def test_detalhe(self):
        self.assertContains(self.client.get(reverse('bazar:produto', args=[self.caneca.slug])), '5 unidades')

    def test_adicionar_respeita_estoque(self):
        self.adicionar(self.caneca, 3)
        self.adicionar(self.caneca, 10)
        self.assertEqual(self.carrinho(), {str(self.caneca.pk): 5})

        self.adicionar(self.vestido)
        resp = self.adicionar(self.vestido)
        self.assertEqual(self.carrinho()[str(self.vestido.pk)], 1)
        self.assertContains(self.client.get(resp.url), 'todas as unidades disponíveis')

    def test_contador_no_menu(self):
        self.adicionar(self.caneca, 2)
        self.adicionar(self.vestido)
        resp = self.client.get(reverse('bazar:lista'))
        self.assertEqual(resp.context['carrinho_qtd'], 3)

    def test_atualizar_e_remover(self):
        self.adicionar(self.caneca, 2)
        self.client.post(reverse('bazar:atualizar', args=[self.caneca.pk]), {'quantidade': 4})
        self.assertEqual(self.carrinho(), {str(self.caneca.pk): 4})
        self.client.post(reverse('bazar:remover', args=[self.caneca.pk]))
        self.assertEqual(self.carrinho(), {})
        self.assertContains(self.client.get(reverse('bazar:carrinho')), 'Seu carrinho está vazio')

    def test_finalizar_cria_pedido_baixa_estoque_e_esvazia_carrinho(self):
        self.adicionar(self.caneca, 2)
        self.adicionar(self.vestido)
        resp = self.client.get(reverse('bazar:carrinho'))
        self.assertContains(resp, 'R$ 50,00')

        resp = self.client.post(reverse('bazar:carrinho'), {**CONTATO, 'observacao': 'Sábado'})
        pedido = Pedido.objects.get()
        self.assertRedirects(resp, reverse('bazar:pedido', args=[pedido.codigo]))
        self.assertEqual(pedido.total, Decimal('50'))
        self.assertEqual(self.carrinho(), {})

        self.caneca.refresh_from_db()
        self.vestido.refresh_from_db()
        self.assertEqual(self.caneca.estoque, 3)
        self.assertEqual(self.vestido.estoque, 0)
        self.assertNotContains(self.client.get(reverse('bazar:lista')), 'Vestido floral')

        mensagem = pedido.mensagem_whatsapp()
        self.assertIn('2x Caneca da ONG (R$ 30,00)', mensagem)
        self.assertIn('Total: R$ 50,00', mensagem)

    def test_produto_esgotado_por_outra_pessoa_nao_grava_nada(self):
        self.adicionar(self.caneca, 2)
        self.adicionar(self.vestido)
        # Outra pessoa comprou o vestido enquanto este visitante preenchia o formulário
        Produto.objects.filter(pk=self.vestido.pk).update(estoque=0)

        resp = self.client.post(reverse('bazar:carrinho'), CONTATO)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Pedido.objects.exists())
        self.caneca.refresh_from_db()
        self.assertEqual(self.caneca.estoque, 5)
        self.assertEqual(self.carrinho(), {str(self.caneca.pk): 2})

    def test_carrinho_ajusta_quantidade_acima_do_estoque(self):
        self.adicionar(self.caneca, 5)
        Produto.objects.filter(pk=self.caneca.pk).update(estoque=2)
        resp = self.client.get(reverse('bazar:carrinho'), follow=True)
        self.assertContains(resp, 'Só temos 2 unidade(s)')
        self.assertEqual(self.carrinho(), {str(self.caneca.pk): 2})

    def test_finalizar_carrinho_vazio(self):
        self.client.post(reverse('bazar:carrinho'), CONTATO)
        self.assertFalse(Pedido.objects.exists())

    def test_limite_de_pedidos_pendentes_por_telefone(self):
        for _ in range(3):
            self.adicionar(self.caneca)
            self.client.post(reverse('bazar:carrinho'), {**CONTATO, 'telefone': '93 99999 0000'})
        self.adicionar(self.caneca)
        resp = self.client.post(reverse('bazar:carrinho'), CONTATO)
        self.assertContains(resp, 'pedidos pendentes')
        self.assertEqual(Pedido.objects.count(), 3)

    def test_confirmacao_com_e_sem_whatsapp(self):
        self.adicionar(self.vestido)
        self.client.post(reverse('bazar:carrinho'), CONTATO)
        url = reverse('bazar:pedido', args=[Pedido.objects.get().codigo])
        self.assertContains(self.client.get(url), 'vai entrar em contato')

        sobre = SobreONG.get_solo()
        sobre.whatsapp_contato = '(93) 98765-4321'
        sobre.save()
        resp = self.client.get(url)
        self.assertContains(resp, 'https://wa.me/5593987654321?text=')
        self.assertContains(resp, 'Vestido%20floral')

    def test_next_externo_e_ignorado(self):
        resp = self.client.post(reverse('bazar:adicionar', args=[self.caneca.pk]), {'next': 'https://site-malicioso.com/'})
        self.assertRedirects(resp, reverse('bazar:carrinho'))


class BazarAdminTests(TestCase):
    def setUp(self):
        User.objects.create_superuser('admin_teste', 'a@a.com', 'senha-forte-123')
        self.caneca = Produto.objects.create(nome='Caneca', preco=10, estoque=5)
        self.client.post(reverse('bazar:adicionar', args=[self.caneca.pk]), {'quantidade': 2})
        self.client.post(reverse('bazar:carrinho'), CONTATO)
        self.pedido = Pedido.objects.get()
        self.client.login(username='admin_teste', password='senha-forte-123')
        self.changelist = reverse('admin:bazar_pedido_changelist')

    def test_cancelar_devolve_ao_estoque(self):
        self.caneca.refresh_from_db()
        self.assertEqual(self.caneca.estoque, 3)
        self.client.post(self.changelist, {'action': 'cancelar', '_selected_action': [self.pedido.pk]})
        self.caneca.refresh_from_db()
        self.pedido.refresh_from_db()
        self.assertEqual(self.caneca.estoque, 5)
        self.assertEqual(self.pedido.status, 'cancelado')
        # Cancelar de novo não devolve em dobro
        self.client.post(self.changelist, {'action': 'cancelar', '_selected_action': [self.pedido.pk]})
        self.caneca.refresh_from_db()
        self.assertEqual(self.caneca.estoque, 5)

    def test_concluir_mantem_estoque(self):
        self.client.post(self.changelist, {'action': 'concluir', '_selected_action': [self.pedido.pk]})
        self.pedido.refresh_from_db()
        self.caneca.refresh_from_db()
        self.assertEqual(self.pedido.status, 'concluido')
        self.assertEqual(self.caneca.estoque, 3)

    def test_excluir_pedido_pendente_devolve_ao_estoque(self):
        self.client.post(reverse('admin:bazar_pedido_delete', args=[self.pedido.pk]), {'post': 'yes'})
        self.assertFalse(Pedido.objects.exists())
        self.caneca.refresh_from_db()
        self.assertEqual(self.caneca.estoque, 5)

    def test_paginas_do_admin(self):
        for url in [
            reverse('admin:bazar_produto_changelist'),
            reverse('admin:bazar_produto_add'),
            reverse('admin:bazar_pedido_change', args=[self.pedido.pk]),
            self.changelist,
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
