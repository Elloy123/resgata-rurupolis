from django.urls import path

from . import views

app_name = 'bazar'

urlpatterns = [
    path('', views.lista_produtos, name='lista'),
    path('produto/<slug:slug>/', views.detalhe_produto, name='produto'),
    path('carrinho/', views.ver_carrinho, name='carrinho'),
    path('carrinho/adicionar/<int:produto_id>/', views.adicionar, name='adicionar'),
    path('carrinho/atualizar/<int:produto_id>/', views.atualizar, name='atualizar'),
    path('carrinho/remover/<int:produto_id>/', views.remover, name='remover'),
    path('pedido/<uuid:codigo>/', views.confirmacao_pedido, name='pedido'),
]
