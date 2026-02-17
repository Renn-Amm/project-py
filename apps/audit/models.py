from django.conf import settings
from django.db import models


class AuditAction(models.TextChoices):
    CREATE = "create", "Create"
    UPDATE = "update", "Update"
    DELETE = "delete", "Delete"
    TOGGLE = "toggle", "Toggle"
    ARCHIVE = "archive", "Archive"
    APPROVE = "approve", "Approve"
    REJECT = "reject", "Reject"
    KILL_SWITCH = "kill_switch", "Kill Switch"
    ROLLBACK = "rollback", "Rollback"
    LOGIN = "login", "Login"


class AuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs",
    )
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="audit_logs",
        null=True,
    )
    action = models.CharField(max_length=30, choices=AuditAction.choices, db_index=True)
    object_type = models.CharField(max_length=100, db_index=True)
    object_id = models.CharField(max_length=100)
    object_repr = models.CharField(max_length=500, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_auditlog"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["tenant", "-timestamp"]),
            models.Index(fields=["object_type", "object_id"]),
        ]

    def __str__(self):
        return f"{self.actor} {self.action} {self.object_type}:{self.object_id}"
