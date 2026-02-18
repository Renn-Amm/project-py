import hashlib
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from apps.feature_flags.models import (
    FeatureFlag,
    FlagStatus,
    FlagType,
    FlagVariant,
    RiskLevel,
)

# Whitelist of fields that can be updated via the update_flag service method.
# Prevents mass-assignment of internal fields like is_approved, version, etc.
UPDATABLE_FLAG_FIELDS = {
    "name", "description", "risk_level", "is_enabled",
    "activate_at", "expire_at",
}


class FeatureFlagService:
    @staticmethod
    @transaction.atomic
    def create_flag(*, name, key, environment, created_by, flag_type=FlagType.BOOLEAN,
                    description="", risk_level=RiskLevel.LOW, depends_on=None,
                    activate_at=None, expire_at=None):
        # Use select_for_update on the environment to serialize flag creation
        # and prevent race conditions on the unique_together constraint.
        from apps.tenants.models import Environment
        Environment.objects.select_for_update().get(pk=environment.pk)

        if FeatureFlag.objects.filter(key=key, environment=environment).exists():
            raise ValidationError(f"Flag key '{key}' already exists in this environment.")

        requires_approval = (
            environment.is_production
            and risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        )

        flag = FeatureFlag(
            name=name,
            key=key,
            description=description,
            flag_type=flag_type,
            environment=environment,
            risk_level=risk_level,
            created_by=created_by,
            depends_on=depends_on,
            activate_at=activate_at,
            expire_at=expire_at,
            requires_approval=requires_approval,
        )
        flag.save()

        if flag_type == FlagType.BOOLEAN:
            FlagVariant.objects.create(
                flag=flag, name="enabled", value=True, rollout_percentage=100
            )

        return flag

    @staticmethod
    @transaction.atomic
    def update_flag(flag, user, **updates):
        # Re-fetch with row lock to prevent concurrent modification
        db_flag = FeatureFlag.objects.select_for_update().get(pk=flag.pk)

        if db_flag.status == FlagStatus.ARCHIVED:
            raise ValidationError("Cannot modify an archived flag.")

        if db_flag.is_production and db_flag.requires_approval and not db_flag.is_approved:
            raise ValidationError(
                "Production flag requires approval before modification."
            )

        # Enforce key immutability
        if "key" in updates and updates["key"] != db_flag.key:
            raise ValidationError("Cannot change 'key' after creation.")

        # Only allow whitelisted fields to prevent mass-assignment attacks
        for field, value in updates.items():
            if field in UPDATABLE_FLAG_FIELDS:
                setattr(db_flag, field, value)

        db_flag.version += 1
        db_flag.save()
        flag.refresh_from_db()
        return flag

    @staticmethod
    @transaction.atomic
    def archive_flag(flag):
        db_flag = FeatureFlag.objects.select_for_update().get(pk=flag.pk)
        if db_flag.dependents.filter(status=FlagStatus.ACTIVE).exists():
            raise ValidationError(
                "Cannot archive flag with active dependents."
            )
        db_flag.status = FlagStatus.ARCHIVED
        db_flag.is_enabled = False
        db_flag.save()
        flag.refresh_from_db()
        return flag

    @staticmethod
    @transaction.atomic
    def toggle_flag(flag, enabled, user):
        db_flag = FeatureFlag.objects.select_for_update().get(pk=flag.pk)

        if db_flag.status == FlagStatus.ARCHIVED:
            raise ValidationError("Cannot toggle an archived flag.")

        if db_flag.kill_switch and enabled:
            raise ValidationError("Kill switch is active. Cannot enable flag.")

        if enabled and db_flag.is_production and db_flag.requires_approval and not db_flag.is_approved:
            raise ValidationError(
                "Production flag requires approval before enabling."
            )

        db_flag.is_enabled = enabled
        db_flag.version += 1
        db_flag.save()
        flag.refresh_from_db()
        return flag

    @staticmethod
    @transaction.atomic
    def activate_kill_switch(flag):
        db_flag = FeatureFlag.objects.select_for_update().get(pk=flag.pk)
        db_flag.kill_switch = True
        db_flag.is_enabled = False
        db_flag.version += 1
        db_flag.save()
        flag.refresh_from_db()
        return flag

    @staticmethod
    @transaction.atomic
    def deactivate_kill_switch(flag):
        db_flag = FeatureFlag.objects.select_for_update().get(pk=flag.pk)
        db_flag.kill_switch = False
        db_flag.version += 1
        db_flag.save()
        flag.refresh_from_db()
        return flag

    @staticmethod
    def check_and_expire_flags():
        now = timezone.now()
        expired = FeatureFlag.objects.filter(
            expire_at__lte=now,
            is_enabled=True,
            status=FlagStatus.ACTIVE,
        )
        count = expired.update(is_enabled=False)
        return count

    @staticmethod
    def get_stale_flags(tenant, days=30):
        threshold = timezone.now() - timezone.timedelta(days=days)
        return FeatureFlag.objects.filter(
            environment__tenant=tenant,
            status=FlagStatus.ACTIVE,
            last_evaluated_at__lt=threshold,
        ) | FeatureFlag.objects.filter(
            environment__tenant=tenant,
            status=FlagStatus.ACTIVE,
            last_evaluated_at__isnull=True,
            created_at__lt=threshold,
        )

    @staticmethod
    @transaction.atomic
    def delete_flag(flag):
        flag = FeatureFlag.objects.select_for_update().get(pk=flag.pk)
        if flag.dependents.filter(status=FlagStatus.ACTIVE).exists():
            raise ValidationError(
                "Cannot delete flag with active dependents."
            )
        flag.delete()


