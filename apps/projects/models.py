from django.conf import settings
from django.db import models


class Project(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="projects",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_projects",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["organization", "name"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="uniq_project_org_name"),
        ]

    def __str__(self) -> str:
        return self.name


class ProjectMember(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_memberships")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["project", "user"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["project", "user"], name="uniq_project_member"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} in {self.project_id}"
