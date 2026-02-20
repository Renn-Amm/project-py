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
    organization = models.ForeignKey(
        "organizations.Organization",
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
            models.Index(fields=["organization", "-timestamp"]),
            models.Index(fields=["object_type", "object_id"]),
        ]

    def __str__(self):
        return f"{self.actor} {self.action} {self.object_type}:{self.object_id}"


class ActivityType(models.TextChoices):
    STATUS_CHANGE = "status_change", "Status Change"
    TIME_LOGGED = "time_logged", "Time Logged"
    REVIEW_SUBMITTED = "review_submitted", "Review Submitted"
    ASSIGNMENT_CHANGED = "assignment_changed", "Assignment Changed"
    TASK_CREATED = "task_created", "Task Created"
    COMMENT_ADDED = "comment_added", "Comment Added"


class ActivityEntry(models.Model):
    """Immutable activity feed entry — append-only audit trail."""

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="activity_entries",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="activity_entries",
    )
    activity_type = models.CharField(
        max_length=30,
        choices=ActivityType.choices,
        db_index=True,
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activity_entries",
    )
    description = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "-created_at"]),
            models.Index(fields=["task", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.activity_type}: {self.description[:50]}"
