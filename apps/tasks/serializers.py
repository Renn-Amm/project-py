from rest_framework import serializers

from apps.tasks.models import Task, TaskDependency, TaskStatus, TaskStatusChange


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            "id",
            "project",
            "title",
            "description",
            "priority",
            "status",
            "sprint",
            "assignee",
            "reviewer",
            "deadline",
            "estimated_time_hours",
            "total_logged_time_hours",
            "is_overdue",
            "overdue_marked_at",
            "created_by",
            "created_at",
            "updated_at",
            "completed_at",
            "review_approved_at",
            "review_approved_by",
        ]
        read_only_fields = [
            "id",
            "status",
            "total_logged_time_hours",
            "is_overdue",
            "overdue_marked_at",
            "created_by",
            "created_at",
            "updated_at",
            "completed_at",
            "review_approved_at",
            "review_approved_by",
        ]


class TaskStatusChangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskStatusChange
        fields = ["id", "task", "from_status", "to_status", "actor", "created_at"]
        read_only_fields = fields


class TaskTransitionSerializer(serializers.Serializer):
    to_status = serializers.ChoiceField(choices=TaskStatus.choices)


class TaskDependencySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskDependency
        fields = ["id", "task", "depends_on", "created_at"]
        read_only_fields = ["id", "created_at"]
