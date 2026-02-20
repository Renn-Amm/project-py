from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer
from apps.notifications.services import NotificationService


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        org = getattr(self.request.user, "organization", None)
        if not org:
            return Notification.objects.none()
        return Notification.objects.filter(
            recipient=self.request.user,
            organization=org,
        ).order_by("-created_at")


class NotificationMarkReadView(APIView):
    def post(self, request, pk):
        success = NotificationService.mark_as_read(pk, request.user)
        if not success:
            return Response(
                {"error": "Notification not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"message": "Marked as read."})


class NotificationMarkAllReadView(APIView):
    def post(self, request):
        org = getattr(request.user, "organization", None)
        if not org:
            return Response({"updated": 0})
        updated = Notification.objects.filter(
            recipient=request.user,
            organization=org,
            is_read=False,
        ).update(is_read=True)
        return Response({"updated": updated})
