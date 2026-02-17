from django.db import models


class TenantScopedQuerySet(models.QuerySet):
    """QuerySet that enforces tenant isolation at the query level."""

    def for_tenant(self, tenant):
        if tenant is None:
            return self.none()
        return self.filter(**{self._tenant_field: tenant})

    @property
    def _tenant_field(self):
        return getattr(self.model, "TENANT_FIELD", "environment__tenant")


class TenantScopedManager(models.Manager):
    """Manager that provides tenant-scoped queries by default."""

    def get_queryset(self):
        return TenantScopedQuerySet(self.model, using=self._db)

    def for_tenant(self, tenant):
        return self.get_queryset().for_tenant(tenant)
