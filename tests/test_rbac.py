from rest_framework import status

from apps.feature_flags.services import FeatureFlagService


# ============================================================
# Security Tests: Role-Based Access Control
# ============================================================

class TestViewerRestrictions:
    """Viewers should only be able to read, never mutate."""

    def test_viewer_can_list_flags(self, viewer_client, dev_environment, owner_user):
        FeatureFlagService.create_flag(
            name="Flag", key="viewer-list",
            environment=dev_environment, created_by=owner_user,
        )
        resp = viewer_client.get("/api/flags/")
        assert resp.status_code == status.HTTP_200_OK

    def test_viewer_cannot_create_flag(self, viewer_client, dev_environment):
        resp = viewer_client.post(
            "/api/flags/create/",
            {
                "name": "Hack",
                "key": "viewer-create",
                "environment_id": dev_environment.id,
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_cannot_toggle_flag(
        self, viewer_client, dev_environment, owner_user
    ):
        flag = FeatureFlagService.create_flag(
            name="Flag", key="viewer-toggle",
            environment=dev_environment, created_by=owner_user,
        )
        resp = viewer_client.post(
            f"/api/flags/{flag.id}/toggle/",
            {"is_enabled": True},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_cannot_archive_flag(
        self, viewer_client, dev_environment, owner_user
    ):
        flag = FeatureFlagService.create_flag(
            name="Flag", key="viewer-archive",
            environment=dev_environment, created_by=owner_user,
        )
        resp = viewer_client.post(f"/api/flags/{flag.id}/archive/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_cannot_create_targeting_rule(
        self, viewer_client, dev_environment, owner_user
    ):
        flag = FeatureFlagService.create_flag(
            name="Flag", key="viewer-rule",
            environment=dev_environment, created_by=owner_user,
        )
        resp = viewer_client.post(
            "/api/targeting/rules/",
            {
                "flag_id": flag.id,
                "rule_type": "user_id",
                "operator": "equals",
                "value": "user1",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_cannot_access_audit_logs(self, viewer_client):
        resp = viewer_client.get("/api/audit/logs/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_cannot_see_approval_queue(self, viewer_client):
        resp = viewer_client.get("/api/policies/approvals/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestDeveloperRestrictions:
    """Developers can create/modify but cannot archive or manage policies."""

    def test_developer_can_create_flag(self, developer_client, dev_environment):
        resp = developer_client.post(
            "/api/flags/create/",
            {
                "name": "Dev Flag",
                "key": "dev-create",
                "environment_id": dev_environment.id,
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_developer_can_toggle_flag(
        self, developer_client, dev_environment, developer_user
    ):
        flag = FeatureFlagService.create_flag(
            name="Flag", key="dev-toggle",
            environment=dev_environment, created_by=developer_user,
        )
        resp = developer_client.post(
            f"/api/flags/{flag.id}/toggle/",
            {"is_enabled": True},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_developer_cannot_archive_flag(
        self, developer_client, dev_environment, developer_user
    ):
        flag = FeatureFlagService.create_flag(
            name="Flag", key="dev-archive",
            environment=dev_environment, created_by=developer_user,
        )
        resp = developer_client.post(f"/api/flags/{flag.id}/archive/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_developer_cannot_kill_switch(
        self, developer_client, dev_environment, developer_user
    ):
        flag = FeatureFlagService.create_flag(
            name="Flag", key="dev-kill",
            environment=dev_environment, created_by=developer_user,
        )
        resp = developer_client.post(
            f"/api/flags/{flag.id}/kill-switch/",
            {"action": "activate"},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestPrivilegeEscalation:
    """Verify users cannot escalate their own privileges."""

    def test_cannot_set_role_via_registration(self, api_client, db):
        resp = api_client.post(
            "/api/auth/register/",
            {
                "email": "attacker@evil.com",
                "password": "attackpass123",
                "role": "owner",
                "first_name": "Evil",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        # Role should be forced to viewer regardless of what was sent
        from apps.accounts.models import User
        user = User.objects.get(email="attacker@evil.com")
        assert user.role == "viewer"

    def test_cannot_set_tenant_via_registration(self, api_client, tenant):
        resp = api_client.post(
            "/api/auth/register/",
            {
                "email": "attacker2@evil.com",
                "password": "attackpass123",
                "tenant": tenant.id,
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        from apps.accounts.models import User
        user = User.objects.get(email="attacker2@evil.com")
        assert user.tenant is None

    def test_cannot_change_own_role_via_profile(self, developer_client, developer_user):
        developer_client.patch(
            "/api/auth/profile/",
            {"role": "owner"},
            format="json",
        )
        developer_user.refresh_from_db()
        assert developer_user.role == "developer"

    def test_cannot_change_own_tenant_via_profile(self, developer_client, developer_user, tenant_b):
        developer_client.patch(
            "/api/auth/profile/",
            {"tenant": tenant_b.id},
            format="json",
        )
        developer_user.refresh_from_db()
        assert developer_user.tenant_id != tenant_b.id

    def test_viewer_cannot_list_users(self, viewer_client):
        resp = viewer_client.get("/api/auth/users/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
