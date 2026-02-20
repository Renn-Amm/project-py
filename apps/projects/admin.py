from django.contrib import admin

from apps.projects.models import Project, ProjectMember


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "organization", "name", "created_by", "created_at")
    list_filter = ("organization",)
    search_fields = ("name", "description")
    ordering = ("name",)


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "user", "added_at")
    list_filter = ("project",)
    search_fields = ("project__name", "user__email")
