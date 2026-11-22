from __future__ import annotations

from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def healthz(_request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("admin/", admin.site.urls),
    # Single Source of Truth OpenAPI endpoints
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    # Versioned API v1 Modules
    path("api/v1/auth/", include("apps.identity.api.urls")),
    path("api/v1/corridor/", include("apps.corridor.api.urls")),
    path("api/v1/welfare/", include("apps.welfare.api.urls")),
    path("api/v1/ussd/", include("apps.ussd_gateway.urls")),
]
