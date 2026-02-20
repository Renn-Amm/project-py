from rest_framework import serializers

from apps.projects.models import Project, ProjectMember


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            "id",
            "organization",
            "name",
            "description",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization", "created_by", "created_at", "updated_at"]


class ProjectMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectMember
        fields = ["id", "project", "user", "added_at"]
        read_only_fields = ["id", "added_at"]
