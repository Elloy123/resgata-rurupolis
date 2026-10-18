"""Carrinho do bazar guardado na sessão do visitante (sem precisar de cadastro)."""
from decimal import Decimal

from django.db import transaction
from django.db.models import F

from .models import Pedido, PedidoItem, Produto

CHAVE_SESSAO = 'carrinho_bazar'


class ProdutoIndisponivel(Exception):
    def __init__(self, produto):
        self.produto = produto
        super().__init__(produto.nome)


class Carrinho:
    def __init__(self, request):
        self.session = request.session
        self.dados = {str(k): int(v) for k, v in self.session.get(CHAVE_SESSAO, {}).items()}

    def _salvar(self):
        self.session[CHAVE_SESSAO] = self.dados
        self.session.modified = True

    def __len__(self):
        return sum(self.dados.values())

    def quantidade_de(self, produto):
        return self.dados.get(str(produto.pk), 0)

    def adicionar(self, produto, quantidade=1, substituir=False):
        """Adiciona (ou define) a quantidade, sem passar do estoque. Retorna a quantidade final."""
        atual = 0 if substituir else self.quantidade_de(produto)
        final = max(0, min(atual + quantidade, produto.estoque))
        if final:
            self.dados[str(produto.pk)] = final
        else:
            self.dados.pop(str(produto.pk), None)
        self._salvar()
        return final

    def remover(self, produto_id):
        self.dados.pop(str(produto_id), None)
        self._salvar()

    def limpar(self):
        self.dados = {}
        self._salvar()

    def linhas(self):
        """Itens do carrinho conferidos com o banco. Produtos que saíram do site ou
        esgotaram são removidos e quantidades acima do estoque são reduzidas.
        Retorna (linhas, avisos)."""
        produtos = Produto.objects.in_bulk([int(pk) for pk in self.dados])
        linhas, avisos = [], []
        for pk, quantidade in list(self.dados.items()):
            produto = produtos.get(int(pk))
            if produto is None or not produto.ativo or produto.esgotado:
                nome = produto.nome if produto else 'Um produto'
                avisos.append(f'{nome} não está mais disponível e saiu do seu carrinho.')
                self.dados.pop(pk)
                continue
            if quantidade > produto.estoque:
                avisos.append(f'Só temos {produto.estoque} unidade(s) de {produto.nome}; ajustamos seu carrinho.')
                quantidade = self.dados[pk] = produto.estoque
            linhas.append({'produto': produto, 'quantidade': quantidade, 'subtotal': produto.preco * quantidade})
        if avisos:
            self._salvar()
        return linhas, avisos

    @staticmethod
    def total(linhas):
        return sum((l['subtotal'] for l in linhas), Decimal('0.00'))

    def finalizar(self, nome, telefone, observacao=''):
        """Cria o pedido e reserva o estoque de uma vez só. Se algum produto não tiver
        mais estoque suficiente, nada é gravado e ProdutoIndisponivel é lançada."""
        linhas, _ = self.linhas()
        with transaction.atomic():
            for linha in linhas:
                produto, quantidade = linha['produto'], linha['quantidade']
                # Atualização condicional: o estoque nunca fica negativo, mesmo com compras simultâneas
                baixou = Produto.objects.filter(
                    pk=produto.pk, ativo=True, estoque__gte=quantidade
                ).update(estoque=F('estoque') - quantidade)
                if not baixou:
                    raise ProdutoIndisponivel(produto)

            pedido = Pedido.objects.create(nome=nome, telefone=telefone, observacao=observacao)
            PedidoItem.objects.bulk_create([
                PedidoItem(
                    pedido=pedido, produto=l['produto'], nome=l['produto'].nome,
                    preco_unitario=l['produto'].preco, quantidade=l['quantidade'],
                )
                for l in linhas
            ])
        self.limpar()
        return pedido


def devolver_ao_estoque(pedido):
    for item in pedido.itens.all():
        if item.produto_id:
            Produto.objects.filter(pk=item.produto_id).update(estoque=F('estoque') + item.quantidade)
