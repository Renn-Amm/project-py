from rest_framework import serializers

from apps.policies.models import ApprovalRequest, Policy


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = ["id", "tenant", "policy_type", "is_enabled", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ApprovalRequestSerializer(serializers.ModelSerializer):
    requested_by_email = serializers.EmailField(source="requested_by.email", read_only=True)
    reviewed_by_email = serializers.EmailField(
        source="reviewed_by.email", read_only=True, default=None
    )
    flag_key = serializers.CharField(source="flag.key", read_only=True)

    class Meta:
        model = ApprovalRequest
        fields = [
            "id", "flag", "flag_key", "requested_by", "requested_by_email",
            "reviewed_by", "reviewed_by_email", "status",
            "change_description", "change_payload", "review_comment",
            "created_at", "reviewed_at",
        ]
        read_only_fields = [
            "id", "reviewed_by", "status", "reviewed_at", "created_at",
        ]


class ApprovalActionSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, default="")
