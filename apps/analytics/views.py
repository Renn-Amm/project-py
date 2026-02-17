from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrAbove
from apps.analytics.serializers import (
    AnalyticsSummarySerializer,
    ExperimentResultsSerializer,
    TenantAnalyticsSummarySerializer,
)
from apps.analytics.services import AnalyticsService
from apps.feature_flags.models import FeatureFlag


class FlagAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            flag = FeatureFlag.objects.get(
                pk=pk, environment__tenant=request.user.tenant
            )
        except FeatureFlag.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        days = int(request.query_params.get("days", 7))
        summary = AnalyticsService.get_flag_evaluation_summary(flag, days)
        serializer = AnalyticsSummarySerializer(summary)
        return Response(serializer.data)


class TenantAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrAbove]

    def get(self, request):
        days = int(request.query_params.get("days", 7))
        summary = AnalyticsService.get_tenant_analytics_summary(
            request.user.tenant, days
        )
        serializer = TenantAnalyticsSummarySerializer(summary)
        return Response(serializer.data)


class ExperimentResultsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            flag = FeatureFlag.objects.get(
                pk=pk, environment__tenant=request.user.tenant
            )
        except FeatureFlag.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        days = int(request.query_params.get("days", 30))
        results = AnalyticsService.get_experiment_results(flag, days)
        serializer = ExperimentResultsSerializer(results)
        return Response(serializer.data)
