from decimal import Decimal

import pytest
from django.utils import timezone

from apps.tasks.models import Task, TaskStatus
from apps.tasks.services import TaskWorkflowService
from apps.performance.services import PerformanceScoreService


@pytest.mark.django_db
class TestPerformanceScore:
    def test_empty_metrics(self, organization, developer_user):
        metrics = PerformanceScoreService.calculate(developer_user, organization)
        assert metrics["tasks_completed"] == 0
        assert metrics["total_assigned"] == 0
        assert metrics["weighted_score"] == Decimal("0")

    def test_completed_task_scoring(self, project_with_team, developer_user, reviewer_user, owner_user, organization):
        task = Task.objects.create(
            project=project_with_team,
            title="Score Task",
            assignee=developer_user,
            reviewer=reviewer_user,
            priority="high",
            estimated_time_hours=Decimal("8.00"),
            created_by=owner_user,
        )
        # Complete the task
        TaskWorkflowService.transition(task=task, actor=developer_user, to_status=TaskStatus.IN_PROGRESS)
        TaskWorkflowService.transition(task=task, actor=owner_user, to_status=TaskStatus.IN_REVIEW)
        TaskWorkflowService.transition(task=task, actor=reviewer_user, to_status=TaskStatus.APPROVED)
        TaskWorkflowService.transition(task=task, actor=owner_user, to_status=TaskStatus.COMPLETED)

        metrics = PerformanceScoreService.calculate(developer_user, organization)
        assert metrics["tasks_completed"] == 1
        assert metrics["total_assigned"] == 1
        assert metrics["weighted_score"] > 0

    def test_overdue_affects_score(self, project_with_team, developer_user, owner_user, organization):
        _task = Task.objects.create(
            project=project_with_team,
            title="Overdue Task",
            assignee=developer_user,
            deadline=timezone.now() - timezone.timedelta(days=1),
            is_overdue=True,
            overdue_marked_at=timezone.now(),
            created_by=owner_user,
        )
        metrics = PerformanceScoreService.calculate(developer_user, organization)
        assert metrics["overdue_rate"] > 0
        assert metrics["total_assigned"] == 1

    def test_multiple_tasks_scoring(self, project_with_team, developer_user, reviewer_user, owner_user, organization):
        for i in range(3):
            task = Task.objects.create(
                project=project_with_team,
                title=f"Task {i}",
                assignee=developer_user,
                reviewer=reviewer_user,
                created_by=owner_user,
            )
            TaskWorkflowService.transition(task=task, actor=developer_user, to_status=TaskStatus.IN_PROGRESS)
            TaskWorkflowService.transition(task=task, actor=owner_user, to_status=TaskStatus.IN_REVIEW)
            TaskWorkflowService.transition(task=task, actor=reviewer_user, to_status=TaskStatus.APPROVED)
            TaskWorkflowService.transition(task=task, actor=owner_user, to_status=TaskStatus.COMPLETED)

        metrics = PerformanceScoreService.calculate(developer_user, organization)
        assert metrics["tasks_completed"] == 3
        assert metrics["weighted_score"] > 0


@pytest.mark.django_db
class TestPerformanceAPI:
    def test_get_own_score(self, developer_client, organization):
        resp = developer_client.get("/api/performance/score/")
        assert resp.status_code == 200
        assert "weighted_score" in resp.data

    def test_team_scores(self, authenticated_client, organization):
        resp = authenticated_client.get("/api/performance/team/")
        assert resp.status_code == 200
        assert isinstance(resp.data, list)

    def test_get_other_user_score(self, authenticated_client, developer_user, organization):
        resp = authenticated_client.get(f"/api/performance/score/?user_id={developer_user.id}")
        assert resp.status_code == 200
        assert resp.data["user_id"] == developer_user.id

    def test_other_org_user_not_found(self, authenticated_client, other_org_owner_user):
        resp = authenticated_client.get(f"/api/performance/score/?user_id={other_org_owner_user.id}")
        assert resp.status_code == 404
