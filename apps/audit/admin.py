from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "actor",
        "action",
        "object_type",
        "object_id",
        "organization",
        "timestamp",
    )
    list_filter = ("action", "object_type")
    search_fields = ("object_id", "actor__email")
    readonly_fields = ("timestamp",)
    date_hierarchy = "timestamp"
