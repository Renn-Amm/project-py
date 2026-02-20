from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.performance.services import PerformanceScoreService

User = get_user_model()


class PerformanceScoreView(APIView):
    """Get performance score for the authenticated user or a specified org member."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = getattr(request.user, "organization", None)
        if not org:
            return Response(
                {"error": "No organization found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_id = request.query_params.get("user_id")
        if user_id:
            try:
                target_user = User.objects.get(pk=user_id, organization=org)
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found in your organization."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            target_user = request.user

        metrics = PerformanceScoreService.calculate(target_user, org)
        metrics["user_id"] = target_user.id
        metrics["email"] = target_user.email
        return Response(metrics)


class TeamPerformanceView(APIView):
    """Get performance scores for all members of the organization."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = getattr(request.user, "organization", None)
        if not org:
            return Response([])

        users = User.objects.filter(organization=org, is_active=True)
        results = []
        for user in users:
            metrics = PerformanceScoreService.calculate(user, org)
            metrics["user_id"] = user.id
            metrics["email"] = user.email
            results.append(metrics)

        results.sort(key=lambda x: x["weighted_score"], reverse=True)
        return Response(results)
