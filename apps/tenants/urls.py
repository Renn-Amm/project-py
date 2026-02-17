from django.urls import path

from apps.tenants.views import EnvironmentListView, TenantCreateView, TenantDetailView

urlpatterns = [
    path("", TenantCreateView.as_view(), name="tenant_create"),
    path("<int:pk>/", TenantDetailView.as_view(), name="tenant_detail"),
    path("environments/", EnvironmentListView.as_view(), name="environment_list"),
]
