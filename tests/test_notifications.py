import pytest

from apps.notifications.models import Notification, NotificationType
from apps.notifications.services import NotificationService
from apps.tasks.models import Task


@pytest.mark.django_db
class TestNotificationCreation:
    def test_notify_task_assigned(self, project_with_team, developer_user, owner_user):
        task = Task.objects.create(
            project=project_with_team,
            title="Assigned Task",
            assignee=developer_user,
            created_by=owner_user,
        )
        task.project = project_with_team  # ensure relation loaded
        notif = NotificationService.notify_task_assigned(task=task)
        assert notif is not None
        assert notif.recipient_id == developer_user.id
        assert notif.notification_type == NotificationType.TASK_ASSIGNED
        assert notif.organization_id == developer_user.organization_id

    def test_notify_moved_to_review(self, project_with_team, reviewer_user, owner_user):
        task = Task.objects.create(
            project=project_with_team,
            title="Review Task",
            reviewer=reviewer_user,
            created_by=owner_user,
        )
        notif = NotificationService.notify_moved_to_review(task=task)
        assert notif is not None
        assert notif.recipient_id == reviewer_user.id
        assert notif.notification_type == NotificationType.MOVED_TO_REVIEW

    def test_notify_overdue(self, project_with_team, developer_user, owner_user):
        task = Task.objects.create(
            project=project_with_team,
            title="Overdue Task",
            assignee=developer_user,
            created_by=owner_user,
        )
        notif = NotificationService.notify_overdue(task=task)
        assert notif is not None
        assert notif.notification_type == NotificationType.OVERDUE_DETECTED

    def test_no_notification_without_assignee(self, project_with_team, owner_user):
        task = Task.objects.create(
            project=project_with_team,
            title="Unassigned",
            created_by=owner_user,
        )
        assert NotificationService.notify_task_assigned(task=task) is None
        assert NotificationService.notify_overdue(task=task) is None


@pytest.mark.django_db
class TestNotificationTenantIsolation:
    def test_notifications_scoped_to_org(self, project_with_team, developer_user, owner_user, organization, organization_b):
        task = Task.objects.create(
            project=project_with_team,
            title="Org Task",
            assignee=developer_user,
            created_by=owner_user,
        )
        NotificationService.notify_task_assigned(task=task)

        # Same org sees it
        assert Notification.objects.filter(organization=organization).count() == 1
        # Other org does not
        assert Notification.objects.filter(organization=organization_b).count() == 0

    def test_mark_read_own_org_only(self, project_with_team, developer_user, owner_user, other_org_owner_user):
        task = Task.objects.create(
            project=project_with_team,
            title="Notify",
            assignee=developer_user,
            created_by=owner_user,
        )
        notif = NotificationService.notify_task_assigned(task=task)

        # Other org user cannot mark as read
        assert NotificationService.mark_as_read(notif.id, other_org_owner_user) is False
        # Own user can
        assert NotificationService.mark_as_read(notif.id, developer_user) is True


@pytest.mark.django_db
class TestNotificationAPI:
    def test_list_notifications(self, developer_client, project_with_team, developer_user, owner_user):
        task = Task.objects.create(
            project=project_with_team,
            title="API Task",
            assignee=developer_user,
            created_by=owner_user,
        )
        NotificationService.notify_task_assigned(task=task)
        resp = developer_client.get("/api/notifications/")
        assert resp.status_code == 200
        assert len(resp.data["results"]) == 1

    def test_mark_read(self, developer_client, project_with_team, developer_user, owner_user):
        task = Task.objects.create(
            project=project_with_team,
            title="Read Task",
            assignee=developer_user,
            created_by=owner_user,
        )
        notif = NotificationService.notify_task_assigned(task=task)
        resp = developer_client.post(f"/api/notifications/{notif.id}/read/")
        assert resp.status_code == 200
        notif.refresh_from_db()
        assert notif.is_read is True
