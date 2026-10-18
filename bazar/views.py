from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.utils import apenas_digitos

from .carrinho import Carrinho, ProdutoIndisponivel
from .forms import FinalizarPedidoForm
from .models import Pedido, Produto

PRODUTOS_POR_PAGINA = 12
MAX_PEDIDOS_PENDENTES_POR_TELEFONE = 3


def lista_produtos(request):
    produtos = Produto.objects.filter(ativo=True, estoque__gt=0)
    categoria = request.GET.get('categoria', '')
    if categoria:
        produtos = produtos.filter(categoria=categoria)

    pagina = Paginator(produtos, PRODUTOS_POR_PAGINA).get_page(request.GET.get('pagina'))
    filtros = request.GET.copy()
    filtros.pop('pagina', None)

    context = {
        'produtos': pagina,
        'pagina': pagina,
        'filtros_querystring': filtros.urlencode(),
        'categoria_selecionada': categoria,
        'categoria_choices': Produto.CATEGORIA_CHOICES,
    }
    return render(request, 'bazar/lista.html', context)


def detalhe_produto(request, slug):
    produto = get_object_or_404(Produto.objects.prefetch_related('fotos_extras'), slug=slug, ativo=True)
    context = {
        'produto': produto,
        'fotos_extras': list(produto.fotos_extras.all()),
        'no_carrinho': Carrinho(request).quantidade_de(produto),
    }
    return render(request, 'bazar/detalhe.html', context)


def _voltar(request, padrao='bazar:carrinho'):
    destino = request.POST.get('next')
    if destino and url_has_allowed_host_and_scheme(destino, {request.get_host()}, request.is_secure()):
        return redirect(destino)
    return redirect(padrao)


def _quantidade(request, padrao=1):
    try:
        return max(0, int(request.POST.get('quantidade', padrao)))
    except (TypeError, ValueError):
        return padrao


@require_POST
def adicionar(request, produto_id):
    produto = get_object_or_404(Produto, pk=produto_id, ativo=True)
    carrinho = Carrinho(request)
    antes = carrinho.quantidade_de(produto)
    depois = carrinho.adicionar(produto, _quantidade(request))

    if produto.esgotado:
        messages.error(request, f'{produto.nome} acabou de esgotar.')
    elif depois == antes:
        messages.warning(request, f'Você já tem todas as unidades disponíveis de {produto.nome} no carrinho.')
    else:
        messages.success(request, f'{produto.nome} foi adicionado ao carrinho.')
    return _voltar(request)


@require_POST
def atualizar(request, produto_id):
    produto = get_object_or_404(Produto, pk=produto_id)
    Carrinho(request).adicionar(produto, _quantidade(request, padrao=0), substituir=True)
    return redirect('bazar:carrinho')


@require_POST
def remover(request, produto_id):
    Carrinho(request).remover(produto_id)
    messages.info(request, 'Produto removido do carrinho.')
    return redirect('bazar:carrinho')


def ver_carrinho(request):
    carrinho = Carrinho(request)
    form = FinalizarPedidoForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        _, avisos = carrinho.linhas()
        if avisos:
            # O carrinho mudou (algo esgotou): mostra os avisos para a pessoa revisar antes de finalizar
            for aviso in avisos:
                messages.warning(request, aviso)
            linhas, _ = carrinho.linhas()
            return render(request, 'bazar/carrinho.html', {'linhas': linhas, 'total': Carrinho.total(linhas), 'form': form})

        telefone = form.cleaned_data['telefone']
        pendentes = sum(
            1 for t in Pedido.objects.filter(status='pendente').values_list('telefone', flat=True)
            if apenas_digitos(t) == apenas_digitos(telefone)
        )
        if pendentes >= MAX_PEDIDOS_PENDENTES_POR_TELEFONE:
            messages.warning(
                request,
                f'Você já tem {pendentes} pedidos pendentes. Conclua ou cancele algum com a ONG antes de fazer outro.',
            )
        elif not len(carrinho):
            messages.warning(request, 'Seu carrinho está vazio.')
        else:
            try:
                pedido = carrinho.finalizar(
                    form.cleaned_data['nome'], telefone, form.cleaned_data['observacao']
                )
            except ProdutoIndisponivel as erro:
                messages.error(
                    request,
                    f'Que pena! {erro.produto.nome} esgotou enquanto você comprava. Revise o carrinho e tente de novo.',
                )
            else:
                return redirect('bazar:pedido', codigo=pedido.codigo)

    linhas, avisos = carrinho.linhas()
    for aviso in avisos:
        messages.warning(request, aviso)

    context = {'linhas': linhas, 'total': Carrinho.total(linhas), 'form': form}
    return render(request, 'bazar/carrinho.html', context)


def confirmacao_pedido(request, codigo):
    pedido = get_object_or_404(Pedido.objects.prefetch_related('itens'), codigo=codigo)
    return render(request, 'bazar/confirmacao_pedido.html', {'pedido': pedido})
