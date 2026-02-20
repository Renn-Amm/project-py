from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.projects.models import Project
from apps.tasks.models import Task, TaskStatusChange
from apps.tasks.serializers import (
    TaskSerializer,
    TaskStatusChangeSerializer,
    TaskTransitionSerializer,
)
from apps.tasks.services import TaskWorkflowService


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer

    def get_queryset(self):
        org = getattr(self.request.user, "organization", None)
        if not org:
            return Task.objects.none()
        return (
            Task.objects
            .filter(project__organization=org, project__memberships__user=self.request.user)
            .select_related("project", "assignee", "reviewer", "created_by", "review_approved_by")
            .distinct()
        )

    def perform_create(self, serializer):
        org = getattr(self.request.user, "organization", None)
        project = get_object_or_404(
            Project,
            pk=self.request.data.get("project"),
            organization=org,
            memberships__user=self.request.user,
        )
        serializer.save(project=project, created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="transition")
    def transition(self, request, pk=None):
        task = self.get_object()
        serializer = TaskTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        to_status = serializer.validated_data["to_status"]
        result = TaskWorkflowService.transition(task=task, actor=request.user, to_status=to_status)
        return Response(TaskSerializer(result.task).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="status-changes")
    def status_changes(self, request, pk=None):
        task = self.get_object()
        changes = TaskStatusChange.objects.filter(task=task).select_related("actor").order_by("created_at")
        return Response(TaskStatusChangeSerializer(changes, many=True).data)
