from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.tasks.models import Task, TaskStatus, TaskStatusChange


@dataclass(frozen=True)
class TransitionResult:
    task: Task


class TaskWorkflowService:
    """Enforces backend-only workflow rules.

    All status changes must go through this service.
    """

    @staticmethod
    def validate_transition(*, task: Task, actor, to_status: str) -> None:
        from_status = task.status

        if from_status == TaskStatus.ARCHIVED:
            raise ValidationError("Archived tasks cannot change status.")

        if actor.organization_id != task.organization_id:
            raise ValidationError("Cross-organization access is not allowed.")

        # Viewer cannot change status
        if actor.role == UserRole.VIEWER:
            raise ValidationError("Viewer role cannot change task status.")

        # Owner override: can perform any transition (except archived protection above)
        if actor.role == UserRole.OWNER:
            return

        # Role restricted transitions (mandatory rules)
        if (
            from_status == TaskStatus.BACKLOG
            and to_status == TaskStatus.IN_PROGRESS
            and task.assignee_id != actor.id
        ):
            raise ValidationError("Only the Assignee can move a task to In Progress.")

        if (
            from_status == TaskStatus.IN_REVIEW
            and to_status == TaskStatus.APPROVED
            and task.reviewer_id != actor.id
        ):
            raise ValidationError("Only the Reviewer can approve a task.")

        if to_status == TaskStatus.ARCHIVED and actor.role != UserRole.PROJECT_MANAGER:
            raise ValidationError("Only the Project Manager can archive tasks.")

        # Cannot close task without review
        if to_status == TaskStatus.COMPLETED:
            if task.review_approved_at is None:
                raise ValidationError("Task cannot be completed without reviewer approval.")
            # Must have been In Review at some point
            has_in_review = TaskStatusChange.objects.filter(task=task, to_status=TaskStatus.IN_REVIEW).exists()
            if not has_in_review and from_status != TaskStatus.IN_REVIEW:
                raise ValidationError("Task must be in 'In Review' before it can be completed.")

    @staticmethod
    @transaction.atomic
    def transition(*, task: Task, actor, to_status: str) -> TransitionResult:
        locked = Task.objects.select_for_update().select_related("project", "project__organization").get(pk=task.pk)
        from_status = locked.status

        TaskWorkflowService.validate_transition(task=locked, actor=actor, to_status=to_status)

        # Side-effects
        if from_status == TaskStatus.IN_REVIEW and to_status == TaskStatus.APPROVED:
            locked.review_approved_at = timezone.now()
            locked.review_approved_by = actor

        if to_status == TaskStatus.COMPLETED:
            locked.completed_at = timezone.now()
            locked.is_overdue = False

        locked.status = to_status
        locked.save(update_fields=[
            "status",
            "completed_at",
            "is_overdue",
            "review_approved_at",
            "review_approved_by",
            "updated_at",
        ])

        TaskStatusChange.objects.create(
            task=locked,
            from_status=from_status,
            to_status=to_status,
            actor=actor,
        )

        return TransitionResult(task=locked)


class OverdueDetectionService:
    """Cron-friendly logic; called by management command."""

    @staticmethod
    def mark_overdue_tasks(*, organization_id: int | None = None) -> int:
        qs = Task.objects.select_related("project", "project__organization").all()
        if organization_id is not None:
            qs = qs.filter(project__organization_id=organization_id)

        now = timezone.now()
        candidates = qs.filter(
            deadline__isnull=False,
            deadline__lt=now,
        ).exclude(status=TaskStatus.COMPLETED)

        updated = 0
        for task in candidates:
            if task.mark_overdue_if_needed():
                task.save(update_fields=["is_overdue", "overdue_marked_at", "updated_at"])
                updated += 1
        return updated
