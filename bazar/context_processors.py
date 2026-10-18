from .carrinho import CHAVE_SESSAO


def carrinho(request):
    """Quantidade de itens no carrinho para o ícone do menu (lida só da sessão, sem consultar o banco)."""
    dados = request.session.get(CHAVE_SESSAO, {}) if hasattr(request, 'session') else {}
    return {'carrinho_qtd': sum(int(v) for v in dados.values())}
