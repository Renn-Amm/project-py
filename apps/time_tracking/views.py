from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.tasks.models import Task
from apps.time_tracking.models import TimeEntry
from apps.time_tracking.serializers import TimeEntrySerializer
from apps.time_tracking.services import TimeEntryService


class TimeEntryViewSet(viewsets.ModelViewSet):
    serializer_class = TimeEntrySerializer

    def get_queryset(self):
        org = getattr(self.request.user, "organization", None)
        if not org:
            return TimeEntry.objects.none()
        return (
            TimeEntry.objects
            .filter(
                task__project__organization=org,
                task__project__memberships__user=self.request.user,
            )
            .select_related("task", "user")
            .distinct()
        )

    def create(self, request, *args, **kwargs):
        org = getattr(request.user, "organization", None)
        task = get_object_or_404(
            Task,
            pk=request.data.get("task"),
            project__organization=org,
            project__memberships__user=request.user,
        )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entry = TimeEntryService.create_time_entry(
            user=request.user,
            task=task,
            hours=serializer.validated_data["hours"],
            date=serializer.validated_data["date"],
        )
        return Response(TimeEntrySerializer(entry).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        entry = self.get_object()
        TimeEntryService.assert_entry_mutable(entry)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        entry = self.get_object()
        TimeEntryService.assert_entry_mutable(entry)
        task = entry.task
        response = super().destroy(request, *args, **kwargs)
        TimeEntryService.recalculate_task_total(task)
        return response
