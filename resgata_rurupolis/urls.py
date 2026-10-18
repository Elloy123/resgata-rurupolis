from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('animais/', include('animais.urls')),
    path('vaquinhas/', include('doacoes.urls')),
    path('apadrinhamento/', include('apadrinhamento.urls')),
    path('eventos/', include('eventos.urls')),
    path('bazar/', include('bazar.urls')),
    path('', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
