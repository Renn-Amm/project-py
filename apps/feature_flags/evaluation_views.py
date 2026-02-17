import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.analytics.services import AnalyticsService
from apps.feature_flags.models import FeatureFlag
from apps.feature_flags.serializers import (
    EvaluationRequestSerializer,
    EvaluationResponseSerializer,
)
from apps.feature_flags.services import EvaluationEngine
from apps.tenants.models import Environment

logger = logging.getLogger(__name__)


class EvaluateView(APIView):
    """SDK-compatible evaluation endpoint.

    Security notes:
    - AllowAny is intentional: SDKs call this without user auth.
    - Tenant identification via X-Tenant-Slug header (acts as API key scope).
    - Throttled aggressively to prevent abuse.
    - Response never exposes internal rule logic or targeting rule details.
    """
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "evaluation"

    def post(self, request):
        serializer = EvaluationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        tenant_slug = request.headers.get("X-Tenant-Slug", "").strip()
        if not tenant_slug:
            return Response(
                {"error": "X-Tenant-Slug header is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            environment = Environment.objects.select_related("tenant").get(
                name=data["environment"],
                tenant__slug=tenant_slug,
                tenant__is_active=True,
                is_active=True,
            )
        except Environment.DoesNotExist:
            return Response(
                {"error": "Environment or tenant not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            flag = (
                FeatureFlag.objects
                .select_related("depends_on", "environment")
                .prefetch_related("variants", "targeting_rules")
                .get(key=data["flag_key"], environment=environment)
            )
        except FeatureFlag.DoesNotExist:
            return Response(
                {"error": "Flag not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Use prefetched targeting_rules instead of a second query
        targeting_rules = sorted(
            flag.targeting_rules.all(),
            key=lambda r: r.priority,
        )

        result = EvaluationEngine.evaluate(
            flag=flag,
            user_identifier=data["user_identifier"],
            attributes=data.get("attributes", {}),
            targeting_rules=targeting_rules,
        )

        # Async-safe: fire-and-forget update (non-blocking for perf)
        FeatureFlag.objects.filter(pk=flag.pk).update(last_evaluated_at=timezone.now())

        try:
            AnalyticsService.record_evaluation(
                flag=flag,
                user_identifier=data["user_identifier"],
                variant=result["variant"],
                environment_name=data["environment"],
            )
        except Exception:
            logger.exception("Failed to record evaluation event for flag %s", flag.key)

        # Sanitize response: never expose rule_matched ID to SDK clients
        safe_result = {
            "variant": result["variant"],
            "reason": result["reason"],
            "rule_matched": None,
        }
        response_serializer = EvaluationResponseSerializer(safe_result)
        return Response(response_serializer.data)
