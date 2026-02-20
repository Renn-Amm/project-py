import pytest
from django.utils import timezone
from rest_framework import status

from apps.projects.models import ProjectMember
from apps.tasks.models import Task, TaskStatus


@pytest.mark.django_db
class TestTaskSystemAPI:
    def test_register_rejects_invalid_email(self, api_client):
        resp = api_client.post(
            "/api/auth/register/",
            {
                "email": "not-an-email",
                "password": "verystrongpass",
                "first_name": "X",
                "last_name": "Y",
                "organization_name": "Org",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_login_and_profile(self, api_client):
        resp = api_client.post(
            "/api/auth/register/",
            {
                "email": "new@test.com",
                "password": "verystrongpass",
                "first_name": "New",
                "last_name": "User",
                "organization_name": "New Org",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED

        login = api_client.post(
            "/api/auth/login/",
            {"email": "new@test.com", "password": "verystrongpass"},
            format="json",
        )
        assert login.status_code == status.HTTP_200_OK
        assert "access" in login.data
        assert "refresh" in login.data

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        profile = api_client.get("/api/auth/profile/")
        assert profile.status_code == status.HTTP_200_OK
        assert profile.data["email"] == "new@test.com"

    def test_project_crud_and_membership_enforced(self, authenticated_client, other_org_client, developer_user):
        resp = authenticated_client.post(
            "/api/projects/",
            {"name": "API Project", "description": ""},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        project_id = resp.data["id"]

        # owner is automatically a member
        assert ProjectMember.objects.filter(project_id=project_id).count() == 1

        # owner can add member
        add = authenticated_client.post(
            f"/api/projects/{project_id}/members/",
            {"user": developer_user.id},
            format="json",
        )
        assert add.status_code == status.HTTP_201_CREATED

        # cross-organization user cannot see project
        other_list = other_org_client.get("/api/projects/")
        assert other_list.status_code == status.HTTP_200_OK
        ids = [p["id"] for p in other_list.data.get("results", other_list.data)]
        assert project_id not in ids

        other_detail = other_org_client.get(f"/api/projects/{project_id}/")
        assert other_detail.status_code == status.HTTP_404_NOT_FOUND

    def test_task_transition_rules_and_time_entries(self, authenticated_client, project_with_team, developer_user, reviewer_user):
        # create task
        create = authenticated_client.post(
            "/api/tasks/",
            {
                "project": project_with_team.id,
                "title": "T1",
                "description": "",
                "assignee": developer_user.id,
                "reviewer": reviewer_user.id,
                "deadline": (timezone.now() + timezone.timedelta(days=1)).isoformat(),
            },
            format="json",
        )
        assert create.status_code == status.HTTP_201_CREATED
        task_id = create.data["id"]

        # viewer cannot transition
        # (use force_authenticate by swapping credentials)

        # developer (assignee) can move to in_progress
        from rest_framework.test import APIClient

        dev_client = APIClient()
        dev_client.force_authenticate(user=developer_user)
        to_in_progress = dev_client.post(
            f"/api/tasks/{task_id}/transition/",
            {"to_status": TaskStatus.IN_PROGRESS},
            format="json",
        )
        assert to_in_progress.status_code == status.HTTP_200_OK
        assert to_in_progress.data["status"] == TaskStatus.IN_PROGRESS

        # owner can move to in_review
        to_in_review = authenticated_client.post(
            f"/api/tasks/{task_id}/transition/",
            {"to_status": TaskStatus.IN_REVIEW},
            format="json",
        )
        assert to_in_review.status_code == status.HTTP_200_OK

        # reviewer can approve
        reviewer_client = APIClient()
        reviewer_client.force_authenticate(user=reviewer_user)
        approved = reviewer_client.post(
            f"/api/tasks/{task_id}/transition/",
            {"to_status": TaskStatus.APPROVED},
            format="json",
        )
        assert approved.status_code == status.HTTP_200_OK

        # complete (owner override) clears overdue
        completed = authenticated_client.post(
            f"/api/tasks/{task_id}/transition/",
            {"to_status": TaskStatus.COMPLETED},
            format="json",
        )
        assert completed.status_code == status.HTTP_200_OK

        task = Task.objects.get(pk=task_id)
        assert task.status == TaskStatus.COMPLETED

        # log time
        time_resp = authenticated_client.post(
            "/api/time-entries/",
            {"task": task_id, "hours": "1.25", "date": timezone.now().date().isoformat()},
            format="json",
        )
        assert time_resp.status_code == status.HTTP_201_CREATED
