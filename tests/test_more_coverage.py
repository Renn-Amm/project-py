from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.test import RequestFactory
from django.utils import timezone
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from rest_framework import status
from rest_framework.test import APIRequestFactory

from apps.accounts.permissions import IsAdminOrAbove
from apps.accounts.permissions import IsDeveloperOrAbove
from apps.accounts.permissions import IsOwner
from apps.accounts.permissions import RoleBasedPermission
from apps.audit.models import AuditLog
from apps.audit.services import AuditService
from apps.core.exception_handler import custom_exception_handler
from apps.core.views import HealthCheckView
from apps.core.views import signup_view
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

    def test_audit_service_filters(self, owner_user):
        org = owner_user.organization

        AuditService.log(
            actor=owner_user,
            organization=org,
            action="create",
            object_type="Project",
            object_id="1",
            metadata={"password": "secret"},
        )
        AuditService.log(
            actor=owner_user,
            organization=org,
            action="delete",
            object_type="Task",
            object_id="2",
        )

        assert AuditLog.objects.filter(organization=org).count() == 2
        assert AuditService.get_logs_for_object("Project", "1").count() == 1
        assert AuditService.get_logs_for_organization(org, {"action": "create"}).count() == 1
        assert AuditService.get_logs_for_organization(org, {"object_type": "Task"}).count() == 1
        assert AuditService.get_logs_for_organization(org, {"actor_id": owner_user.id}).count() == 2

    def test_health_check_view(self, db):
        rf = APIRequestFactory()
        req = rf.get("/api/health/")
        resp = HealthCheckView.as_view()(req)
        assert resp.status_code in (200, 503)
        assert "status" in resp.data
        assert "checks" in resp.data

    def test_signup_view_validation_and_duplicate_email(self, db):
        rf = RequestFactory()

        def _attach_messages(request):
            middleware = SessionMiddleware(lambda r: None)
            middleware.process_request(request)
            request.session.save()
            request._messages = FallbackStorage(request)

        req_missing = rf.post(
            "/signup/",
            data={"email": "a@example.com", "password": "testpass123"},
        )
        req_missing.user = type("Anon", (), {"is_authenticated": False})()
        _attach_messages(req_missing)
        resp_missing = signup_view(req_missing)
        assert resp_missing.status_code == 200

        Organization.objects.create(name="Org")
        from django.contrib.auth import get_user_model

        User = get_user_model()
        User.objects.create_user(
            email="dup@example.com",
            password="testpass123",
            first_name="",
            last_name="",
            role="owner",
            organization=Organization.objects.create(name="Dup Org"),
        )

        req_dup = rf.post(
            "/signup/",
            data={
                "email": "dup@example.com",
                "password": "testpass123",
                "organization_name": "X",
            },
        )
        req_dup.user = type("Anon", (), {"is_authenticated": False})()
        _attach_messages(req_dup)
        resp_dup = signup_view(req_dup)
        assert resp_dup.status_code == 200
