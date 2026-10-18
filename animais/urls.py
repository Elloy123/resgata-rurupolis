from django.urls import path

from . import views

app_name = 'animais'

urlpatterns = [
    path('', views.lista_animais, name='lista'),
    path('<slug:slug>/', views.detalhe_animal, name='detalhe'),
]
