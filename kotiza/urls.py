"""Configuration des URLs pour le projet Kotiza.

Ce module définit la configuration principale des URLs du projet,
incluant les routes pour l'admin, l'API REST, l'interface web,
l'authentification et les handlers d'erreurs personnalisés.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from core.views import healthcheck

from . import error_views

urlpatterns = [
    path('health/', healthcheck, name='healthcheck'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain'), name='robots'),
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    # Application URLs
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    path('', include('core.web_urls')),
    path('accounts/', include('django.contrib.auth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler400 = "kotiza.error_views.bad_request"
handler403 = "kotiza.error_views.permission_denied"
handler404 = "kotiza.error_views.page_not_found"
handler500 = "kotiza.error_views.server_error"
