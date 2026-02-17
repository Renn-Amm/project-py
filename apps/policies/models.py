from django.conf import settings
from django.db import models


class ApprovalStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class ApprovalRequest(models.Model):
    flag = models.ForeignKey(
        "feature_flags.FeatureFlag",
        on_delete=models.CASCADE,
        related_name="approval_requests",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="requested_approvals",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_approvals",
    )
    status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )
    change_description = models.TextField()
    change_payload = models.JSONField(
        default=dict,
        help_text="Serialized representation of the proposed change",
    )
    review_comment = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "policies_approvalrequest"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Approval for {self.flag.key} - {self.status}"


class Policy(models.Model):
    """Configurable policy rules per tenant."""

    class PolicyType(models.TextChoices):
        PRODUCTION_OWNER_ONLY = "production_owner_only", "Only Owner can modify production"
        PRODUCTION_APPROVAL = "production_approval", "Production flags require approval"
        ARCHIVED_IMMUTABLE = "archived_immutable", "Archived flags cannot be edited"
        KEY_IMMUTABLE = "key_immutable", "Key cannot change after creation"
        HIGH_RISK_DUAL_APPROVAL = "high_risk_dual_approval", "High risk flags need dual approval"

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="policies",
    )
    policy_type = models.CharField(max_length=50, choices=PolicyType.choices)
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "policies_policy"
        unique_together = [("tenant", "policy_type")]
        ordering = ["policy_type"]

    def __str__(self):
        return f"{self.tenant.name} - {self.policy_type}"
