from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.feature_flags.models import FlagStatus, RiskLevel
from apps.policies.models import ApprovalRequest, ApprovalStatus, Policy


class PolicyEngine:
    """Centralized policy enforcement engine."""

    @staticmethod
    def check_can_modify_flag(flag, user):
        tenant = flag.environment.tenant
        policies = {
            p.policy_type: p.is_enabled
            for p in Policy.objects.filter(tenant=tenant)
        }

        if flag.status == FlagStatus.ARCHIVED:
            if policies.get(Policy.PolicyType.ARCHIVED_IMMUTABLE, True):
                raise ValidationError("Policy violation: Archived flags cannot be edited.")

        if flag.environment.is_production:
            if policies.get(Policy.PolicyType.PRODUCTION_OWNER_ONLY, False):
                if user.role != UserRole.OWNER:
                    raise ValidationError(
                        "Policy violation: Only Owner can modify production flags."
                    )

            if policies.get(Policy.PolicyType.PRODUCTION_APPROVAL, True):
                if flag.requires_approval and not flag.is_approved:
                    pending = ApprovalRequest.objects.filter(
                        flag=flag, status=ApprovalStatus.PENDING
                    ).exists()
                    if not pending:
                        raise ValidationError(
                            "Policy violation: Production flag requires an approval request."
                        )

        if flag.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            if flag.environment.is_production:
                if policies.get(Policy.PolicyType.HIGH_RISK_DUAL_APPROVAL, True):
                    if not flag.is_approved:
                        raise ValidationError(
                            "Policy violation: High/critical risk production flags require approval."
                        )

    @staticmethod
    def check_key_immutability(flag, new_key):
        if new_key != flag.key:
            tenant = flag.environment.tenant
            policy_enabled = Policy.objects.filter(
                tenant=tenant,
                policy_type=Policy.PolicyType.KEY_IMMUTABLE,
                is_enabled=True,
            ).exists()
            if policy_enabled:
                raise ValidationError(
                    "Policy violation: Flag key cannot be changed after creation."
                )


class ApprovalService:
    @staticmethod
    @transaction.atomic
    def create_approval_request(flag, requested_by, change_description, change_payload=None):
        if not flag.requires_approval:
            raise ValidationError("This flag does not require approval.")

        existing_pending = ApprovalRequest.objects.filter(
            flag=flag, status=ApprovalStatus.PENDING
        ).exists()
        if existing_pending:
            raise ValidationError("There is already a pending approval request for this flag.")

        return ApprovalRequest.objects.create(
            flag=flag,
            requested_by=requested_by,
            change_description=change_description,
            change_payload=change_payload or {},
        )

    @staticmethod
    @transaction.atomic
    def approve_request(approval_request, reviewer, comment=""):
        if approval_request.status != ApprovalStatus.PENDING:
            raise ValidationError("This request has already been reviewed.")

        if approval_request.requested_by == reviewer:
            raise ValidationError("Cannot approve your own request.")

        if not reviewer.has_role_level(UserRole.ADMIN):
            raise ValidationError("Only Admin or Owner can approve requests.")

        approval_request.status = ApprovalStatus.APPROVED
        approval_request.reviewed_by = reviewer
        approval_request.review_comment = comment
        approval_request.reviewed_at = timezone.now()
        approval_request.save()

        flag = approval_request.flag
        flag.is_approved = True
        flag.approved_by = reviewer
        flag.approved_at = timezone.now()
        flag.save(update_fields=["is_approved", "approved_by", "approved_at", "updated_at"])

        return approval_request

    @staticmethod
    @transaction.atomic
    def reject_request(approval_request, reviewer, comment=""):
        if approval_request.status != ApprovalStatus.PENDING:
            raise ValidationError("This request has already been reviewed.")

        if not reviewer.has_role_level(UserRole.ADMIN):
            raise ValidationError("Only Admin or Owner can reject requests.")

        approval_request.status = ApprovalStatus.REJECTED
        approval_request.reviewed_by = reviewer
        approval_request.review_comment = comment
        approval_request.reviewed_at = timezone.now()
        approval_request.save()

        return approval_request

    @staticmethod
    def get_pending_approvals(tenant):
        return ApprovalRequest.objects.filter(
            flag__environment__tenant=tenant,
            status=ApprovalStatus.PENDING,
        ).select_related("flag", "requested_by")
