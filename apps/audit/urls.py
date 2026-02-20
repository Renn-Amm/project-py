from django.urls import path

from apps.audit.views import ActivityFeedView, AuditLogListView, AuditLogObjectView

urlpatterns = [
    path("logs/", AuditLogListView.as_view(), name="audit_log_list"),
    path(
        "logs/<str:object_type>/<str:object_id>/",
        AuditLogObjectView.as_view(),
        name="audit_log_object",
    ),
    path("activity/", ActivityFeedView.as_view(), name="activity_feed"),
]
