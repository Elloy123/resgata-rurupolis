from django.urls import path

from . import views

app_name = 'doacoes'

urlpatterns = [
    path('', views.lista_campanhas, name='lista'),
    path('doar/', views.doar_geral, name='doar_geral'),
    path('obrigado/', views.doacao_obrigado, name='obrigado'),
    path('pendente/', views.doacao_pendente, name='pendente'),
    path('erro/', views.doacao_erro, name='erro'),
    path('webhook/mercadopago/', views.webhook_mercadopago, name='webhook_mercadopago'),
    path('<slug:slug>/', views.detalhe_campanha, name='detalhe'),
    path('<slug:slug>/doar/', views.doar_campanha, name='doar'),
]
