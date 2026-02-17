from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrAbove, IsOwner
from apps.tenants.models import Environment, Tenant
from apps.tenants.serializers import EnvironmentSerializer, TenantSerializer
from apps.tenants.services import TenantService


class TenantCreateView(APIView):
    permission_classes = [IsOwner]

    def post(self, request):
        serializer = TenantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant = TenantService.create_tenant(
            name=serializer.validated_data["name"],
            subscription_plan=serializer.validated_data.get("subscription_plan", "free"),
        )
        return Response(TenantSerializer(tenant).data, status=status.HTTP_201_CREATED)


class TenantDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = TenantSerializer
    permission_classes = [IsAdminOrAbove]

    def get_queryset(self):
        return Tenant.objects.filter(id=self.request.user.tenant_id)


class EnvironmentListView(generics.ListAPIView):
    serializer_class = EnvironmentSerializer
    permission_classes = [IsAdminOrAbove]

    def get_queryset(self):
        return Environment.objects.filter(tenant=self.request.user.tenant)
