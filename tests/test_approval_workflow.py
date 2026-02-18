import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import UserRole
from apps.feature_flags.services import FeatureFlagService
from apps.policies.models import ApprovalStatus
from apps.policies.services import ApprovalService

# ============================================================
# Integration Tests: Approval Workflow
# ============================================================

class TestApprovalWorkflow:
    @pytest.fixture
    def prod_flag_needing_approval(self, prod_environment, owner_user):
        return FeatureFlagService.create_flag(
            name="Prod Feature",
            key="prod-approval",
            environment=prod_environment,
            created_by=owner_user,
            risk_level="high",
        )

    def test_create_approval_request(
        self, prod_flag_needing_approval, developer_user
    ):
        approval = ApprovalService.create_approval_request(
            flag=prod_flag_needing_approval,
            requested_by=developer_user,
            change_description="Enable new checkout flow",
        )
        assert approval.status == ApprovalStatus.PENDING
        assert approval.requested_by == developer_user

    def test_cannot_create_duplicate_pending_request(
        self, prod_flag_needing_approval, developer_user
    ):
        ApprovalService.create_approval_request(
            flag=prod_flag_needing_approval,
            requested_by=developer_user,
            change_description="First request",
        )
        with pytest.raises(ValidationError, match="already a pending"):
            ApprovalService.create_approval_request(
                flag=prod_flag_needing_approval,
                requested_by=developer_user,
                change_description="Second request",
            )

    def test_cannot_request_approval_for_non_approval_flag(
        self, dev_environment, owner_user, developer_user
    ):
        flag = FeatureFlagService.create_flag(
            name="Dev Flag", key="no-approval",
            environment=dev_environment, created_by=owner_user,
        )
        with pytest.raises(ValidationError, match="does not require"):
            ApprovalService.create_approval_request(
                flag=flag,
                requested_by=developer_user,
                change_description="Not needed",
            )

    def test_approve_request(
        self, prod_flag_needing_approval, developer_user, admin_user
    ):
        approval = ApprovalService.create_approval_request(
            flag=prod_flag_needing_approval,
            requested_by=developer_user,
            change_description="Enable feature",
        )
        result = ApprovalService.approve_request(
            approval, reviewer=admin_user, comment="Looks good"
        )
        assert result.status == ApprovalStatus.APPROVED
        assert result.reviewed_by == admin_user
        assert result.reviewed_at is not None

        prod_flag_needing_approval.refresh_from_db()
        assert prod_flag_needing_approval.is_approved is True
        assert prod_flag_needing_approval.approved_by == admin_user

    def test_cannot_approve_own_request(
        self, prod_flag_needing_approval, owner_user
    ):
        approval = ApprovalService.create_approval_request(
            flag=prod_flag_needing_approval,
            requested_by=owner_user,
            change_description="Self approve attempt",
        )
        with pytest.raises(ValidationError, match="Cannot approve your own"):
            ApprovalService.approve_request(approval, reviewer=owner_user)

    def test_reject_request(
        self, prod_flag_needing_approval, developer_user, admin_user
    ):
        approval = ApprovalService.create_approval_request(
            flag=prod_flag_needing_approval,
            requested_by=developer_user,
            change_description="Risky change",
        )
        result = ApprovalService.reject_request(
            approval, reviewer=admin_user, comment="Too risky"
        )
        assert result.status == ApprovalStatus.REJECTED
        assert result.review_comment == "Too risky"

        prod_flag_needing_approval.refresh_from_db()
        assert prod_flag_needing_approval.is_approved is False

    def test_cannot_review_already_reviewed_request(
        self, prod_flag_needing_approval, developer_user, admin_user
    ):
        approval = ApprovalService.create_approval_request(
            flag=prod_flag_needing_approval,
            requested_by=developer_user,
            change_description="Change",
        )
        ApprovalService.approve_request(approval, reviewer=admin_user)
        with pytest.raises(ValidationError, match="already been reviewed"):
            ApprovalService.approve_request(approval, reviewer=admin_user)

    def test_developer_cannot_approve(
        self, prod_flag_needing_approval, developer_user
    ):
        from apps.accounts.models import User
        dev2 = User.objects.create_user(
            email="dev2@test.com",
            password="testpass123",
            role=UserRole.DEVELOPER,
            tenant=developer_user.tenant,
        )
        approval = ApprovalService.create_approval_request(
            flag=prod_flag_needing_approval,
            requested_by=developer_user,
            change_description="Change",
        )
        with pytest.raises(ValidationError, match="Only Admin or Owner"):
            ApprovalService.approve_request(approval, reviewer=dev2)

    def test_viewer_cannot_approve(
        self, prod_flag_needing_approval, developer_user, viewer_user
    ):
        approval = ApprovalService.create_approval_request(
            flag=prod_flag_needing_approval,
            requested_by=developer_user,
            change_description="Change",
        )
        with pytest.raises(ValidationError, match="Only Admin or Owner"):
            ApprovalService.approve_request(approval, reviewer=viewer_user)


# ============================================================
# Integration Tests: Full Approval Lifecycle via API
# ============================================================

class TestApprovalAPI:
    def test_full_approval_lifecycle(
        self, authenticated_client, developer_client, api_client,
        prod_environment, owner_user, admin_user, developer_user,
    ):
        # Step 1: Developer creates a high-risk production flag
        resp = developer_client.post(
            "/api/flags/create/",
            {
                "name": "New Checkout",
                "key": "new-checkout",
                "environment_id": prod_environment.id,
                "risk_level": "high",
            },
            format="json",
        )
        assert resp.status_code == 201
        flag_id = resp.data["id"]
        assert resp.data["requires_approval"] is True

        # Step 2: Developer cannot enable without approval
        resp = developer_client.post(
            f"/api/flags/{flag_id}/toggle/",
            {"is_enabled": True},
            format="json",
        )
        assert resp.status_code == 400
        assert "approval" in resp.data["error"].lower()

        # Step 3: Developer creates approval request
        resp = developer_client.post(
            "/api/policies/approvals/create/",
            {
                "flag_id": flag_id,
                "change_description": "Enable new checkout flow for 10% rollout",
            },
            format="json",
        )
        assert resp.status_code == 201
        approval_id = resp.data["id"]

        # Step 4: Admin approves
        admin_client = api_client.__class__()
        admin_client.force_authenticate(user=admin_user)
        resp = admin_client.post(
            f"/api/policies/approvals/{approval_id}/approve/",
            {"comment": "Approved after review"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["status"] == "approved"

        # Step 5: Developer can now enable the flag
        resp = developer_client.post(
            f"/api/flags/{flag_id}/toggle/",
            {"is_enabled": True},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["is_enabled"] is True

    def test_pending_approvals_visible_in_queue(
        self, authenticated_client, developer_client,
        prod_environment, owner_user, developer_user,
    ):
        flag = FeatureFlagService.create_flag(
            name="Queue Test", key="queue-test",
            environment=prod_environment, created_by=owner_user,
            risk_level="critical",
        )
        developer_client.post(
            "/api/policies/approvals/create/",
            {
                "flag_id": flag.id,
                "change_description": "Test queue visibility",
            },
            format="json",
        )
        resp = authenticated_client.get("/api/policies/approvals/")
        results = resp.data.get("results", resp.data)
        assert any(a["flag"] == flag.id for a in results)
