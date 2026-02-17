import re

from apps.targeting.models import Operator, RuleType


class TargetingService:
    @staticmethod
    def evaluate_rules(rules, user_identifier, attributes):
        for rule in rules:
            if not rule.is_active:
                continue
            if TargetingService._evaluate_single_rule(rule, user_identifier, attributes):
                return {
                    "variant": rule.variant_value,
                    "rule_id": rule.id,
                }
        return None

    @staticmethod
    def _evaluate_single_rule(rule, user_identifier, attributes):
        actual_value = TargetingService._get_actual_value(
            rule.rule_type, rule.attribute_key, user_identifier, attributes
        )
        if actual_value is None:
            return False
        return TargetingService._apply_operator(rule.operator, actual_value, rule.value)

    @staticmethod
    def _get_actual_value(rule_type, attribute_key, user_identifier, attributes):
        if rule_type == RuleType.USER_ID:
            return user_identifier
        elif rule_type == RuleType.EMAIL:
            return attributes.get("email")
        elif rule_type == RuleType.ROLE:
            return attributes.get("role")
        elif rule_type == RuleType.COUNTRY:
            return attributes.get("country")
        elif rule_type == RuleType.CUSTOM_ATTRIBUTE:
            return attributes.get(attribute_key)
        return None

    @staticmethod
    def _apply_operator(operator, actual_value, rule_value):
        actual_str = str(actual_value)
        rule_str = str(rule_value)

        if operator == Operator.EQUALS:
            return actual_str == rule_str

        elif operator == Operator.NOT_EQUALS:
            return actual_str != rule_str

        elif operator == Operator.CONTAINS:
            return rule_str in actual_str

        elif operator == Operator.NOT_CONTAINS:
            return rule_str not in actual_str

        elif operator == Operator.GREATER_THAN:
            try:
                return float(actual_value) > float(rule_value)
            except (ValueError, TypeError):
                return False

        elif operator == Operator.LESS_THAN:
            try:
                return float(actual_value) < float(rule_value)
            except (ValueError, TypeError):
                return False

        elif operator == Operator.IN_LIST:
            if isinstance(rule_value, list):
                return actual_str in [str(v) for v in rule_value]
            return False

        elif operator == Operator.NOT_IN_LIST:
            if isinstance(rule_value, list):
                return actual_str not in [str(v) for v in rule_value]
            return True

        elif operator == Operator.STARTS_WITH:
            return actual_str.startswith(rule_str)

        elif operator == Operator.ENDS_WITH:
            return actual_str.endswith(rule_str)

        elif operator == Operator.REGEX:
            try:
                return bool(re.match(rule_str, actual_str, flags=re.DOTALL, timeout=1))
            except (re.error, TimeoutError):
                return False

        return False
