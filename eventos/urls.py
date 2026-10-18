from django.urls import path

from . import views

app_name = 'eventos'

urlpatterns = [
    path('', views.lista_eventos, name='lista'),
    path('encomenda/<uuid:codigo>/', views.confirmacao_encomenda, name='encomenda'),
    path('<slug:slug>/', views.detalhe_evento, name='detalhe'),
]