class FlagVariantService:
    @staticmethod
    @transaction.atomic
    def set_variants(flag, variants_data):
        # Lock the flag row to prevent concurrent variant modification
        flag = FeatureFlag.objects.select_for_update().get(pk=flag.pk)

        if flag.status == FlagStatus.ARCHIVED:
            raise ValidationError("Cannot modify variants of an archived flag.")

        if flag.flag_type in (FlagType.MULTIVARIATE, FlagType.EXPERIMENT):
            total = sum(Decimal(str(v["rollout_percentage"])) for v in variants_data)
            if total != Decimal("100"):
                raise ValidationError(
                    f"Variant percentages must sum to 100. Current sum: {total}"
                )

        flag.variants.all().delete()
        variants = []
        for v_data in variants_data:
            variant = FlagVariant(
                flag=flag,
                name=v_data["name"],
                value=v_data["value"],
                rollout_percentage=Decimal(str(v_data["rollout_percentage"])),
                is_control=v_data.get("is_control", False),
            )
            variant.full_clean()
            variants.append(variant)
        FlagVariant.objects.bulk_create(variants)
        return flag.variants.all()

    @staticmethod
    def validate_percentage_sum(flag):
        total = flag.variants.aggregate(
            total=models.Sum("rollout_percentage")
        )["total"] or Decimal("0")
        if flag.flag_type in (FlagType.MULTIVARIATE, FlagType.EXPERIMENT):
            if total != Decimal("100"):
                raise ValidationError(
                    f"Variant percentages must sum to 100. Current sum: {total}"
                )
        return True


class EvaluationEngine:
    @staticmethod
    def _hash_key(flag_key, user_identifier):
        raw = f"{flag_key}:{user_identifier}"
        hash_val = int(hashlib.sha256(raw.encode()).hexdigest(), 16)
        return hash_val % 10000

    @staticmethod
    def evaluate(flag, user_identifier, attributes=None, targeting_rules=None):
        if flag.status == FlagStatus.ARCHIVED:
            return {
                "variant": None,
                "reason": "flag_archived",
                "rule_matched": None,
            }

        if flag.kill_switch:
            return {
                "variant": None,
                "reason": "kill_switch_active",
                "rule_matched": None,
            }

        if not flag.is_enabled:
            return {
                "variant": None,
                "reason": "flag_disabled",
                "rule_matched": None,
            }

        if not flag.is_within_activation_window:
            return {
                "variant": None,
                "reason": "outside_activation_window",
                "rule_matched": None,
            }

        if flag.depends_on:
            parent = flag.depends_on
            if not parent.is_enabled or parent.status != FlagStatus.ACTIVE:
                return {
                    "variant": None,
                    "reason": "parent_flag_inactive",
                    "rule_matched": None,
                }

        if targeting_rules:
            from apps.targeting.services import TargetingService
            rule_result = TargetingService.evaluate_rules(
                targeting_rules, user_identifier, attributes or {}
            )
            if rule_result is not None:
                return {
                    "variant": rule_result["variant"],
                    "reason": "targeting_rule_match",
                    "rule_matched": rule_result["rule_id"],
                }

        if flag.flag_type == FlagType.BOOLEAN:
            return {
                "variant": True,
                "reason": "flag_enabled",
                "rule_matched": None,
            }

        variants = list(flag.variants.all().order_by("name"))
        if not variants:
            return {
                "variant": None,
                "reason": "no_variants_configured",
                "rule_matched": None,
            }

        hash_value = EvaluationEngine._hash_key(flag.key, user_identifier)
        cumulative = Decimal("0")
        for variant in variants:
            cumulative += variant.rollout_percentage * 100
            if hash_value < int(cumulative):
                return {
                    "variant": variant.value,
                    "reason": "percentage_rollout",
                    "rule_matched": None,
                }

        return {
            "variant": variants[-1].value,
            "reason": "percentage_rollout_fallback",
            "rule_matched": None,
        }
