import pytest
from datetime import date, timedelta
from django.core.exceptions import ValidationError

from apps.projects.models import Sprint
from apps.tasks.models import Task, TaskStatus
from apps.tasks.services import SprintAutoCloseService, TaskWorkflowService


@pytest.mark.django_db
class TestSprintModel:
    def test_create_sprint(self, project):
        sprint = Sprint.objects.create(
            project=project,
            name="Sprint 1",
            goal="Finish MVP",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=14),
        )
        assert sprint.name == "Sprint 1"
        assert sprint.is_closed is False

    def test_sprint_unique_name_per_project(self, project):
        Sprint.objects.create(
            project=project,
            name="Sprint 1",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=14),
        )
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            Sprint.objects.create(
                project=project,
                name="Sprint 1",
                start_date=date.today() + timedelta(days=15),
                end_date=date.today() + timedelta(days=28),
            )


@pytest.mark.django_db
class TestSprintAutoClose:
    def test_auto_close_expired_sprints(self, project):
        Sprint.objects.create(
            project=project,
            name="Past Sprint",
            start_date=date.today() - timedelta(days=28),
            end_date=date.today() - timedelta(days=1),
        )
        Sprint.objects.create(
            project=project,
            name="Active Sprint",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=14),
        )
        closed = SprintAutoCloseService.close_expired_sprints()
        assert closed == 1
        assert Sprint.objects.get(name="Past Sprint").is_closed is True
        assert Sprint.objects.get(name="Active Sprint").is_closed is False


@pytest.mark.django_db
class TestSprintEnforcement:
    def test_cannot_transition_in_closed_sprint(self, project_with_team, owner_user, developer_user):
        sprint = Sprint.objects.create(
            project=project_with_team,
            name="Closed Sprint",
            start_date=date.today() - timedelta(days=28),
            end_date=date.today() + timedelta(days=14),
            is_closed=True,
        )
        task = Task.objects.create(
            project=project_with_team,
            title="Sprint Task",
            assignee=developer_user,
            sprint=sprint,
            created_by=owner_user,
        )
        with pytest.raises(ValidationError, match="closed sprint"):
            TaskWorkflowService.transition(task=task, actor=developer_user, to_status=TaskStatus.IN_PROGRESS)

    def test_can_transition_in_open_sprint(self, project_with_team, owner_user, developer_user):
        sprint = Sprint.objects.create(
            project=project_with_team,
            name="Open Sprint",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=14),
        )
        task = Task.objects.create(
            project=project_with_team,
            title="Sprint Task",
            assignee=developer_user,
            sprint=sprint,
            created_by=owner_user,
        )
        result = TaskWorkflowService.transition(task=task, actor=developer_user, to_status=TaskStatus.IN_PROGRESS)
        assert result.task.status == TaskStatus.IN_PROGRESS
