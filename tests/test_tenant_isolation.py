import pytest
from rest_framework import status

from apps.feature_flags.services import FeatureFlagService
from apps.tenants.services import TenantService

# ============================================================
# Security Tests: Cross-Tenant Access Denial
# ============================================================

class TestCrossTenantFlagAccess:
    """Verify that no endpoint allows cross-tenant data access."""

    @pytest.fixture
    def tenant_a_flag(self, dev_environment, owner_user):
        return FeatureFlagService.create_flag(
            name="Tenant A Flag",
            key="tenant-a-flag",
            environment=dev_environment,
            created_by=owner_user,
        )

    def test_other_tenant_cannot_list_flags(
        self, other_tenant_client, tenant_a_flag
    ):
        resp = other_tenant_client.get("/api/flags/")
        assert resp.status_code == status.HTTP_200_OK
        flag_ids = [f["id"] for f in resp.data.get("results", resp.data)]
        assert tenant_a_flag.id not in flag_ids

    def test_other_tenant_cannot_get_flag_detail(
        self, other_tenant_client, tenant_a_flag
    ):
        resp = other_tenant_client.get(f"/api/flags/{tenant_a_flag.id}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_other_tenant_cannot_toggle_flag(
        self, other_tenant_client, tenant_a_flag
    ):
        resp = other_tenant_client.post(
            f"/api/flags/{tenant_a_flag.id}/toggle/",
            {"is_enabled": True},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_other_tenant_cannot_archive_flag(
        self, other_tenant_client, tenant_a_flag
    ):
        resp = other_tenant_client.post(
            f"/api/flags/{tenant_a_flag.id}/archive/"
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_other_tenant_cannot_delete_flag(
        self, other_tenant_client, tenant_a_flag
    ):
        resp = other_tenant_client.delete(
            f"/api/flags/{tenant_a_flag.id}/"
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_other_tenant_cannot_set_variants(
        self, other_tenant_client, tenant_a_flag
    ):
        resp = other_tenant_client.post(
            f"/api/flags/{tenant_a_flag.id}/variants/",
            {"variants": [{"name": "hack", "value": "x", "rollout_percentage": 100}]},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_other_tenant_cannot_kill_switch_flag(
        self, other_tenant_client, tenant_a_flag
    ):
        resp = other_tenant_client.post(
            f"/api/flags/{tenant_a_flag.id}/kill-switch/",
            {"action": "activate"},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestCrossTenantTargetingRuleAccess:
    """Verify targeting rules are tenant-isolated."""

    @pytest.fixture
    def tenant_a_flag_with_rule(self, dev_environment, owner_user, authenticated_client):
        flag = FeatureFlagService.create_flag(
            name="Rule Flag", key="rule-flag",
            environment=dev_environment, created_by=owner_user,
        )
        resp = authenticated_client.post(
            "/api/targeting/rules/",
            {
                "flag_id": flag.id,
                "rule_type": "user_id",
                "operator": "equals",
                "value": "user1",
            },
            format="json",
        )
        return flag, resp.data["id"]

    def test_other_tenant_cannot_list_rules(
        self, other_tenant_client, tenant_a_flag_with_rule
    ):
        flag, rule_id = tenant_a_flag_with_rule
        resp = other_tenant_client.get(f"/api/targeting/flags/{flag.id}/rules/")
        assert resp.status_code == status.HTTP_200_OK
        rule_ids = [r["id"] for r in resp.data.get("results", resp.data)]
        assert rule_id not in rule_ids

    def test_other_tenant_cannot_modify_rule(
        self, other_tenant_client, tenant_a_flag_with_rule
    ):
        _, rule_id = tenant_a_flag_with_rule
        resp = other_tenant_client.patch(
            f"/api/targeting/rules/{rule_id}/",
            {"value": "hacked"},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_other_tenant_cannot_delete_rule(
        self, other_tenant_client, tenant_a_flag_with_rule
    ):
        _, rule_id = tenant_a_flag_with_rule
        resp = other_tenant_client.delete(f"/api/targeting/rules/{rule_id}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestCrossTenantApprovalAccess:
    """Verify approval requests are tenant-isolated."""

    def test_other_tenant_cannot_see_approval_queue(
        self, other_tenant_client, authenticated_client,
        prod_environment, owner_user
    ):
        flag = FeatureFlagService.create_flag(
            name="Prod Flag", key="approval-iso",
            environment=prod_environment, created_by=owner_user,
            risk_level="high",
        )
        authenticated_client.post(
            "/api/policies/approvals/create/",
            {
                "flag_id": flag.id,
                "change_description": "Enable feature",
            },
            format="json",
        )
        resp = other_tenant_client.get("/api/policies/approvals/")
        results = resp.data.get("results", resp.data)
        assert len(results) == 0


class TestCrossTenantAuditAccess:
    """Verify audit logs are tenant-isolated."""

    def test_other_tenant_cannot_see_audit_logs(
        self, other_tenant_client, authenticated_client, dev_environment, owner_user
    ):
        # Create a flag to generate audit log
        authenticated_client.post(
            "/api/flags/create/",
            {
                "name": "Audit Flag",
                "key": "audit-iso",
                "environment_id": dev_environment.id,
            },
            format="json",
        )
        resp = other_tenant_client.get("/api/audit/logs/")
        results = resp.data.get("results", resp.data)
        # Other tenant should see zero logs from tenant A
        assert len(results) == 0


# ============================================================
# Security Tests: Tenant Middleware Enforcement
# ============================================================

class TestTenantMiddleware:
    def test_unauthenticated_request_rejected(self, api_client):
        resp = api_client.get("/api/flags/")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_without_tenant_rejected_on_tenant_paths(self, api_client, db):
        from apps.accounts.models import User, UserRole
        orphan = User.objects.create_user(
            email="orphan@test.com",
            password="testpass123",
            role=UserRole.DEVELOPER,
            tenant=None,
        )
        api_client.force_authenticate(user=orphan)
        resp = api_client.get("/api/flags/")
        assert resp.status_code == 403
        assert "not associated" in resp.json()["error"]

    def test_deactivated_tenant_rejected(self, api_client, tenant, owner_user):
        tenant.is_active = False
        tenant.save()
        api_client.force_authenticate(user=owner_user)
        resp = api_client.get("/api/flags/")
        assert resp.status_code == 403
        assert "deactivated" in resp.json()["error"]


# ============================================================
# Security Tests: ID Enumeration Prevention
# ============================================================

class TestIDEnumeration:
    """Verify that accessing objects by ID from another tenant returns 404, not 403.
    Returning 403 would confirm the object exists (information leak)."""

    def test_flag_id_enumeration_returns_404(
        self, other_tenant_client, dev_environment, owner_user
    ):
        flag = FeatureFlagService.create_flag(
            name="Secret", key="secret-flag",
            environment=dev_environment, created_by=owner_user,
        )
        resp = other_tenant_client.get(f"/api/flags/{flag.id}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_sequential_id_scan_returns_404(self, other_tenant_client):
        for fake_id in range(1, 10):
            resp = other_tenant_client.get(f"/api/flags/{fake_id}/")
            assert resp.status_code == status.HTTP_404_NOT_FOUND


# ============================================================
# Tests: Tenant Service
# ============================================================

class TestTenantService:
    def test_create_tenant_creates_all_environments(self, db):
        tenant = TenantService.create_tenant("New Corp")
        envs = list(tenant.environments.values_list("name", flat=True))
        assert sorted(envs) == ["development", "production", "staging"]

    def test_deactivate_tenant(self, tenant):
        TenantService.deactivate_tenant(tenant)
        tenant.refresh_from_db()
        assert tenant.is_active is False
