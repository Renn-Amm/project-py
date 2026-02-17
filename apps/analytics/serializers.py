from rest_framework import serializers

from apps.analytics.models import EvaluationEvent


class EvaluationEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationEvent
        fields = [
            "id", "flag", "flag_key", "user_identifier",
            "evaluated_variant", "environment_name", "timestamp",
        ]
        read_only_fields = fields


class AnalyticsSummarySerializer(serializers.Serializer):
    total_evaluations = serializers.IntegerField()
    unique_users = serializers.IntegerField()
    variant_distribution = serializers.ListField(required=False)
    daily_counts = serializers.ListField(required=False)
    period_days = serializers.IntegerField()


class TenantAnalyticsSummarySerializer(serializers.Serializer):
    total_evaluations = serializers.IntegerField()
    unique_users = serializers.IntegerField()
    unique_flags = serializers.IntegerField()
    hourly_counts = serializers.ListField(required=False)
    top_flags = serializers.ListField(required=False)
    period_days = serializers.IntegerField()


class ExperimentResultsSerializer(serializers.Serializer):
    flag_key = serializers.CharField()
    total_evaluations = serializers.IntegerField()
    variant_stats = serializers.ListField()
    period_days = serializers.IntegerField()
