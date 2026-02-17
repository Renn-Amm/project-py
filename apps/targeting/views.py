from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsDeveloperOrAbove
from apps.feature_flags.models import FeatureFlag, FlagStatus
from apps.targeting.models import TargetingRule
from apps.targeting.serializers import TargetingRuleCreateSerializer, TargetingRuleSerializer


class TargetingRuleListView(generics.ListAPIView):
    serializer_class = TargetingRuleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        flag_id = self.kwargs.get("flag_id")
        return TargetingRule.objects.filter(
            flag_id=flag_id,
            flag__environment__tenant=self.request.user.tenant,
        )


class TargetingRuleCreateView(APIView):
    permission_classes = [IsAuthenticated, IsDeveloperOrAbove]

    def post(self, request):
        serializer = TargetingRuleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            flag = FeatureFlag.objects.get(
                id=data["flag_id"],
                environment__tenant=request.user.tenant,
            )
        except FeatureFlag.DoesNotExist:
            return Response(
                {"error": "Flag not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if flag.status == FlagStatus.ARCHIVED:
            return Response(
                {"error": "Cannot add targeting rules to an archived flag."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rule = TargetingRule.objects.create(
            flag=flag,
            rule_type=data["rule_type"],
            attribute_key=data.get("attribute_key", ""),
            operator=data["operator"],
            value=data["value"],
            variant_value=data.get("variant_value"),
            priority=data.get("priority", 0),
        )
        return Response(
            TargetingRuleSerializer(rule).data,
            status=status.HTTP_201_CREATED,
        )


class TargetingRuleDetailView(APIView):
    permission_classes = [IsAuthenticated, IsDeveloperOrAbove]

    def get_rule(self, pk, tenant):
        try:
            return TargetingRule.objects.get(
                pk=pk,
                flag__environment__tenant=tenant,
            )
        except TargetingRule.DoesNotExist:
            return None

    def patch(self, request, pk):
        rule = self.get_rule(pk, request.user.tenant)
        if not rule:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        if rule.flag.status == FlagStatus.ARCHIVED:
            return Response(
                {"error": "Cannot modify targeting rules of an archived flag."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed_fields = ["operator", "value", "variant_value", "priority", "is_active", "attribute_key"]
        for field in allowed_fields:
            if field in request.data:
                setattr(rule, field, request.data[field])
        rule.save()
        return Response(TargetingRuleSerializer(rule).data)

    def delete(self, request, pk):
        rule = self.get_rule(pk, request.user.tenant)
        if not rule:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        rule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
