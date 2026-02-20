from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "recipient",
            "organization",
            "notification_type",
            "title",
            "message",
            "is_read",
            "related_task",
            "created_at",
        ]
        read_only_fields = fields
