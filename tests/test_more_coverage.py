from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory

from apps.accounts.permissions import IsAdminOrAbove
from apps.accounts.permissions import IsDeveloperOrAbove
from apps.accounts.permissions import IsOwner
from apps.accounts.permissions import RoleBasedPermission
from apps.core.exception_handler import custom_exception_handler
from apps.organizations.models import Organization
from apps.tasks.models import Task, TaskStatus
from apps.tasks.services import TaskWorkflowService
from apps.time_tracking.models import TimeEntry
from apps.time_tracking.services import TimeEntryService


@pytest.mark.django_db
class TestCoverageBoost:
    def test_permissions_classes(self, owner_user, developer_user, viewer_user):
        rf = APIRequestFactory()

        req = rf.get("/")
        req.user = owner_user
        assert IsOwner().has_permission(req, None) is True

        req.user = developer_user
        assert IsDeveloperOrAbove().has_permission(req, None) is True
        assert IsAdminOrAbove().has_permission(req, None) is False

        req.user = viewer_user
        assert IsDeveloperOrAbove().has_permission(req, None) is False

        post_req = rf.post("/")
        post_req.user = developer_user
        assert RoleBasedPermission().has_permission(post_req, None) is True

        del_req = rf.delete("/")
        del_req.user = developer_user
        assert RoleBasedPermission().has_permission(del_req, None) is False

    def test_exception_handler_validation_error(self):
        exc = ValidationError("bad")
        resp = custom_exception_handler(exc, {"view": "x"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "errors" in resp.data

    def test_exception_handler_unhandled_exception(self):
        resp = custom_exception_handler(Exception("boom"), {"view": "x"})
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert resp.data["error"]

    def test_organization_slug_autogeneration(self, db):
        org = Organization.objects.create(name="My Org")
        assert org.slug == "my-org"

    def test_task_workflow_restrictions_and_archived_protection(self, project_with_team, owner_user, developer_user, reviewer_user, viewer_user):
        task = Task.objects.create(
            project=project_with_team,
            title="T",
            description="",
            assignee=developer_user,
            created_by=owner_user,
        )

        # viewer cannot change status
        with pytest.raises(ValidationError):
            TaskWorkflowService.transition(task=task, actor=viewer_user, to_status=TaskStatus.IN_PROGRESS)

        # non-assignee (non-owner) cannot move backlog->in_progress
        with pytest.raises(ValidationError):
            TaskWorkflowService.transition(task=task, actor=reviewer_user, to_status=TaskStatus.IN_PROGRESS)

        # assignee can
        TaskWorkflowService.transition(task=task, actor=developer_user, to_status=TaskStatus.IN_PROGRESS)

        # archived tasks cannot change
        TaskWorkflowService.transition(task=task, actor=owner_user, to_status=TaskStatus.ARCHIVED)
        with pytest.raises(ValidationError):
            TaskWorkflowService.transition(task=task, actor=owner_user, to_status=TaskStatus.BACKLOG)

    def test_time_entry_immutability(self, project_with_team, owner_user):
        task = Task.objects.create(project=project_with_team, title="T", description="", created_by=owner_user)
        entry = TimeEntry.objects.create(user=owner_user, task=task, hours="1.00", date=timezone.now().date())

        # still mutable
        TimeEntryService.assert_entry_mutable(entry)

        # simulate old
        entry.created_at = timezone.now() - (TimeEntryService.IMMUTABLE_AFTER + timedelta(seconds=1))
        entry.save(update_fields=["created_at"])
        with pytest.raises(ValidationError):
            TimeEntryService.assert_entry_mutable(entry)
