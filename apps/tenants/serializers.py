from rest_framework import serializers

from apps.tenants.models import Environment, Tenant


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ["id", "name", "slug", "subscription_plan", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class EnvironmentSerializer(serializers.ModelSerializer):
    is_production = serializers.ReadOnlyField()

    class Meta:
        model = Environment
        fields = ["id", "name", "tenant", "is_active", "is_production", "created_at"]
        read_only_fields = ["id", "created_at"]
