import pytest
from rest_framework import status

from apps.feature_flags.models import FlagType
from apps.feature_flags.services import FeatureFlagService, FlagVariantService
from apps.targeting.models import Operator, RuleType, TargetingRule


# ============================================================
# Integration Tests: Evaluation Endpoint
# ============================================================

class TestEvaluationEndpoint:
    @pytest.fixture
    def enabled_boolean_flag(self, dev_environment, owner_user, tenant):
        flag = FeatureFlagService.create_flag(
            name="Eval Bool", key="eval-bool",
            environment=dev_environment, created_by=owner_user,
        )
        FeatureFlagService.toggle_flag(flag, True, owner_user)
        return flag

    @pytest.fixture
    def enabled_mv_flag(self, dev_environment, owner_user, tenant):
        flag = FeatureFlagService.create_flag(
            name="Eval MV", key="eval-mv-api",
            environment=dev_environment, created_by=owner_user,
            flag_type=FlagType.MULTIVARIATE,
        )
        FlagVariantService.set_variants(flag, [
            {"name": "control", "value": "old_ui", "rollout_percentage": 50, "is_control": True},
            {"name": "treatment", "value": "new_ui", "rollout_percentage": 50},
        ])
        FeatureFlagService.toggle_flag(flag, True, owner_user)
        return flag

    def test_evaluate_boolean_flag(self, api_client, enabled_boolean_flag, tenant):
        resp = api_client.post(
            "/api/evaluate/",
            {
                "flag_key": "eval-bool",
                "user_identifier": "user123",
                "environment": "development",
            },
            format="json",
            HTTP_X_TENANT_SLUG=tenant.slug,
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["variant"] is True
        assert resp.data["reason"] == "flag_enabled"

    def test_evaluate_multivariate_flag(self, api_client, enabled_mv_flag, tenant):
        resp = api_client.post(
            "/api/evaluate/",
            {
                "flag_key": "eval-mv-api",
                "user_identifier": "user456",
                "environment": "development",
            },
            format="json",
            HTTP_X_TENANT_SLUG=tenant.slug,
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["variant"] in ["old_ui", "new_ui"]
        assert resp.data["reason"] == "percentage_rollout"

    def test_evaluate_deterministic(self, api_client, enabled_mv_flag, tenant):
        """Same user always gets same variant."""
        results = set()
        for _ in range(5):
            resp = api_client.post(
                "/api/evaluate/",
                {
                    "flag_key": "eval-mv-api",
                    "user_identifier": "deterministic-user",
                    "environment": "development",
                },
                format="json",
                HTTP_X_TENANT_SLUG=tenant.slug,
            )
            results.add(resp.data["variant"])
        assert len(results) == 1

    def test_evaluate_disabled_flag(self, api_client, dev_environment, owner_user, tenant):
        FeatureFlagService.create_flag(
            name="Disabled", key="eval-disabled",
            environment=dev_environment, created_by=owner_user,
        )
        resp = api_client.post(
            "/api/evaluate/",
            {
                "flag_key": "eval-disabled",
                "user_identifier": "user1",
                "environment": "development",
            },
            format="json",
            HTTP_X_TENANT_SLUG=tenant.slug,
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["variant"] is None
        assert resp.data["reason"] == "flag_disabled"

    def test_evaluate_nonexistent_flag(self, api_client, tenant):
        resp = api_client.post(
            "/api/evaluate/",
            {
                "flag_key": "nonexistent",
                "user_identifier": "user1",
                "environment": "development",
            },
            format="json",
            HTTP_X_TENANT_SLUG=tenant.slug,
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_evaluate_missing_tenant_slug(self, api_client, enabled_boolean_flag):
        resp = api_client.post(
            "/api/evaluate/",
            {
                "flag_key": "eval-bool",
                "user_identifier": "user1",
                "environment": "development",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "X-Tenant-Slug" in resp.data["error"]

    def test_evaluate_wrong_tenant_slug(self, api_client, enabled_boolean_flag):
        resp = api_client.post(
            "/api/evaluate/",
            {
                "flag_key": "eval-bool",
                "user_identifier": "user1",
                "environment": "development",
            },
            format="json",
            HTTP_X_TENANT_SLUG="nonexistent-tenant",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_evaluate_deactivated_tenant(self, api_client, enabled_boolean_flag, tenant):
        tenant.is_active = False
        tenant.save()
        resp = api_client.post(
            "/api/evaluate/",
            {
                "flag_key": "eval-bool",
                "user_identifier": "user1",
                "environment": "development",
            },
            format="json",
            HTTP_X_TENANT_SLUG=tenant.slug,
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_evaluate_does_not_expose_rule_id(
        self, api_client, dev_environment, owner_user, tenant
    ):
        """Security: rule_matched must always be None in SDK response."""
        flag = FeatureFlagService.create_flag(
            name="Targeted", key="eval-targeted",
            environment=dev_environment, created_by=owner_user,
        )
        TargetingRule.objects.create(
            flag=flag,
            rule_type=RuleType.USER_ID,
            operator=Operator.EQUALS,
            value="special-user",
            variant_value=True,
            priority=1,
        )
        FeatureFlagService.toggle_flag(flag, True, owner_user)

        resp = api_client.post(
            "/api/evaluate/",
            {
                "flag_key": "eval-targeted",
                "user_identifier": "special-user",
                "environment": "development",
            },
            format="json",
            HTTP_X_TENANT_SLUG=tenant.slug,
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["rule_matched"] is None  # Never expose internal IDs

    def test_evaluate_with_targeting_rules(
        self, api_client, dev_environment, owner_user, tenant
    ):
        flag = FeatureFlagService.create_flag(
            name="Country", key="eval-country",
            environment=dev_environment, created_by=owner_user,
        )
        TargetingRule.objects.create(
            flag=flag,
            rule_type=RuleType.COUNTRY,
            operator=Operator.EQUALS,
            value="US",
            variant_value={"us_feature": True},
            priority=1,
        )
        FeatureFlagService.toggle_flag(flag, True, owner_user)

        resp = api_client.post(
            "/api/evaluate/",
            {
                "flag_key": "eval-country",
                "user_identifier": "user1",
                "environment": "development",
                "attributes": {"country": "US"},
            },
            format="json",
            HTTP_X_TENANT_SLUG=tenant.slug,
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["variant"] == {"us_feature": True}

    def test_evaluate_invalid_input(self, api_client, tenant):
        resp = api_client.post(
            "/api/evaluate/",
            {},
            format="json",
            HTTP_X_TENANT_SLUG=tenant.slug,
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================
# Integration Tests: Flag Lifecycle via API
# ============================================================

class TestFlagLifecycleAPI:
    def test_create_toggle_archive_lifecycle(
        self, authenticated_client, dev_environment
    ):
        # Create
        resp = authenticated_client.post(
            "/api/flags/create/",
            {
                "name": "Lifecycle Flag",
                "key": "lifecycle-flag",
                "environment_id": dev_environment.id,
            },
            format="json",
        )
        assert resp.status_code == 201
        flag_id = resp.data["id"]
        assert resp.data["status"] == "active"
        assert resp.data["is_enabled"] is False

        # Toggle on
        resp = authenticated_client.post(
            f"/api/flags/{flag_id}/toggle/",
            {"is_enabled": True},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["is_enabled"] is True

        # Toggle off
        resp = authenticated_client.post(
            f"/api/flags/{flag_id}/toggle/",
            {"is_enabled": False},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["is_enabled"] is False

        # Archive
        resp = authenticated_client.post(f"/api/flags/{flag_id}/archive/")
        assert resp.status_code == 200
        assert resp.data["status"] == "archived"

        # Cannot toggle archived
        resp = authenticated_client.post(
            f"/api/flags/{flag_id}/toggle/",
            {"is_enabled": True},
            format="json",
        )
        assert resp.status_code == 400

    def test_create_flag_with_variants(
        self, authenticated_client, dev_environment
    ):
        resp = authenticated_client.post(
            "/api/flags/create/",
            {
                "name": "MV Flag",
                "key": "mv-lifecycle",
                "environment_id": dev_environment.id,
                "flag_type": "multivariate",
            },
            format="json",
        )
        assert resp.status_code == 201
        flag_id = resp.data["id"]

        resp = authenticated_client.post(
            f"/api/flags/{flag_id}/variants/",
            {
                "variants": [
                    {"name": "A", "value": "a", "rollout_percentage": 50},
                    {"name": "B", "value": "b", "rollout_percentage": 50},
                ]
            },
            format="json",
        )
        assert resp.status_code == 200
        assert len(resp.data) == 2
