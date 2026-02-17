import os

os.environ.setdefault("DJANGO_ENV", "test")

import pytest

from apps.accounts.models import User, UserRole
from apps.tenants.models import Environment, Tenant
from apps.tenants.services import TenantService


@pytest.fixture
def tenant(db):
    return TenantService.create_tenant("Test Corp", "professional")


@pytest.fixture
def tenant_b(db):
    return TenantService.create_tenant("Other Corp", "free")


@pytest.fixture
def dev_environment(tenant):
    return Environment.objects.get(tenant=tenant, name="development")


@pytest.fixture
def staging_environment(tenant):
    return Environment.objects.get(tenant=tenant, name="staging")


@pytest.fixture
def prod_environment(tenant):
    return Environment.objects.get(tenant=tenant, name="production")


@pytest.fixture
def owner_user(tenant):
    return User.objects.create_user(
        email="owner@test.com",
        password="testpass123",
        role=UserRole.OWNER,
        tenant=tenant,
    )


@pytest.fixture
def admin_user(tenant):
    return User.objects.create_user(
        email="admin@test.com",
        password="testpass123",
        role=UserRole.ADMIN,
        tenant=tenant,
    )


@pytest.fixture
def developer_user(tenant):
    return User.objects.create_user(
        email="dev@test.com",
        password="testpass123",
        role=UserRole.DEVELOPER,
        tenant=tenant,
    )


@pytest.fixture
def viewer_user(tenant):
    return User.objects.create_user(
        email="viewer@test.com",
        password="testpass123",
        role=UserRole.VIEWER,
        tenant=tenant,
    )


@pytest.fixture
def other_tenant_user(tenant_b):
    return User.objects.create_user(
        email="other@test.com",
        password="testpass123",
        role=UserRole.OWNER,
        tenant=tenant_b,
    )


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, owner_user):
    api_client.force_authenticate(user=owner_user)
    return api_client


@pytest.fixture
def developer_client(api_client, developer_user):
    api_client.force_authenticate(user=developer_user)
    return api_client


@pytest.fixture
def viewer_client(api_client, viewer_user):
    api_client.force_authenticate(user=viewer_user)
    return api_client


@pytest.fixture
def other_tenant_client(api_client, other_tenant_user):
    api_client.force_authenticate(user=other_tenant_user)
    return api_client
