from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class FlagType(models.TextChoices):
    BOOLEAN = "boolean", "Boolean"
    MULTIVARIATE = "multivariate", "Multivariate"
    EXPERIMENT = "experiment", "Experiment"


class FlagStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"


class RiskLevel(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class FeatureFlag(models.Model):
    name = models.CharField(max_length=255)
    key = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, default="")
    flag_type = models.CharField(
        max_length=20,
        choices=FlagType.choices,
        default=FlagType.BOOLEAN,
    )
    status = models.CharField(
        max_length=20,
        choices=FlagStatus.choices,
        default=FlagStatus.ACTIVE,
    )
    risk_level = models.CharField(
        max_length=20,
        choices=RiskLevel.choices,
        default=RiskLevel.LOW,
    )
    environment = models.ForeignKey(
        "tenants.Environment",
        on_delete=models.CASCADE,
        related_name="flags",
    )
    is_enabled = models.BooleanField(default=False)
    # Time-based activation
    activate_at = models.DateTimeField(null=True, blank=True)
    expire_at = models.DateTimeField(null=True, blank=True)
    # Kill switch
    kill_switch = models.BooleanField(default=False)
    # Dependency
    depends_on = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dependents",
    )
    # Approval
    requires_approval = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_flags",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_flags",
    )
    version = models.PositiveIntegerField(default=1)
    last_evaluated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "feature_flags_featureflag"
        unique_together = [("key", "environment")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.key} ({self.environment})"

    def clean(self):
        if self.status == FlagStatus.ARCHIVED and self.is_enabled:
            raise ValidationError("Archived flags cannot be enabled.")
        if self.expire_at and self.activate_at and self.expire_at <= self.activate_at:
            raise ValidationError("Expiration must be after activation time.")
        if self.depends_on and self.depends_on.environment_id != self.environment_id:
            raise ValidationError("Dependency must be in the same environment.")
        if self.depends_on and self.depends_on_id == self.id:
            raise ValidationError("A flag cannot depend on itself.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def tenant(self):
        return self.environment.tenant

    @property
    def is_expired(self):
        if self.expire_at and timezone.now() >= self.expire_at:
            return True
        return False

    @property
    def is_within_activation_window(self):
        now = timezone.now()
        if self.activate_at and now < self.activate_at:
            return False
        if self.expire_at and now >= self.expire_at:
            return False
        return True

    @property
    def is_production(self):
        return self.environment.is_production

    @property
    def requires_dual_approval(self):
        return self.is_production and self.risk_level in (
            RiskLevel.HIGH,
            RiskLevel.CRITICAL,
        )


class FlagVariant(models.Model):
    flag = models.ForeignKey(
        FeatureFlag,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    name = models.CharField(max_length=255)
    value = models.JSONField()
    rollout_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    is_control = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "feature_flags_flagvariant"
        ordering = ["name"]

    def __str__(self):
        return f"{self.flag.key}:{self.name} ({self.rollout_percentage}%)"

    def clean(self):
        if self.rollout_percentage < 0 or self.rollout_percentage > 100:
            raise ValidationError("Rollout percentage must be between 0 and 100.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
