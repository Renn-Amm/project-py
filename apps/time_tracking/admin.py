from django.contrib import admin

from apps.time_tracking.models import TimeEntry


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "user", "hours", "date", "created_at")
    list_filter = ("date",)
    search_fields = ("task__title", "user__email")
    ordering = ("-created_at",)
