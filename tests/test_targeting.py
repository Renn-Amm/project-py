import pytest

from apps.targeting.models import Operator, RuleType, TargetingRule
from apps.targeting.services import TargetingService
from apps.feature_flags.services import FeatureFlagService


# ============================================================
# Unit Tests: Targeting Rule Operator Logic
# ============================================================

class TestOperatorEquals:
    def test_equals_match(self):
        result = TargetingService._apply_operator(Operator.EQUALS, "abc", "abc")
        assert result is True

    def test_equals_no_match(self):
        result = TargetingService._apply_operator(Operator.EQUALS, "abc", "xyz")
        assert result is False


class TestOperatorNotEquals:
    def test_not_equals_match(self):
        result = TargetingService._apply_operator(Operator.NOT_EQUALS, "abc", "xyz")
        assert result is True

    def test_not_equals_no_match(self):
        result = TargetingService._apply_operator(Operator.NOT_EQUALS, "abc", "abc")
        assert result is False


class TestOperatorContains:
    def test_contains_match(self):
        result = TargetingService._apply_operator(Operator.CONTAINS, "hello world", "world")
        assert result is True

    def test_contains_no_match(self):
        result = TargetingService._apply_operator(Operator.CONTAINS, "hello", "world")
        assert result is False


class TestOperatorNotContains:
    def test_not_contains_match(self):
        result = TargetingService._apply_operator(Operator.NOT_CONTAINS, "hello", "world")
        assert result is True

    def test_not_contains_no_match(self):
        result = TargetingService._apply_operator(Operator.NOT_CONTAINS, "hello world", "world")
        assert result is False


class TestOperatorGreaterThan:
    def test_greater_than_match(self):
        result = TargetingService._apply_operator(Operator.GREATER_THAN, 10, 5)
        assert result is True

    def test_greater_than_no_match(self):
        result = TargetingService._apply_operator(Operator.GREATER_THAN, 3, 5)
        assert result is False

    def test_greater_than_non_numeric(self):
        result = TargetingService._apply_operator(Operator.GREATER_THAN, "abc", "5")
        assert result is False


class TestOperatorLessThan:
    def test_less_than_match(self):
        result = TargetingService._apply_operator(Operator.LESS_THAN, 3, 5)
        assert result is True

    def test_less_than_no_match(self):
        result = TargetingService._apply_operator(Operator.LESS_THAN, 10, 5)
        assert result is False


class TestOperatorInList:
    def test_in_list_match(self):
        result = TargetingService._apply_operator(Operator.IN_LIST, "US", ["US", "UK", "CA"])
        assert result is True

    def test_in_list_no_match(self):
        result = TargetingService._apply_operator(Operator.IN_LIST, "FR", ["US", "UK", "CA"])
        assert result is False

    def test_in_list_non_list_value(self):
        result = TargetingService._apply_operator(Operator.IN_LIST, "US", "US")
        assert result is False


class TestOperatorNotInList:
    def test_not_in_list_match(self):
        result = TargetingService._apply_operator(Operator.NOT_IN_LIST, "FR", ["US", "UK"])
        assert result is True

    def test_not_in_list_no_match(self):
        result = TargetingService._apply_operator(Operator.NOT_IN_LIST, "US", ["US", "UK"])
        assert result is False


class TestOperatorStartsWith:
    def test_starts_with_match(self):
        result = TargetingService._apply_operator(Operator.STARTS_WITH, "hello world", "hello")
        assert result is True

    def test_starts_with_no_match(self):
        result = TargetingService._apply_operator(Operator.STARTS_WITH, "hello world", "world")
        assert result is False


class TestOperatorEndsWith:
    def test_ends_with_match(self):
        result = TargetingService._apply_operator(Operator.ENDS_WITH, "hello world", "world")
        assert result is True

    def test_ends_with_no_match(self):
        result = TargetingService._apply_operator(Operator.ENDS_WITH, "hello world", "hello")
        assert result is False


class TestOperatorRegex:
    def test_regex_match(self):
        result = TargetingService._apply_operator(Operator.REGEX, "user123", r"user\d+")
        assert result is True

    def test_regex_no_match(self):
        result = TargetingService._apply_operator(Operator.REGEX, "admin", r"user\d+")
        assert result is False

    def test_regex_invalid_pattern(self):
        result = TargetingService._apply_operator(Operator.REGEX, "test", r"[invalid")
        assert result is False


