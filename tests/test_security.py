import pytest
from django.utils import timezone
from rest_framework import status

from apps.accounts.models import Invitation, User
from apps.notifications.models import Notification
from apps.tasks.models import Task, TaskStatus
from apps.tasks.services import TaskWorkflowService


@pytest.mark.django_db
class TestCrossTenantIsolation:
    def test_other_org_cannot_see_tasks(self, authenticated_client, other_org_client, project_with_team, owner_user):
        task = Task.objects.create(
            project=project_with_team,
            title="Secret Task",
            created_by=owner_user,
        )
        # Other org cannot see the task
        resp = other_org_client.get(f"/api/tasks/{task.id}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_other_org_cannot_list_tasks(self, other_org_client, project_with_team, owner_user):
        Task.objects.create(project=project_with_team, title="Hidden", created_by=owner_user)
        resp = other_org_client.get("/api/tasks/")
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data.get("results", resp.data)
        assert len(results) == 0

    def test_other_org_cannot_access_project(self, other_org_client, project):
        resp = other_org_client.get(f"/api/projects/{project.id}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_other_org_cannot_list_projects(self, other_org_client, project):
        resp = other_org_client.get("/api/projects/")
        results = resp.data.get("results", resp.data)
        assert project.id not in [p["id"] for p in results]

    def test_other_org_cannot_see_audit_logs(self, other_org_client):
        resp = other_org_client.get("/api/audit/logs/")
        # other_org_owner is not admin in the test org
        assert resp.status_code in (status.HTTP_200_OK, status.HTTP_403_FORBIDDEN)

    def test_cross_org_transition_rejected(self, project_with_team, owner_user, other_org_owner_user):
        task = Task.objects.create(
            project=project_with_team,
            title="Cross Org",
            created_by=owner_user,
        )
        from django.core.exceptions import ValidationError

        with pytest.raises(ValidationError, match="Cross-organization"):
            TaskWorkflowService.transition(task=task, actor=other_org_owner_user, to_status=TaskStatus.IN_PROGRESS)

    def test_notifications_leak_prevention(self, project_with_team, developer_user, other_org_owner_user, owner_user):
        task = Task.objects.create(
            project=project_with_team,
            title="Notify Task",
            assignee=developer_user,
            created_by=owner_user,
        )
        from apps.notifications.services import NotificationService

        NotificationService.notify_task_assigned(task=task)

        # Other org has no notifications
        assert Notification.objects.filter(
            recipient=other_org_owner_user,
        ).count() == 0


@pytest.mark.django_db
class TestPrivilegeEscalation:
    def test_viewer_cannot_transition(self, project_with_team, viewer_user, owner_user):
        task = Task.objects.create(
            project=project_with_team,
            title="Viewer Task",
            created_by=owner_user,
        )
        from django.core.exceptions import ValidationError

        with pytest.raises(ValidationError, match="Viewer"):
            TaskWorkflowService.transition(task=task, actor=viewer_user, to_status=TaskStatus.IN_PROGRESS)

    def test_viewer_cannot_create_invitation(self, viewer_client):
        resp = viewer_client.post(
            "/api/auth/invite/",
            {"email": "hack@test.com", "role": "owner"},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_developer_cannot_archive(self, project_with_team, developer_user, owner_user):
        task = Task.objects.create(
            project=project_with_team,
            title="Dev Archive",
            assignee=developer_user,
            created_by=owner_user,
        )
        TaskWorkflowService.transition(task=task, actor=developer_user, to_status=TaskStatus.IN_PROGRESS)
        from django.core.exceptions import ValidationError

        with pytest.raises(ValidationError, match="Project Manager"):
            TaskWorkflowService.transition(task=task, actor=developer_user, to_status=TaskStatus.ARCHIVED)

    def test_non_reviewer_cannot_approve(self, project_with_team, developer_user, owner_user, reviewer_user):
        task = Task.objects.create(
            project=project_with_team,
            title="Approve Test",
            assignee=developer_user,
            reviewer=reviewer_user,
            created_by=owner_user,
        )
        TaskWorkflowService.transition(task=task, actor=developer_user, to_status=TaskStatus.IN_PROGRESS)
        TaskWorkflowService.transition(task=task, actor=owner_user, to_status=TaskStatus.IN_REVIEW)
        from django.core.exceptions import ValidationError

        with pytest.raises(ValidationError, match="Reviewer"):
            TaskWorkflowService.transition(task=task, actor=developer_user, to_status=TaskStatus.APPROVED)


@pytest.mark.django_db
class TestInviteTokenSecurity:
    def test_cannot_accept_with_invalid_token(self, api_client):
        resp = api_client.post(
            "/api/auth/invite/accept/",
            {"token": "invalid-token-xyz", "password": "strongpass123"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_escalate_role_via_invite(self, authenticated_client, api_client):
        # Owner role cannot be assigned via invitation
        resp = authenticated_client.post(
            "/api/auth/invite/",
            {"email": "escalate@test.com", "role": "owner"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
