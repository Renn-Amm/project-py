from rest_framework import serializers

from apps.feature_flags.models import FeatureFlag, FlagVariant


class FlagVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlagVariant
        fields = [
            "id", "name", "value", "rollout_percentage", "is_control",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class FeatureFlagSerializer(serializers.ModelSerializer):
    variants = FlagVariantSerializer(many=True, read_only=True)
    is_expired = serializers.ReadOnlyField()
    is_within_activation_window = serializers.ReadOnlyField()
    requires_dual_approval = serializers.ReadOnlyField()

    class Meta:
        model = FeatureFlag
        fields = [
            "id", "name", "key", "description", "flag_type", "status",
            "risk_level", "environment", "is_enabled", "activate_at",
            "expire_at", "kill_switch", "depends_on", "requires_approval",
            "is_approved", "approved_by", "approved_at", "created_by",
            "version", "last_evaluated_at", "is_expired",
            "is_within_activation_window", "requires_dual_approval",
            "variants", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "version", "is_approved", "approved_by", "approved_at",
            "last_evaluated_at", "created_at", "updated_at",
        ]


class FeatureFlagCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    key = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, default="")
    flag_type = serializers.ChoiceField(
        choices=["boolean", "multivariate", "experiment"],
        default="boolean",
    )
    environment_id = serializers.IntegerField()
    risk_level = serializers.ChoiceField(
        choices=["low", "medium", "high", "critical"],
        default="low",
    )
    depends_on_id = serializers.IntegerField(required=False, allow_null=True)
    activate_at = serializers.DateTimeField(required=False, allow_null=True)
    expire_at = serializers.DateTimeField(required=False, allow_null=True)


class FeatureFlagUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False)
    is_enabled = serializers.BooleanField(required=False)
    risk_level = serializers.ChoiceField(
        choices=["low", "medium", "high", "critical"],
        required=False,
    )
    activate_at = serializers.DateTimeField(required=False, allow_null=True)
    expire_at = serializers.DateTimeField(required=False, allow_null=True)


class SetVariantsSerializer(serializers.Serializer):
    variants = FlagVariantSerializer(many=True)


class ToggleFlagSerializer(serializers.Serializer):
    is_enabled = serializers.BooleanField()


class EvaluationRequestSerializer(serializers.Serializer):
    flag_key = serializers.CharField(max_length=255)
    user_identifier = serializers.CharField(max_length=255)
    environment = serializers.CharField(max_length=20)
    attributes = serializers.DictField(required=False, default=dict)


class EvaluationResponseSerializer(serializers.Serializer):
    variant = serializers.JSONField(allow_null=True)
    reason = serializers.CharField()
    rule_matched = serializers.IntegerField(allow_null=True)
