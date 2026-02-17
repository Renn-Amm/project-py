from django.urls import path

from apps.targeting.views import (
    TargetingRuleCreateView,
    TargetingRuleDetailView,
    TargetingRuleListView,
)

urlpatterns = [
    path("rules/", TargetingRuleCreateView.as_view(), name="rule_create"),
    path("rules/<int:pk>/", TargetingRuleDetailView.as_view(), name="rule_detail"),
    path("flags/<int:flag_id>/rules/", TargetingRuleListView.as_view(), name="flag_rules"),
]
