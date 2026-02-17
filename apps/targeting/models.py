from django.db import models


class RuleType(models.TextChoices):
    USER_ID = "user_id", "User ID"
    ROLE = "role", "Role"
    COUNTRY = "country", "Country"
    CUSTOM_ATTRIBUTE = "custom_attribute", "Custom Attribute"
    EMAIL = "email", "Email"
    PERCENTAGE = "percentage", "Percentage"


class Operator(models.TextChoices):
    EQUALS = "equals", "Equals"
    NOT_EQUALS = "not_equals", "Not Equals"
    CONTAINS = "contains", "Contains"
    NOT_CONTAINS = "not_contains", "Not Contains"
    GREATER_THAN = "greater_than", "Greater Than"
    LESS_THAN = "less_than", "Less Than"
    IN_LIST = "in_list", "In List"
    NOT_IN_LIST = "not_in_list", "Not In List"
    STARTS_WITH = "starts_with", "Starts With"
    ENDS_WITH = "ends_with", "Ends With"
    REGEX = "regex", "Regex"


class TargetingRule(models.Model):
    flag = models.ForeignKey(
        "feature_flags.FeatureFlag",
        on_delete=models.CASCADE,
        related_name="targeting_rules",
    )
    rule_type = models.CharField(max_length=30, choices=RuleType.choices)
    attribute_key = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Attribute key for custom_attribute rule type",
    )
    operator = models.CharField(max_length=20, choices=Operator.choices)
    value = models.JSONField()
    variant_value = models.JSONField(
        null=True,
        blank=True,
        help_text="Variant to serve when rule matches",
    )
    priority = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "targeting_targetingrule"
        ordering = ["priority"]

    def __str__(self):
        return f"Rule {self.id}: {self.rule_type} {self.operator} {self.value}"
