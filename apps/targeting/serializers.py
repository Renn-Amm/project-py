from rest_framework import serializers

from apps.targeting.models import TargetingRule


class TargetingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TargetingRule
        fields = [
            "id", "flag", "rule_type", "attribute_key", "operator",
            "value", "variant_value", "priority", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TargetingRuleCreateSerializer(serializers.Serializer):
    flag_id = serializers.IntegerField()
    rule_type = serializers.ChoiceField(
        choices=["user_id", "role", "country", "custom_attribute", "email", "percentage"]
    )
    attribute_key = serializers.CharField(required=False, default="")
    operator = serializers.ChoiceField(
        choices=[
            "equals", "not_equals", "contains", "not_contains",
            "greater_than", "less_than", "in_list", "not_in_list",
            "starts_with", "ends_with", "regex",
        ]
    )
    value = serializers.JSONField()
    variant_value = serializers.JSONField(required=False, allow_null=True)
    priority = serializers.IntegerField(default=0)
