from django.urls import path

from apps.analytics.views import (
    ExperimentResultsView,
    FlagAnalyticsView,
    TenantAnalyticsView,
)

urlpatterns = [
    path("summary/", TenantAnalyticsView.as_view(), name="tenant_analytics"),
    path("flags/<int:pk>/", FlagAnalyticsView.as_view(), name="flag_analytics"),
    path("experiments/<int:pk>/", ExperimentResultsView.as_view(), name="experiment_results"),
]
