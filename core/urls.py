from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('sobre/', views.sobre, name='sobre'),
    path('telefones-uteis/', views.telefones_uteis, name='telefones'),
    path('webhook/mercadopago/', views.webhook_mercadopago, name='webhook_mercadopago'),
]
