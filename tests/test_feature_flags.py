from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.feature_flags.models import (
    FeatureFlag,
    FlagStatus,
    FlagType,
    RiskLevel,
)
from apps.feature_flags.services import (
    EvaluationEngine,
    FeatureFlagService,
    FlagVariantService,
)


# ============================================================
# Unit Tests: Flag Creation
# ============================================================

class TestFlagCreation:
    def test_create_boolean_flag(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Test Flag",
            key="test-flag",
            environment=dev_environment,
            created_by=owner_user,
        )
        assert flag.key == "test-flag"
        assert flag.flag_type == FlagType.BOOLEAN
        assert flag.status == FlagStatus.ACTIVE
        assert flag.version == 1
        assert flag.variants.count() == 1
        assert flag.variants.first().rollout_percentage == Decimal("100")

    def test_create_multivariate_flag(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="MV Flag",
            key="mv-flag",
            environment=dev_environment,
            created_by=owner_user,
            flag_type=FlagType.MULTIVARIATE,
        )
        assert flag.flag_type == FlagType.MULTIVARIATE
        assert flag.variants.count() == 0

    def test_duplicate_key_same_environment_rejected(self, dev_environment, owner_user):
        FeatureFlagService.create_flag(
            name="Flag A",
            key="dup-key",
            environment=dev_environment,
            created_by=owner_user,
        )
        with pytest.raises(ValidationError, match="already exists"):
            FeatureFlagService.create_flag(
                name="Flag B",
                key="dup-key",
                environment=dev_environment,
                created_by=owner_user,
            )

    def test_same_key_different_environment_allowed(
        self, dev_environment, staging_environment, owner_user
    ):
        FeatureFlagService.create_flag(
            name="Flag A",
            key="shared-key",
            environment=dev_environment,
            created_by=owner_user,
        )
        flag_b = FeatureFlagService.create_flag(
            name="Flag B",
            key="shared-key",
            environment=staging_environment,
            created_by=owner_user,
        )
        assert flag_b.key == "shared-key"

    def test_high_risk_production_flag_requires_approval(
        self, prod_environment, owner_user
    ):
        flag = FeatureFlagService.create_flag(
            name="Risky Flag",
            key="risky-flag",
            environment=prod_environment,
            created_by=owner_user,
            risk_level=RiskLevel.HIGH,
        )
        assert flag.requires_approval is True
        assert flag.is_approved is False

    def test_low_risk_dev_flag_no_approval(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Safe Flag",
            key="safe-flag",
            environment=dev_environment,
            created_by=owner_user,
            risk_level=RiskLevel.LOW,
        )
        assert flag.requires_approval is False


# ============================================================
# Unit Tests: Flag Modification Rules
# ============================================================

class TestFlagModification:
    def test_cannot_modify_archived_flag(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Flag", key="arch-flag",
            environment=dev_environment, created_by=owner_user,
        )
        FeatureFlagService.archive_flag(flag)
        with pytest.raises(ValidationError, match="archived"):
            FeatureFlagService.update_flag(flag, owner_user, name="New Name")

    def test_cannot_change_key_after_creation(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Flag", key="immutable-key",
            environment=dev_environment, created_by=owner_user,
        )
        with pytest.raises(ValidationError, match="key"):
            FeatureFlagService.update_flag(flag, owner_user, key="new-key")

    def test_version_increments_on_update(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Flag", key="ver-flag",
            environment=dev_environment, created_by=owner_user,
        )
        assert flag.version == 1
        flag = FeatureFlagService.update_flag(flag, owner_user, name="Updated")
        assert flag.version == 2

    def test_unapproved_production_flag_cannot_be_modified(
        self, prod_environment, owner_user
    ):
        flag = FeatureFlagService.create_flag(
            name="Prod Flag", key="prod-mod",
            environment=prod_environment, created_by=owner_user,
            risk_level=RiskLevel.HIGH,
        )
        with pytest.raises(ValidationError, match="approval"):
            FeatureFlagService.update_flag(flag, owner_user, name="Changed")

    def test_mass_assignment_blocked(self, dev_environment, owner_user):
        """Verify internal fields cannot be set via update_flag."""
        flag = FeatureFlagService.create_flag(
            name="Flag", key="mass-flag",
            environment=dev_environment, created_by=owner_user,
        )
        flag = FeatureFlagService.update_flag(
            flag, owner_user, is_approved=True, version=999
        )
        # is_approved and version are NOT in UPDATABLE_FLAG_FIELDS
        assert flag.is_approved is False
        assert flag.version == 2  # incremented by 1, not set to 999


