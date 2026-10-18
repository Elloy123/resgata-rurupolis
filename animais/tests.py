from django.test import TestCase
from django.urls import reverse

from .models import Animal


class AnimaisTests(TestCase):
    def setUp(self):
        self.rex = Animal.objects.create(nome='Rex', especie='cachorro', sexo='macho', porte='grande')
        self.mia = Animal.objects.create(nome='Mia', especie='gato', sexo='femea', porte='pequeno')
        self.bob = Animal.objects.create(nome='Bob', especie='cachorro', sexo='macho', porte='medio', status='adotado')

    def test_slug_unico(self):
        outro = Animal.objects.create(nome='Rex', sexo='macho', porte='grande')
        self.assertEqual(outro.slug, 'rex-2')

    def test_lista_esconde_adotados(self):
        resp = self.client.get(reverse('animais:lista'))
        self.assertContains(resp, 'Rex')
        self.assertContains(resp, 'Mia')
        self.assertNotContains(resp, 'Bob')

    def test_filtro_por_especie(self):
        resp = self.client.get(reverse('animais:lista'), {'especie': 'gato'})
        self.assertContains(resp, 'Mia')
        self.assertNotContains(resp, 'Rex')

    def test_paginacao(self):
        for i in range(15):
            Animal.objects.create(nome=f'Animal {i}', sexo='macho', porte='pequeno')
        resp = self.client.get(reverse('animais:lista'), {'especie': 'cachorro'})
        self.assertContains(resp, 'Página 1 de 2')
        self.assertContains(resp, 'especie=cachorro&amp;pagina=2')
        self.assertEqual(self.client.get(reverse('animais:lista'), {'pagina': '999'}).status_code, 200)

    def test_detalhe(self):
        self.assertContains(self.client.get(reverse('animais:detalhe', args=[self.rex.slug])), 'Rex')
        self.assertEqual(self.client.get(reverse('animais:detalhe', args=['nao-existe'])).status_code, 404)
