from django.contrib import admin
from django.urls import include, path

from apps.core.views import HealthCheckView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", HealthCheckView.as_view(), name="health_check"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/tenants/", include("apps.tenants.urls")),
    path("api/flags/", include("apps.feature_flags.urls")),
    path("api/targeting/", include("apps.targeting.urls")),
    path("api/policies/", include("apps.policies.urls")),
    path("api/audit/", include("apps.audit.urls")),
    path("api/analytics/", include("apps.analytics.urls")),
    path("api/", include("apps.feature_flags.evaluation_urls")),
    path("dashboard/", include("apps.dashboard.urls")),
]
