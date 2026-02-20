from django.contrib import admin
from django.urls import include, path

from apps.core.views import HealthCheckView, landing_page_view, signup_view

urlpatterns = [
    path("", landing_page_view, name="landing"),
    path("signup/", signup_view, name="signup"),
    path("admin/", admin.site.urls),
    path("api/health/", HealthCheckView.as_view(), name="health_check"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.projects.urls")),
    path("api/", include("apps.tasks.urls")),
    path("api/", include("apps.time_tracking.urls")),
    path("api/audit/", include("apps.audit.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/performance/", include("apps.performance.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
]
