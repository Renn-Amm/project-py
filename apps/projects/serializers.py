from rest_framework import serializers

from apps.projects.models import Project, ProjectMember, Sprint


class SprintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sprint
        fields = [
            "id",
            "project",
            "name",
            "goal",
            "start_date",
            "end_date",
            "is_closed",
            "created_at",
        ]
        read_only_fields = ["id", "project", "is_closed", "created_at"]


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