# ============================================================
# Unit Tests: Archive & Delete Rules
# ============================================================

class TestArchiveAndDelete:
    def test_archive_flag(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Flag", key="to-archive",
            environment=dev_environment, created_by=owner_user,
        )
        flag.is_enabled = True
        flag.save()
        flag = FeatureFlagService.archive_flag(flag)
        assert flag.status == FlagStatus.ARCHIVED
        assert flag.is_enabled is False

    def test_cannot_archive_flag_with_active_dependents(
        self, dev_environment, owner_user
    ):
        parent = FeatureFlagService.create_flag(
            name="Parent", key="parent-flag",
            environment=dev_environment, created_by=owner_user,
        )
        FeatureFlagService.create_flag(
            name="Child", key="child-flag",
            environment=dev_environment, created_by=owner_user,
            depends_on=parent,
        )
        with pytest.raises(ValidationError, match="active dependents"):
            FeatureFlagService.archive_flag(parent)

    def test_cannot_delete_flag_with_active_dependents(
        self, dev_environment, owner_user
    ):
        parent = FeatureFlagService.create_flag(
            name="Parent", key="del-parent",
            environment=dev_environment, created_by=owner_user,
        )
        FeatureFlagService.create_flag(
            name="Child", key="del-child",
            environment=dev_environment, created_by=owner_user,
            depends_on=parent,
        )
        with pytest.raises(ValidationError, match="active dependents"):
            FeatureFlagService.delete_flag(parent)

    def test_delete_flag_without_dependents(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Lonely", key="lonely-flag",
            environment=dev_environment, created_by=owner_user,
        )
        flag_id = flag.id
        FeatureFlagService.delete_flag(flag)
        assert not FeatureFlag.objects.filter(id=flag_id).exists()


# ============================================================
# Unit Tests: Toggle & Kill Switch
# ============================================================

class TestToggleAndKillSwitch:
    def test_toggle_flag_on(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Flag", key="toggle-on",
            environment=dev_environment, created_by=owner_user,
        )
        flag = FeatureFlagService.toggle_flag(flag, True, owner_user)
        assert flag.is_enabled is True

    def test_cannot_toggle_archived_flag(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Flag", key="toggle-arch",
            environment=dev_environment, created_by=owner_user,
        )
        FeatureFlagService.archive_flag(flag)
        with pytest.raises(ValidationError, match="archived"):
            FeatureFlagService.toggle_flag(flag, True, owner_user)

    def test_kill_switch_disables_flag(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Flag", key="kill-flag",
            environment=dev_environment, created_by=owner_user,
        )
        flag = FeatureFlagService.toggle_flag(flag, True, owner_user)
        flag = FeatureFlagService.activate_kill_switch(flag)
        assert flag.kill_switch is True
        assert flag.is_enabled is False

    def test_cannot_enable_with_kill_switch_active(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Flag", key="kill-block",
            environment=dev_environment, created_by=owner_user,
        )
        FeatureFlagService.activate_kill_switch(flag)
        with pytest.raises(ValidationError, match="Kill switch"):
            FeatureFlagService.toggle_flag(flag, True, owner_user)

    def test_deactivate_kill_switch(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Flag", key="kill-deact",
            environment=dev_environment, created_by=owner_user,
        )
        FeatureFlagService.activate_kill_switch(flag)
        flag = FeatureFlagService.deactivate_kill_switch(flag)
        assert flag.kill_switch is False


# ============================================================
# Unit Tests: Time-Based Activation
# ============================================================

