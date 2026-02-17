from django.contrib import admin

from apps.targeting.models import TargetingRule


@admin.register(TargetingRule)
class TargetingRuleAdmin(admin.ModelAdmin):
    list_display = ("flag", "rule_type", "operator", "value", "priority", "is_active")
    list_filter = ("rule_type", "operator", "is_active")
    search_fields = ("flag__key",)
