from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import IsAdminOrAbove
from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer


class AuditLogListView(generics.ListAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsAdminOrAbove]
    filterset_fields = ["action", "object_type"]

    def get_queryset(self):
        return AuditLog.objects.filter(
            tenant=self.request.user.tenant
        ).select_related("actor")


class AuditLogObjectView(generics.ListAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AuditLog.objects.filter(
            tenant=self.request.user.tenant,
            object_type=self.kwargs["object_type"],
            object_id=self.kwargs["object_id"],
        ).select_related("actor")
