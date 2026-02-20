from django.urls import path

from apps.dashboard.task_views import (
    activity_feed_view,
    audit_view,
    analytics_view,
    dashboard_home,
    invitation_create_view,
    invitation_list_view,
    notification_list_view,
    notification_mark_read_view,
    notifications_mark_all_read_view,
    performance_view,
    project_add_member_view,
    project_create_view,
    project_detail_view,
    project_list_view,
    project_remove_member_view,
    task_create_view,
    task_detail_view,
    task_transition_view,
    time_entry_create_view,
)
from apps.dashboard.views import login_view, logout_view

urlpatterns = [
    # Auth
    path("login/", login_view, name="dashboard_login"),
    path("logout/", logout_view, name="dashboard_logout"),
    # Dashboard
    path("", dashboard_home, name="dashboard_home"),
    path("analytics/", analytics_view, name="dashboard_analytics"),
    path("audit/", audit_view, name="dashboard_audit"),
    path("performance/", performance_view, name="dashboard_performance"),
    path("activity/", activity_feed_view, name="dashboard_activity"),
    # Invitations
    path("invitations/", invitation_list_view, name="dashboard_invitations"),
    path("invitations/create/", invitation_create_view, name="dashboard_invitation_create"),
    # Notifications
    path("notifications/", notification_list_view, name="dashboard_notifications"),
    path(
        "notifications/<int:pk>/read/",
        notification_mark_read_view,
        name="dashboard_notification_mark_read",
    ),
    path(
        "notifications/read-all/",
        notifications_mark_all_read_view,
        name="dashboard_notifications_mark_all_read",
    ),
    # Projects
    path("projects/", project_list_view, name="dashboard_projects"),
    path("projects/create/", project_create_view, name="dashboard_project_create"),
    path("projects/<int:pk>/", project_detail_view, name="dashboard_project_detail"),
    path(
        "projects/<int:pk>/members/add/",
        project_add_member_view,
        name="dashboard_project_add_member",
    ),
    path(
        "projects/<int:pk>/members/<int:member_id>/remove/",
        project_remove_member_view,
        name="dashboard_project_remove_member",
    ),
    # Tasks
    path(
        "projects/<int:project_pk>/tasks/create/",
        task_create_view,
        name="dashboard_task_create",
    ),
    path("tasks/<int:pk>/", task_detail_view, name="dashboard_task_detail"),
    path(
        "tasks/<int:pk>/transition/",
        task_transition_view,
        name="dashboard_task_transition",
    ),
    # Time entries
    path(
        "tasks/<int:task_pk>/time-entries/create/",
        time_entry_create_view,
        name="dashboard_time_entry_create",
    ),
]
