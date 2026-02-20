import pytest
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status

from apps.accounts.models import User
from apps.projects.models import Sprint
from apps.tasks.models import Task, TaskStatus
from apps.tasks.services import TaskWorkflowService
from apps.time_tracking.services import TimeEntryService


@pytest.mark.django_db
class TestFullTaskLifecycle:
    """Integration test: signup → create project → create sprint → create task →
    assign → transition through all states → complete."""

    def test_complete_lifecycle(self, authenticated_client, project_with_team, developer_user, reviewer_user, owner_user):
        # 1. Create task
        create_resp = authenticated_client.post(
            "/api/tasks/",
            {
                "project": project_with_team.id,
                "title": "Lifecycle Task",
                "description": "Full lifecycle test",
                "assignee": developer_user.id,
                "reviewer": reviewer_user.id,
                "priority": "critical",
                "deadline": (timezone.now() + timezone.timedelta(days=7)).isoformat(),
                "estimated_time_hours": "8.00",
            },
            format="json",
        )
        assert create_resp.status_code == status.HTTP_201_CREATED
        task_id = create_resp.data["id"]

        # 2. Developer moves to in_progress
        from rest_framework.test import APIClient

        dev_client = APIClient()
        dev_client.force_authenticate(user=developer_user)
        resp = dev_client.post(
            f"/api/tasks/{task_id}/transition/",
            {"to_status": "in_progress"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["status"] == "in_progress"

        # 3. Log time
        time_resp = dev_client.post(
            "/api/time-entries/",
            {"task": task_id, "hours": "4.00", "date": date.today().isoformat()},
            format="json",
        )
        assert time_resp.status_code == status.HTTP_201_CREATED

        # 4. Owner moves to review
        review_resp = authenticated_client.post(
            f"/api/tasks/{task_id}/transition/",
            {"to_status": "in_review"},
            format="json",
        )
        assert review_resp.status_code == status.HTTP_200_OK

        # 5. Reviewer approves
        rev_client = APIClient()
        rev_client.force_authenticate(user=reviewer_user)
        approve_resp = rev_client.post(
            f"/api/tasks/{task_id}/transition/",
            {"to_status": "approved"},
            format="json",
        )
        assert approve_resp.status_code == status.HTTP_200_OK

        # 6. Complete
        complete_resp = authenticated_client.post(
            f"/api/tasks/{task_id}/transition/",
            {"to_status": "completed"},
            format="json",
        )
        assert complete_resp.status_code == status.HTTP_200_OK
        assert complete_resp.data["status"] == "completed"

        # 7. Status changes recorded
        changes_resp = authenticated_client.get(f"/api/tasks/{task_id}/status-changes/")
        assert changes_resp.status_code == status.HTTP_200_OK
        assert len(changes_resp.data) == 4


@pytest.mark.django_db
class TestOrgSignupAndInviteFlow:
    """Integration test: signup → invite → accept → verify org membership."""

    def test_signup_creates_org_and_owner(self, api_client):
        resp = api_client.post(
            "/api/auth/register/",
            {
                "email": "founder@startup.com",
                "password": "strongpass123",
                "first_name": "Founder",
                "last_name": "CEO",
                "organization_name": "My Startup",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email="founder@startup.com")
        assert user.role == "owner"
        assert user.organization is not None
        assert user.organization.name == "My Startup"

    def test_invite_accept_flow(self, api_client):
        # Signup
        signup = api_client.post(
            "/api/auth/register/",
            {
                "email": "boss@company.com",
                "password": "strongpass123",
                "first_name": "Boss",
                "last_name": "Man",
                "organization_name": "Company Inc",
            },
            format="json",
        )
        assert signup.status_code == status.HTTP_201_CREATED

        # Login
        login = api_client.post(
            "/api/auth/login/",
            {"email": "boss@company.com", "password": "strongpass123"},
            format="json",
        )
        assert login.status_code == status.HTTP_200_OK
        token = login.data["access"]

        # Create invitation
        from rest_framework.test import APIClient

        auth_client = APIClient()
        auth_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        invite_resp = auth_client.post(
            "/api/auth/invite/",
            {"email": "dev@company.com", "role": "developer"},
            format="json",
        )
        assert invite_resp.status_code == status.HTTP_201_CREATED
        invite_token = invite_resp.data["token"]

        # Accept invitation
        accept = api_client.post(
            "/api/auth/invite/accept/",
            {
                "token": invite_token,
                "password": "devpass12345",
                "first_name": "Dev",
                "last_name": "Person",
            },
            format="json",
        )
        assert accept.status_code == status.HTTP_201_CREATED
        assert accept.data["role"] == "developer"

        # Verify both users in same org
        boss = User.objects.get(email="boss@company.com")
        dev = User.objects.get(email="dev@company.com")
        assert boss.organization_id == dev.organization_id


@pytest.mark.django_db
class TestMultiUserInteraction:
    def test_developer_and_reviewer_collaboration(self, project_with_team, developer_user, reviewer_user, owner_user):
        task = Task.objects.create(
            project=project_with_team,
            title="Collab Task",
            assignee=developer_user,
            reviewer=reviewer_user,
            created_by=owner_user,
        )

        # Developer starts
        TaskWorkflowService.transition(task=task, actor=developer_user, to_status=TaskStatus.IN_PROGRESS)

        # Log time
        TimeEntryService.create_time_entry(
            user=developer_user,
            task=task,
            hours=Decimal("2.5"),
            date=date.today(),
        )

        # Move to review
        TaskWorkflowService.transition(task=task, actor=owner_user, to_status=TaskStatus.IN_REVIEW)

        # Reviewer approves
        TaskWorkflowService.transition(task=task, actor=reviewer_user, to_status=TaskStatus.APPROVED)

        # Complete
        TaskWorkflowService.transition(task=task, actor=owner_user, to_status=TaskStatus.COMPLETED)

        task.refresh_from_db()
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
        assert task.review_approved_at is not None
        assert task.total_logged_time_hours == Decimal("2.5")

    def test_sprint_with_tasks_lifecycle(self, project_with_team, developer_user, reviewer_user, owner_user):
        sprint = Sprint.objects.create(
            project=project_with_team,
            name="Sprint Alpha",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=14),
        )
        task = Task.objects.create(
            project=project_with_team,
            title="Sprint Task",
            assignee=developer_user,
            reviewer=reviewer_user,
            sprint=sprint,
            created_by=owner_user,
        )

        # Full lifecycle within sprint
        TaskWorkflowService.transition(task=task, actor=developer_user, to_status=TaskStatus.IN_PROGRESS)
        TaskWorkflowService.transition(task=task, actor=owner_user, to_status=TaskStatus.IN_REVIEW)
        TaskWorkflowService.transition(task=task, actor=reviewer_user, to_status=TaskStatus.APPROVED)
        TaskWorkflowService.transition(task=task, actor=owner_user, to_status=TaskStatus.COMPLETED)

        task.refresh_from_db()
        assert task.status == TaskStatus.COMPLETED
        assert task.sprint_id == sprint.id
