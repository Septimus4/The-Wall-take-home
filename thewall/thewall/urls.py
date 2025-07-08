"""
URL configuration for The Wall project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.profiles.urls", namespace="profiles")),
    path("health/", include("apps.health.urls")),
    path("", include("django_prometheus.urls")),
]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)  # type: ignore[arg-type]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # type: ignore[arg-type]
