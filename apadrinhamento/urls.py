from django.urls import path

from . import views

app_name = 'apadrinhamento'

urlpatterns = [
    path('', views.lista_apadrinhamento, name='lista'),
    path('obrigado/', views.apadrinhamento_obrigado, name='obrigado'),
    path('webhook/mercadopago/', views.webhook_mercadopago, name='webhook_mercadopago'),
    path('<slug:slug>/', views.apadrinhar_animal, name='apadrinhar'),
]