class TestTimeBasedActivation:
    def test_flag_not_active_before_activation_time(self, dev_environment, owner_user):
        future = timezone.now() + timedelta(hours=1)
        flag = FeatureFlagService.create_flag(
            name="Future", key="future-flag",
            environment=dev_environment, created_by=owner_user,
            activate_at=future,
        )
        assert flag.is_within_activation_window is False

    def test_flag_expired(self, dev_environment, owner_user):
        past = timezone.now() - timedelta(hours=1)
        flag = FeatureFlagService.create_flag(
            name="Expired", key="expired-flag",
            environment=dev_environment, created_by=owner_user,
            expire_at=past,
        )
        assert flag.is_expired is True
        assert flag.is_within_activation_window is False

    def test_flag_within_window(self, dev_environment, owner_user):
        past = timezone.now() - timedelta(hours=1)
        future = timezone.now() + timedelta(hours=1)
        flag = FeatureFlagService.create_flag(
            name="Active", key="window-flag",
            environment=dev_environment, created_by=owner_user,
            activate_at=past, expire_at=future,
        )
        assert flag.is_within_activation_window is True

    def test_expire_before_activate_rejected(self, dev_environment, owner_user):
        now = timezone.now()
        with pytest.raises(ValidationError, match="after activation"):
            FeatureFlagService.create_flag(
                name="Bad", key="bad-time",
                environment=dev_environment, created_by=owner_user,
                activate_at=now + timedelta(hours=2),
                expire_at=now + timedelta(hours=1),
            )

    def test_auto_expire_flags(self, dev_environment, owner_user):
        past = timezone.now() - timedelta(hours=1)
        flag = FeatureFlagService.create_flag(
            name="Expiring", key="auto-expire",
            environment=dev_environment, created_by=owner_user,
            expire_at=past,
        )
        flag.is_enabled = True
        flag.save()
        count = FeatureFlagService.check_and_expire_flags()
        assert count == 1
        flag.refresh_from_db()
        assert flag.is_enabled is False


# ============================================================
# Unit Tests: Dependency Logic
# ============================================================

class TestDependencyLogic:
    def test_dependency_in_same_environment(self, dev_environment, owner_user):
        parent = FeatureFlagService.create_flag(
            name="Parent", key="dep-parent",
            environment=dev_environment, created_by=owner_user,
        )
        child = FeatureFlagService.create_flag(
            name="Child", key="dep-child",
            environment=dev_environment, created_by=owner_user,
            depends_on=parent,
        )
        assert child.depends_on == parent

    def test_dependency_cross_environment_rejected(
        self, dev_environment, staging_environment, owner_user
    ):
        parent = FeatureFlagService.create_flag(
            name="Parent", key="cross-parent",
            environment=staging_environment, created_by=owner_user,
        )
        with pytest.raises(ValidationError, match="same environment"):
            FeatureFlagService.create_flag(
                name="Child", key="cross-child",
                environment=dev_environment, created_by=owner_user,
                depends_on=parent,
            )

    def test_self_dependency_rejected(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Self", key="self-dep",
            environment=dev_environment, created_by=owner_user,
        )
        flag.depends_on = flag
        with pytest.raises(ValidationError, match="itself"):
            flag.save()


# ============================================================
# Unit Tests: Variant Percentage Logic
# ============================================================

class TestVariantPercentage:
    def test_multivariate_must_sum_to_100(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="MV", key="mv-pct",
            environment=dev_environment, created_by=owner_user,
            flag_type=FlagType.MULTIVARIATE,
        )
        with pytest.raises(ValidationError, match="sum to 100"):
            FlagVariantService.set_variants(flag, [
                {"name": "A", "value": "a", "rollout_percentage": 60},
                {"name": "B", "value": "b", "rollout_percentage": 30},
            ])

    def test_multivariate_valid_percentages(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="MV", key="mv-valid",
            environment=dev_environment, created_by=owner_user,
            flag_type=FlagType.MULTIVARIATE,
        )
        variants = FlagVariantService.set_variants(flag, [
            {"name": "A", "value": "a", "rollout_percentage": 50},
            {"name": "B", "value": "b", "rollout_percentage": 50},
        ])
        assert variants.count() == 2

    def test_experiment_must_sum_to_100(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Exp", key="exp-pct",
            environment=dev_environment, created_by=owner_user,
            flag_type=FlagType.EXPERIMENT,
        )
        with pytest.raises(ValidationError, match="sum to 100"):
            FlagVariantService.set_variants(flag, [
                {"name": "Control", "value": "c", "rollout_percentage": 10, "is_control": True},
                {"name": "Treatment", "value": "t", "rollout_percentage": 10},
            ])

    def test_cannot_set_variants_on_archived_flag(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Arch", key="arch-var",
            environment=dev_environment, created_by=owner_user,
            flag_type=FlagType.MULTIVARIATE,
        )
        FeatureFlagService.archive_flag(flag)
        with pytest.raises(ValidationError, match="archived"):
            FlagVariantService.set_variants(flag, [
                {"name": "A", "value": "a", "rollout_percentage": 100},
            ])

    def test_variant_percentage_out_of_range_rejected(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Bad", key="bad-pct",
            environment=dev_environment, created_by=owner_user,
            flag_type=FlagType.MULTIVARIATE,
        )
        with pytest.raises(ValidationError):
            FlagVariantService.set_variants(flag, [
                {"name": "A", "value": "a", "rollout_percentage": -10},
                {"name": "B", "value": "b", "rollout_percentage": 110},
            ])


