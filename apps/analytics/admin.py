from django.contrib import admin

from apps.analytics.models import EvaluationEvent


@admin.register(EvaluationEvent)
class EvaluationEventAdmin(admin.ModelAdmin):
    list_display = ("flag_key", "user_identifier", "evaluated_variant", "environment_name", "timestamp")
    list_filter = ("environment_name", "flag_key")
    search_fields = ("flag_key", "user_identifier")
    date_hierarchy = "timestamp"
    readonly_fields = ("timestamp",)
