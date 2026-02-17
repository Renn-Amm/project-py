from django.db import transaction
from django.utils.text import slugify

from apps.tenants.models import Environment, Tenant


class TenantService:
    @staticmethod
    @transaction.atomic
    def create_tenant(name, subscription_plan="free"):
        slug = slugify(name)
        tenant = Tenant.objects.create(
            name=name,
            slug=slug,
            subscription_plan=subscription_plan,
        )
        for env_name in Environment.EnvironmentName.values:
            Environment.objects.create(name=env_name, tenant=tenant)
        return tenant

    @staticmethod
    def get_tenant_environments(tenant):
        return Environment.objects.filter(tenant=tenant)

    @staticmethod
    def deactivate_tenant(tenant):
        tenant.is_active = False
        tenant.save(update_fields=["is_active", "updated_at"])
        return tenant
