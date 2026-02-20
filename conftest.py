import os

os.environ.setdefault("DJANGO_ENV", "test")

import pytest

from apps.accounts.models import User, UserRole
from apps.organizations.models import Organization
from apps.projects.models import Project, ProjectMember


@pytest.fixture
def organization(db):
    return Organization.objects.create(name="Test Org", slug="test-org")


@pytest.fixture
def organization_b(db):
    return Organization.objects.create(name="Other Org", slug="other-org")


@pytest.fixture
def owner_user(organization):
    return User.objects.create_user(
        email="owner@test.com",
        password="testpass123",
        role=UserRole.OWNER,
        organization=organization,
    )


@pytest.fixture
def project_manager_user(organization):
    return User.objects.create_user(
        email="pm@test.com",
        password="testpass123",
        role=UserRole.PROJECT_MANAGER,
        organization=organization,
    )


@pytest.fixture
def developer_user(organization):
    return User.objects.create_user(
        email="dev@test.com",
        password="testpass123",
        role=UserRole.DEVELOPER,
        organization=organization,
    )


@pytest.fixture
def reviewer_user(organization):
    return User.objects.create_user(
        email="reviewer@test.com",
        password="testpass123",
        role=UserRole.REVIEWER,
        organization=organization,
    )


@pytest.fixture
def viewer_user(organization):
    return User.objects.create_user(
        email="viewer@test.com",
        password="testpass123",
        role=UserRole.VIEWER,
        organization=organization,
    )


@pytest.fixture
def other_org_owner_user(organization_b):
    return User.objects.create_user(
        email="other@test.com",
        password="testpass123",
        role=UserRole.OWNER,
        organization=organization_b,
    )


@pytest.fixture
def project(organization, owner_user):
    project = Project.objects.create(
        organization=organization,
        name="Project Alpha",
        description="",
        created_by=owner_user,
    )
    ProjectMember.objects.create(project=project, user=owner_user)
    return project


@pytest.fixture
def project_with_team(project, developer_user, reviewer_user, viewer_user):
    ProjectMember.objects.get_or_create(project=project, user=developer_user)
    ProjectMember.objects.get_or_create(project=project, user=reviewer_user)
    ProjectMember.objects.get_or_create(project=project, user=viewer_user)
    return project


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def authenticated_client(owner_user):
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user=owner_user)
    return client


@pytest.fixture
def developer_client(developer_user):
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user=developer_user)
    return client


@pytest.fixture
def viewer_client(viewer_user):
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user=viewer_user)
    return client


@pytest.fixture
def other_org_client(other_org_owner_user):
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user=other_org_owner_user)
    return client