# ============================================================
# Unit Tests: Targeting Rule Evaluation with Attributes
# ============================================================

class TestRuleEvaluation:
    @pytest.fixture
    def flag_with_rules(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Targeted", key="targeted-flag",
            environment=dev_environment, created_by=owner_user,
        )
        rule1 = TargetingRule.objects.create(
            flag=flag,
            rule_type=RuleType.USER_ID,
            operator=Operator.EQUALS,
            value="vip-user",
            variant_value={"special": True},
            priority=1,
        )
        rule2 = TargetingRule.objects.create(
            flag=flag,
            rule_type=RuleType.COUNTRY,
            operator=Operator.IN_LIST,
            value=["US", "UK"],
            variant_value={"region": "english"},
            priority=2,
        )
        rule3 = TargetingRule.objects.create(
            flag=flag,
            rule_type=RuleType.CUSTOM_ATTRIBUTE,
            attribute_key="plan",
            operator=Operator.EQUALS,
            value="enterprise",
            variant_value={"tier": "enterprise"},
            priority=3,
        )
        return flag, [rule1, rule2, rule3]

    def test_user_id_rule_matches(self, flag_with_rules):
        flag, rules = flag_with_rules
        result = TargetingService.evaluate_rules(rules, "vip-user", {})
        assert result is not None
        assert result["variant"] == {"special": True}

    def test_country_rule_matches(self, flag_with_rules):
        flag, rules = flag_with_rules
        result = TargetingService.evaluate_rules(
            rules, "regular-user", {"country": "US"}
        )
        assert result is not None
        assert result["variant"] == {"region": "english"}

    def test_custom_attribute_rule_matches(self, flag_with_rules):
        flag, rules = flag_with_rules
        result = TargetingService.evaluate_rules(
            rules, "regular-user", {"country": "FR", "plan": "enterprise"}
        )
        assert result is not None
        assert result["variant"] == {"tier": "enterprise"}

    def test_no_rule_matches(self, flag_with_rules):
        flag, rules = flag_with_rules
        result = TargetingService.evaluate_rules(
            rules, "regular-user", {"country": "FR", "plan": "free"}
        )
        assert result is None

    def test_priority_order_respected(self, flag_with_rules):
        """VIP user rule (priority=1) should match before country rule (priority=2)."""
        flag, rules = flag_with_rules
        result = TargetingService.evaluate_rules(
            rules, "vip-user", {"country": "US"}
        )
        assert result["variant"] == {"special": True}

    def test_inactive_rule_skipped(self, flag_with_rules):
        flag, rules = flag_with_rules
        rules[0].is_active = False
        rules[0].save()
        result = TargetingService.evaluate_rules(
            rules, "vip-user", {"country": "US"}
        )
        # Should skip user_id rule and match country rule instead
        assert result["variant"] == {"region": "english"}

    def test_email_rule_type(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Email", key="email-rule",
            environment=dev_environment, created_by=owner_user,
        )
        rule = TargetingRule.objects.create(
            flag=flag,
            rule_type=RuleType.EMAIL,
            operator=Operator.ENDS_WITH,
            value="@company.com",
            variant_value=True,
            priority=1,
        )
        result = TargetingService.evaluate_rules(
            [rule], "user1", {"email": "alice@company.com"}
        )
        assert result is not None
        assert result["variant"] is True

    def test_role_rule_type(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Role", key="role-rule",
            environment=dev_environment, created_by=owner_user,
        )
        rule = TargetingRule.objects.create(
            flag=flag,
            rule_type=RuleType.ROLE,
            operator=Operator.EQUALS,
            value="admin",
            variant_value={"admin_feature": True},
            priority=1,
        )
        result = TargetingService.evaluate_rules(
            [rule], "user1", {"role": "admin"}
        )
        assert result is not None

    def test_missing_attribute_returns_no_match(self, dev_environment, owner_user):
        flag = FeatureFlagService.create_flag(
            name="Missing", key="missing-attr",
            environment=dev_environment, created_by=owner_user,
        )
        rule = TargetingRule.objects.create(
            flag=flag,
            rule_type=RuleType.CUSTOM_ATTRIBUTE,
            attribute_key="nonexistent",
            operator=Operator.EQUALS,
            value="something",
            variant_value=True,
            priority=1,
        )
        result = TargetingService.evaluate_rules([rule], "user1", {})
        assert result is None
