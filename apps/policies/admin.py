from django.contrib import admin

from apps.policies.models import ApprovalRequest, Policy


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ("tenant", "policy_type", "is_enabled", "created_at")
    list_filter = ("policy_type", "is_enabled")


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ("flag", "requested_by", "status", "reviewed_by", "created_at")
    list_filter = ("status",)
    readonly_fields = ("created_at", "reviewed_at")
