from rest_framework import serializers

from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(
        source="actor.email", read_only=True, default=None
    )

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor",
            "actor_email",
            "organization",
            "action",
            "object_type",
            "object_id",
            "object_repr",
            "metadata",
            "ip_address",
            "timestamp",
        ]
        read_only_fields = fields
