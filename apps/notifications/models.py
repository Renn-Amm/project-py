from django.conf import settings
from django.db import models


class NotificationType(models.TextChoices):
    TASK_ASSIGNED = "task_assigned", "Task Assigned"
    MOVED_TO_REVIEW = "moved_to_review", "Moved to Review"
    REVIEW_REJECTED = "review_rejected", "Review Rejected"
    OVERDUE_DETECTED = "overdue_detected", "Overdue Detected"


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        db_index=True,
    )
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    related_task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["organization", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.notification_type}: {self.title}"
