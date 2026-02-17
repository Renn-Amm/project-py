from django.urls import path

from apps.dashboard.views import (
    analytics_view,
    approval_action_view,
    approval_queue_view,
    audit_log_view,
    dashboard_home,
    flag_archive_view,
    flag_create_view,
    flag_detail_view,
    flag_kill_switch_view,
    flag_list_view,
    flag_toggle_view,
    flag_variants_view,
    login_view,
    logout_view,
    request_approval_view,
    rule_create_view,
    rule_delete_view,
)

urlpatterns = [
    # Auth
    path("login/", login_view, name="dashboard_login"),
    path("logout/", logout_view, name="dashboard_logout"),

    # Dashboard
    path("", dashboard_home, name="dashboard_home"),

    # Flags
    path("flags/", flag_list_view, name="dashboard_flags"),
    path("flags/create/", flag_create_view, name="dashboard_flag_create"),
    path("flags/<int:pk>/", flag_detail_view, name="dashboard_flag_detail"),
    path("flags/<int:pk>/toggle/", flag_toggle_view, name="dashboard_flag_toggle"),
    path("flags/<int:pk>/archive/", flag_archive_view, name="dashboard_flag_archive"),
    path("flags/<int:pk>/kill-switch/", flag_kill_switch_view, name="dashboard_flag_kill_switch"),
    path("flags/<int:pk>/variants/", flag_variants_view, name="dashboard_flag_variants"),
    path("flags/<int:flag_pk>/rules/add/", rule_create_view, name="dashboard_rule_create"),
    path("flags/<int:flag_pk>/request-approval/", request_approval_view, name="dashboard_request_approval"),

    # Targeting rules
    path("rules/<int:rule_pk>/delete/", rule_delete_view, name="dashboard_rule_delete"),

    # Approvals
    path("approvals/", approval_queue_view, name="dashboard_approvals"),
    path("approvals/<int:pk>/action/", approval_action_view, name="dashboard_approval_action"),

    # Audit & Analytics
    path("audit/", audit_log_view, name="dashboard_audit"),
    path("analytics/", analytics_view, name="dashboard_analytics"),
]
