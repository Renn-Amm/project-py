from django.urls import path

from apps.feature_flags.views import (
    ArchiveFlagView,
    FeatureFlagCreateView,
    FeatureFlagDetailView,
    FeatureFlagListView,
    KillSwitchView,
    SetVariantsView,
    StaleFlagsView,
    ToggleFlagView,
)

urlpatterns = [
    path("", FeatureFlagListView.as_view(), name="flag_list"),
    path("create/", FeatureFlagCreateView.as_view(), name="flag_create"),
    path("<int:pk>/", FeatureFlagDetailView.as_view(), name="flag_detail"),
    path("<int:pk>/toggle/", ToggleFlagView.as_view(), name="flag_toggle"),
    path("<int:pk>/variants/", SetVariantsView.as_view(), name="flag_variants"),
    path("<int:pk>/archive/", ArchiveFlagView.as_view(), name="flag_archive"),
    path("<int:pk>/kill-switch/", KillSwitchView.as_view(), name="flag_kill_switch"),
    path("stale/", StaleFlagsView.as_view(), name="stale_flags"),
]
