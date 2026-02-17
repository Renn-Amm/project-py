from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrAbove, IsDeveloperOrAbove, RoleBasedPermission
from apps.feature_flags.models import FeatureFlag, FlagStatus
from apps.feature_flags.serializers import (
    FeatureFlagCreateSerializer,
    FeatureFlagSerializer,
    FeatureFlagUpdateSerializer,
    SetVariantsSerializer,
    ToggleFlagSerializer,
)
from apps.feature_flags.services import FeatureFlagService, FlagVariantService
from apps.tenants.models import Environment


class FeatureFlagListView(generics.ListAPIView):
    serializer_class = FeatureFlagSerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]

    def get_queryset(self):
        qs = FeatureFlag.objects.filter(
            environment__tenant=self.request.user.tenant
        ).select_related("environment", "created_by", "depends_on").prefetch_related("variants")
        env = self.request.query_params.get("environment")
        if env:
            qs = qs.filter(environment__name=env)
        flag_status = self.request.query_params.get("status")
        if flag_status:
            qs = qs.filter(status=flag_status)
        return qs


class FeatureFlagCreateView(APIView):
    permission_classes = [IsAuthenticated, IsDeveloperOrAbove]

    def post(self, request):
        serializer = FeatureFlagCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            environment = Environment.objects.get(
                id=data["environment_id"],
                tenant=request.user.tenant,
            )
        except Environment.DoesNotExist:
            return Response(
                {"error": "Environment not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        depends_on = None
        if data.get("depends_on_id"):
            try:
                depends_on = FeatureFlag.objects.get(
                    id=data["depends_on_id"],
                    environment=environment,
                )
            except FeatureFlag.DoesNotExist:
                return Response(
                    {"error": "Dependency flag not found in this environment."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        try:
            flag = FeatureFlagService.create_flag(
                name=data["name"],
                key=data["key"],
                environment=environment,
                created_by=request.user,
                flag_type=data["flag_type"],
                description=data.get("description", ""),
                risk_level=data.get("risk_level", "low"),
                depends_on=depends_on,
                activate_at=data.get("activate_at"),
                expire_at=data.get("expire_at"),
            )
        except DjangoValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            FeatureFlagSerializer(flag).data,
            status=status.HTTP_201_CREATED,
        )


class FeatureFlagDetailView(APIView):
    permission_classes = [IsAuthenticated, RoleBasedPermission]

    def get_flag(self, pk, tenant):
        try:
            return FeatureFlag.objects.select_related(
                "environment", "created_by", "depends_on"
            ).prefetch_related("variants").get(
                pk=pk, environment__tenant=tenant
            )
        except FeatureFlag.DoesNotExist:
            return None

    def get(self, request, pk):
        flag = self.get_flag(pk, request.user.tenant)
        if not flag:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(FeatureFlagSerializer(flag).data)

    def patch(self, request, pk):
        flag = self.get_flag(pk, request.user.tenant)
        if not flag:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = FeatureFlagUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            flag = FeatureFlagService.update_flag(
                flag, request.user, **serializer.validated_data
            )
        except DjangoValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(FeatureFlagSerializer(flag).data)

    def delete(self, request, pk):
        flag = self.get_flag(pk, request.user.tenant)
        if not flag:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            FeatureFlagService.delete_flag(flag)
        except DjangoValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_204_NO_CONTENT)


class ToggleFlagView(APIView):
    permission_classes = [IsAuthenticated, IsDeveloperOrAbove]

    def post(self, request, pk):
        try:
            flag = FeatureFlag.objects.get(
                pk=pk, environment__tenant=request.user.tenant
            )
        except FeatureFlag.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ToggleFlagSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            flag = FeatureFlagService.toggle_flag(
                flag, serializer.validated_data["is_enabled"], request.user
            )
        except DjangoValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(FeatureFlagSerializer(flag).data)


class SetVariantsView(APIView):
    permission_classes = [IsAuthenticated, IsDeveloperOrAbove]

    def post(self, request, pk):
        try:
            flag = FeatureFlag.objects.get(
                pk=pk, environment__tenant=request.user.tenant
            )
        except FeatureFlag.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = SetVariantsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            variants = FlagVariantService.set_variants(
                flag, serializer.validated_data["variants"]
            )
        except DjangoValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        from apps.feature_flags.serializers import FlagVariantSerializer
        return Response(FlagVariantSerializer(variants, many=True).data)


class ArchiveFlagView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrAbove]

    def post(self, request, pk):
        try:
            flag = FeatureFlag.objects.get(
                pk=pk, environment__tenant=request.user.tenant
            )
        except FeatureFlag.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            flag = FeatureFlagService.archive_flag(flag)
        except DjangoValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(FeatureFlagSerializer(flag).data)


class KillSwitchView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrAbove]

    def post(self, request, pk):
        try:
            flag = FeatureFlag.objects.get(
                pk=pk, environment__tenant=request.user.tenant
            )
        except FeatureFlag.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get("action", "activate")
        if action == "activate":
            flag = FeatureFlagService.activate_kill_switch(flag)
        else:
            flag = FeatureFlagService.deactivate_kill_switch(flag)

        return Response(FeatureFlagSerializer(flag).data)


class StaleFlagsView(generics.ListAPIView):
    serializer_class = FeatureFlagSerializer
    permission_classes = [IsAuthenticated, IsAdminOrAbove]

    def get_queryset(self):
        from django.conf import settings
        days = int(self.request.query_params.get("days", settings.STALE_FLAG_DAYS))
        return FeatureFlagService.get_stale_flags(self.request.user.tenant, days)
