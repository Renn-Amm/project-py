from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.projects.models import Project
from apps.tasks.models import Task, TaskDependency, TaskStatusChange
from apps.tasks.serializers import (
    TaskDependencySerializer,
    TaskSerializer,
    TaskStatusChangeSerializer,
    TaskTransitionSerializer,
)
from apps.tasks.services import DependencyService, TaskWorkflowService


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer

    def get_queryset(self):
        org = getattr(self.request.user, "organization", None)
        if not org:
            return Task.objects.none()
        return (
            Task.objects
            .filter(project__organization=org, project__memberships__user=self.request.user)
            .select_related("project", "assignee", "reviewer", "created_by", "review_approved_by", "sprint")
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
        # Enforce org membership for assignee and reviewer
        assignee_id = self.request.data.get("assignee")
        reviewer_id = self.request.data.get("reviewer")
        if assignee_id:
            get_object_or_404(type(self.request.user).objects, pk=assignee_id, organization=org)
        if reviewer_id:
            get_object_or_404(type(self.request.user).objects, pk=reviewer_id, organization=org)

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

    @action(detail=True, methods=["get", "post"], url_path="dependencies")
    def dependencies(self, request, pk=None):
        task = self.get_object()

        if request.method == "GET":
            deps = TaskDependency.objects.filter(task=task).select_related("depends_on")
            return Response(TaskDependencySerializer(deps, many=True).data)

        depends_on_id = request.data.get("depends_on")
        depends_on = get_object_or_404(Task, pk=depends_on_id, project__organization=request.user.organization)

        dep = DependencyService.add_dependency(task=task, depends_on=depends_on, actor=request.user)
        return Response(TaskDependencySerializer(dep).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path=r"dependencies/(?P<dep_task_id>[^/.]+)")
    def remove_dependency(self, request, pk=None, dep_task_id=None):
        task = self.get_object()
        depends_on = get_object_or_404(Task, pk=dep_task_id, project__organization=request.user.organization)
        DependencyService.remove_dependency(task=task, depends_on=depends_on, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