# ============================================================
# Unit Tests: Evaluation Engine
# ============================================================

class TestEvaluationEngine:
    def test_evaluate_archived_flag(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Arch", key="eval-arch",
            environment=dev_environment, created_by=owner_user,
        )
        FeatureFlagService.archive_flag(flag)
        result = EvaluationEngine.evaluate(flag, "user1")
        assert result["variant"] is None
        assert result["reason"] == "flag_archived"

    def test_evaluate_disabled_flag(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Disabled", key="eval-dis",
            environment=dev_environment, created_by=owner_user,
        )
        result = EvaluationEngine.evaluate(flag, "user1")
        assert result["variant"] is None
        assert result["reason"] == "flag_disabled"

    def test_evaluate_kill_switch_active(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Kill", key="eval-kill",
            environment=dev_environment, created_by=owner_user,
        )
        flag.is_enabled = True
        flag.save()
        FeatureFlagService.activate_kill_switch(flag)
        result = EvaluationEngine.evaluate(flag, "user1")
        assert result["reason"] == "kill_switch_active"

    def test_evaluate_enabled_boolean_flag(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Enabled", key="eval-on",
            environment=dev_environment, created_by=owner_user,
        )
        FeatureFlagService.toggle_flag(flag, True, owner_user)
        result = EvaluationEngine.evaluate(flag, "user1")
        assert result["variant"] is True
        assert result["reason"] == "flag_enabled"

    def test_evaluate_parent_inactive(self, dev_environment, owner_user):
        parent = FeatureFlagService.create_flag(
            name="Parent", key="eval-parent",
            environment=dev_environment, created_by=owner_user,
        )
        child = FeatureFlagService.create_flag(
            name="Child", key="eval-child",
            environment=dev_environment, created_by=owner_user,
            depends_on=parent,
        )
        FeatureFlagService.toggle_flag(child, True, owner_user)
        result = EvaluationEngine.evaluate(child, "user1")
        assert result["reason"] == "parent_flag_inactive"

    def test_deterministic_percentage_rollout(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="MV", key="eval-mv",
            environment=dev_environment, created_by=owner_user,
            flag_type=FlagType.MULTIVARIATE,
        )
        FlagVariantService.set_variants(flag, [
            {"name": "A", "value": "variant_a", "rollout_percentage": 50},
            {"name": "B", "value": "variant_b", "rollout_percentage": 50},
        ])
        FeatureFlagService.toggle_flag(flag, True, owner_user)

        # Same user always gets same variant (deterministic)
        result1 = EvaluationEngine.evaluate(flag, "user123")
        result2 = EvaluationEngine.evaluate(flag, "user123")
        assert result1["variant"] == result2["variant"]
        assert result1["reason"] == "percentage_rollout"

    def test_outside_activation_window(self, dev_environment, owner_user):
        future = timezone.now() + timedelta(hours=1)
        flag = FeatureFlagService.create_flag(
            name="Future", key="eval-future",
            environment=dev_environment, created_by=owner_user,
            activate_at=future,
        )
        flag.is_enabled = True
        flag.save()
        result = EvaluationEngine.evaluate(flag, "user1")
        assert result["reason"] == "outside_activation_window"


# ============================================================
# Unit Tests: Stale Flag Detection
# ============================================================

class TestStaleFlagDetection:
    def test_stale_flag_detected(self, tenant, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Stale", key="stale-flag",
            environment=dev_environment, created_by=owner_user,
        )
        # Backdate created_at
        FeatureFlag.objects.filter(pk=flag.pk).update(
            created_at=timezone.now() - timedelta(days=60)
        )
        stale = FeatureFlagService.get_stale_flags(tenant, days=30)
        assert stale.filter(pk=flag.pk).exists()

    def test_recently_evaluated_not_stale(self, tenant, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Fresh", key="fresh-flag",
            environment=dev_environment, created_by=owner_user,
        )
        FeatureFlag.objects.filter(pk=flag.pk).update(
            last_evaluated_at=timezone.now(),
            created_at=timezone.now() - timedelta(days=60),
        )
        stale = FeatureFlagService.get_stale_flags(tenant, days=30)
        assert not stale.filter(pk=flag.pk).exists()
