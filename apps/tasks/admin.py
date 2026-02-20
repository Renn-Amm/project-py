from django.contrib import admin

from apps.tasks.models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "title", "status", "priority", "assignee", "reviewer", "is_overdue")
    list_filter = ("status", "priority", "is_overdue")
    search_fields = ("title", "description")
    ordering = ("-created_at",)
