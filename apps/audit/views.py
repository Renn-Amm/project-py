from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import IsAdminOrAbove
from apps.audit.models import ActivityEntry, AuditLog
from apps.audit.serializers import ActivityEntrySerializer, AuditLogSerializer


class AuditLogListView(generics.ListAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsAdminOrAbove]
    filterset_fields = ["action", "object_type"]

    def get_queryset(self):
        return AuditLog.objects.filter(
            organization=self.request.user.organization
        ).select_related("actor")


class AuditLogObjectView(generics.ListAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AuditLog.objects.filter(
            organization=self.request.user.organization,
            object_type=self.kwargs["object_type"],
            object_id=self.kwargs["object_id"],
        ).select_related("actor")


class ActivityFeedView(generics.ListAPIView):
    """List activity feed entries scoped to organization."""

    serializer_class = ActivityEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        org = getattr(self.request.user, "organization", None)
        if not org:
            return ActivityEntry.objects.none()
        return ActivityEntry.objects.filter(
            organization=org,
        ).select_related("actor", "task").order_by("-created_at")
