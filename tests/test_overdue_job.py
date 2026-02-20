from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.tasks.models import Task, TaskStatus
from apps.tasks.services import TaskWorkflowService


@pytest.mark.django_db
class TestOverdueJob:
    def test_mark_overdue_marks_task_after_deadline(self, project_with_team, owner_user, developer_user):
        task = Task.objects.create(
            project=project_with_team,
            title="Overdue task",
            description="",
            assignee=developer_user,
            created_by=owner_user,
            deadline=timezone.now() - timedelta(days=1),
        )

        assert task.is_overdue is False

        call_command("mark_overdue_tasks")

        task.refresh_from_db()
        assert task.is_overdue is True
        assert task.overdue_marked_at is not None

    def test_mark_overdue_does_not_mark_completed_task(self, project_with_team, owner_user):
        task = Task.objects.create(
            project=project_with_team,
            title="Completed task",
            description="",
            created_by=owner_user,
            status=TaskStatus.COMPLETED,
            completed_at=timezone.now(),
            deadline=timezone.now() - timedelta(days=1),
        )

        call_command("mark_overdue_tasks")

        task.refresh_from_db()
        assert task.is_overdue is False

    def test_overdue_is_cleared_on_completion(self, project_with_team, owner_user, developer_user, reviewer_user):
        task = Task.objects.create(
            project=project_with_team,
            title="Task",
            description="",
            assignee=developer_user,
            reviewer=reviewer_user,
            created_by=owner_user,
            deadline=timezone.now() - timedelta(days=1),
        )

        call_command("mark_overdue_tasks")
        task.refresh_from_db()
        assert task.is_overdue is True

        TaskWorkflowService.transition(task=task, actor=owner_user, to_status=TaskStatus.IN_PROGRESS)
        TaskWorkflowService.transition(task=task, actor=owner_user, to_status=TaskStatus.IN_REVIEW)
        TaskWorkflowService.transition(task=task, actor=reviewer_user, to_status=TaskStatus.APPROVED)
        TaskWorkflowService.transition(task=task, actor=owner_user, to_status=TaskStatus.COMPLETED)

        task.refresh_from_db()
        assert task.status == TaskStatus.COMPLETED
        assert task.is_overdue is False
