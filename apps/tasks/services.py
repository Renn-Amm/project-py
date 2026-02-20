from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.audit.models import ActivityType
from apps.audit.services import ActivityFeedService
from apps.notifications.services import NotificationService
from apps.tasks.models import Task, TaskDependency, TaskStatus, TaskStatusChange


@dataclass(frozen=True)
class TransitionResult:
    task: Task


class DependencyService:
    """Manages task dependencies with circular-detection."""

    @staticmethod
    def _has_path(start_id: int, target_id: int, visited: set[int] | None = None) -> bool:
        """DFS to detect if there is a path from start to target through dependencies."""
        if visited is None:
            visited = set()
        if start_id == target_id:
            return True
        if start_id in visited:
            return False
        visited.add(start_id)
        deps = TaskDependency.objects.filter(task_id=start_id).values_list("depends_on_id", flat=True)
        for dep_id in deps:
            if DependencyService._has_path(dep_id, target_id, visited):
                return True
        return False

    @staticmethod
    @transaction.atomic
    def add_dependency(*, task: Task, depends_on: Task, actor) -> TaskDependency:
        if task.pk == depends_on.pk:
            raise ValidationError("A task cannot depend on itself.")

        if task.project_id != depends_on.project_id:
            raise ValidationError("Dependencies must be within the same project.")

        if actor.organization_id != task.organization_id:
            raise ValidationError("Cross-organization access is not allowed.")

        # Circular dependency check: would adding depends_on→task create a cycle?
        if DependencyService._has_path(depends_on.pk, task.pk):
            raise ValidationError("This would create a circular dependency.")

        dep, created = TaskDependency.objects.get_or_create(task=task, depends_on=depends_on)
        if not created:
            raise ValidationError("This dependency already exists.")

        return dep

    @staticmethod
    @transaction.atomic
    def remove_dependency(*, task: Task, depends_on: Task, actor) -> None:
        if actor.organization_id != task.organization_id:
            raise ValidationError("Cross-organization access is not allowed.")

        deleted, _ = TaskDependency.objects.filter(task=task, depends_on=depends_on).delete()
        if not deleted:
            raise ValidationError("Dependency not found.")


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
            # Even owner must pass dependency check for IN_PROGRESS
            if to_status == TaskStatus.IN_PROGRESS:
                TaskWorkflowService._check_dependencies(task)
            # Even owner must pass sprint check
            if task.sprint_id:
                TaskWorkflowService._check_sprint(task)
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

        # Dependency enforcement: cannot move to IN_PROGRESS with incomplete deps
        if to_status == TaskStatus.IN_PROGRESS:
            TaskWorkflowService._check_dependencies(task)

        # Sprint enforcement
        if task.sprint_id:
            TaskWorkflowService._check_sprint(task)

    @staticmethod
    def _check_dependencies(task: Task) -> None:
        """Cannot start a task if any dependency is not completed."""
        incomplete_deps = TaskDependency.objects.filter(
            task=task,
        ).exclude(
            depends_on__status=TaskStatus.COMPLETED,
        )
        if incomplete_deps.exists():
            raise ValidationError("Cannot start task: some dependencies are not completed.")

    @staticmethod
    def _check_sprint(task: Task) -> None:
        """Cannot move a task in a closed sprint."""
        from apps.projects.models import Sprint

        try:
            sprint = Sprint.objects.get(pk=task.sprint_id)
        except Sprint.DoesNotExist:
            return
        if sprint.is_closed:
            raise ValidationError("Cannot change task status in a closed sprint.")

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

        # Activity feed
        ActivityFeedService.record(
            organization=locked.project.organization,
            actor=actor,
            activity_type=ActivityType.STATUS_CHANGE,
            task=locked,
            description=f"Status changed from {from_status} to {to_status}",
            metadata={"from_status": from_status, "to_status": to_status},
        )

        # Notifications
        if to_status == TaskStatus.IN_REVIEW:
            NotificationService.notify_moved_to_review(task=locked)
        if from_status == TaskStatus.IN_REVIEW and to_status == TaskStatus.BACKLOG:
            NotificationService.notify_review_rejected(task=locked, actor=actor)

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
                NotificationService.notify_overdue(task=task)
                updated += 1
        return updated


class SprintAutoCloseService:
    """Closes sprints that have passed their end date."""

    @staticmethod
    def close_expired_sprints() -> int:
        from apps.projects.models import Sprint

        today = timezone.now().date()
        return Sprint.objects.filter(
            is_closed=False,
            end_date__lt=today,
        ).update(is_closed=True)
