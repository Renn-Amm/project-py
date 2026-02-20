from rest_framework import serializers

from apps.time_tracking.models import TimeEntry


class TimeEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeEntry
        fields = ["id", "user", "task", "hours", "date", "created_at"]
        read_only_fields = ["id", "created_at", "user"]
