from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class TaskPriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


PRIORITY_WEIGHTS: dict[str, int] = {
    TaskPriority.LOW: 1,
    TaskPriority.MEDIUM: 2,
    TaskPriority.HIGH: 3,
    TaskPriority.CRITICAL: 5,
}


class TaskStatus(models.TextChoices):
    BACKLOG = "backlog", "Backlog"
    IN_PROGRESS = "in_progress", "In Progress"
    IN_REVIEW = "in_review", "In Review"
    APPROVED = "approved", "Approved"
    COMPLETED = "completed", "Completed"
    BLOCKED = "blocked", "Blocked"
    ARCHIVED = "archived", "Archived"


class Task(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    priority = models.CharField(max_length=20, choices=TaskPriority.choices, default=TaskPriority.MEDIUM)
    status = models.CharField(max_length=20, choices=TaskStatus.choices, default=TaskStatus.BACKLOG)

    sprint = models.ForeignKey(
        "projects.Sprint",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )

    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="review_tasks",
    )

    deadline = models.DateTimeField(null=True, blank=True)
    estimated_time_hours = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    total_logged_time_hours = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    is_overdue = models.BooleanField(default=False)
    overdue_marked_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    completed_at = models.DateTimeField(null=True, blank=True)

    review_approved_at = models.DateTimeField(null=True, blank=True)
    review_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_tasks",
    )

    class Meta:
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["project", "assignee"]),
            models.Index(fields=["project", "reviewer"]),
            models.Index(fields=["deadline", "status"]),
            models.Index(fields=["sprint"]),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def organization_id(self):
        return self.project.organization_id

    def mark_overdue_if_needed(self) -> bool:
        if not self.deadline:
            return False
        if self.status == TaskStatus.COMPLETED:
            return False
        if timezone.now() <= self.deadline:
            return False
        if self.is_overdue:
            return False
        self.is_overdue = True
        self.overdue_marked_at = timezone.now()
        return True


class TaskStatusChange(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="status_changes")
    from_status = models.CharField(max_length=20, choices=TaskStatus.choices)
    to_status = models.CharField(max_length=20, choices=TaskStatus.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="task_status_changes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["task", "created_at"]),
            models.Index(fields=["to_status", "created_at"]),
        ]


class TaskDependency(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="dependencies")
    depends_on = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="dependents")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["task", "depends_on"], name="uniq_task_dependency"),
            models.CheckConstraint(
                check=~models.Q(task=models.F("depends_on")),
                name="no_self_dependency",
            ),
        ]
        indexes = [
            models.Index(fields=["task"]),
            models.Index(fields=["depends_on"]),
        ]

    def __str__(self) -> str:
        return f"Task {self.task_id} depends on {self.depends_on_id}"
