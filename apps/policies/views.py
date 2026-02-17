from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrAbove, IsDeveloperOrAbove
from apps.feature_flags.models import FeatureFlag
from apps.policies.models import ApprovalRequest, Policy
from apps.policies.serializers import (
    ApprovalActionSerializer,
    ApprovalRequestSerializer,
    PolicySerializer,
)
from apps.policies.services import ApprovalService


class PolicyListView(generics.ListAPIView):
    serializer_class = PolicySerializer
    permission_classes = [IsAuthenticated, IsAdminOrAbove]

    def get_queryset(self):
        return Policy.objects.filter(tenant=self.request.user.tenant)


class PolicyToggleView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrAbove]

    def post(self, request, pk):
        try:
            policy = Policy.objects.get(pk=pk, tenant=request.user.tenant)
        except Policy.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        policy.is_enabled = not policy.is_enabled
        policy.save(update_fields=["is_enabled", "updated_at"])
        return Response(PolicySerializer(policy).data)


class ApprovalRequestCreateView(APIView):
    permission_classes = [IsAuthenticated, IsDeveloperOrAbove]

    def post(self, request):
        flag_id = request.data.get("flag_id")
        change_description = request.data.get("change_description", "")
        change_payload = request.data.get("change_payload", {})

        try:
            flag = FeatureFlag.objects.get(
                id=flag_id,
                environment__tenant=request.user.tenant,
            )
        except FeatureFlag.DoesNotExist:
            return Response(
                {"error": "Flag not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            approval = ApprovalService.create_approval_request(
                flag=flag,
                requested_by=request.user,
                change_description=change_description,
                change_payload=change_payload,
            )
        except DjangoValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            ApprovalRequestSerializer(approval).data,
            status=status.HTTP_201_CREATED,
        )


class ApprovalQueueView(generics.ListAPIView):
    serializer_class = ApprovalRequestSerializer
    permission_classes = [IsAuthenticated, IsAdminOrAbove]

    def get_queryset(self):
        return ApprovalService.get_pending_approvals(self.request.user.tenant)


class ApproveRequestView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrAbove]

    def post(self, request, pk):
        try:
            approval_request = ApprovalRequest.objects.get(
                pk=pk,
                flag__environment__tenant=request.user.tenant,
            )
        except ApprovalRequest.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            approval = ApprovalService.approve_request(
                approval_request,
                reviewer=request.user,
                comment=serializer.validated_data.get("comment", ""),
            )
        except DjangoValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ApprovalRequestSerializer(approval).data)


class RejectRequestView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrAbove]

    def post(self, request, pk):
        try:
            approval_request = ApprovalRequest.objects.get(
                pk=pk,
                flag__environment__tenant=request.user.tenant,
            )
        except ApprovalRequest.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            approval = ApprovalService.reject_request(
                approval_request,
                reviewer=request.user,
                comment=serializer.validated_data.get("comment", ""),
            )
        except DjangoValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ApprovalRequestSerializer(approval).data)
