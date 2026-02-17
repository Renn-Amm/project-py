from django.db import models


class SubscriptionPlan(models.TextChoices):
    FREE = "free", "Free"
    STARTER = "starter", "Starter"
    PROFESSIONAL = "professional", "Professional"
    ENTERPRISE = "enterprise", "Enterprise"


class Tenant(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    subscription_plan = models.CharField(
        max_length=20,
        choices=SubscriptionPlan.choices,
        default=SubscriptionPlan.FREE,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tenants_tenant"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Environment(models.Model):
    class EnvironmentName(models.TextChoices):
        DEVELOPMENT = "development", "Development"
        STAGING = "staging", "Staging"
        PRODUCTION = "production", "Production"

    name = models.CharField(max_length=20, choices=EnvironmentName.choices)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="environments",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tenants_environment"
        unique_together = [("name", "tenant")]
        ordering = ["name"]

    def __str__(self):
        return f"{self.tenant.name} - {self.name}"

    @property
    def is_production(self):
        return self.name == self.EnvironmentName.PRODUCTION
