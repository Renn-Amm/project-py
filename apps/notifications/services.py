from __future__ import annotations

from apps.notifications.models import Notification, NotificationType


class NotificationService:
    @staticmethod
    def notify(*, recipient, organization, notification_type: str, title: str, message: str = "", related_task=None) -> Notification:
        """Create a notification scoped to the recipient's organization."""
        if recipient.organization_id != organization.id:
            return None  # type: ignore[return-value]
        return Notification.objects.create(
            recipient=recipient,
            organization=organization,
            notification_type=notification_type,
            title=title,
            message=message,
            related_task=related_task,
        )

    @staticmethod
    def notify_task_assigned(*, task) -> Notification | None:
        if not task.assignee:
            return None
        return NotificationService.notify(
            recipient=task.assignee,
            organization=task.project.organization,
            notification_type=NotificationType.TASK_ASSIGNED,
            title=f"You were assigned to: {task.title}",
            message=f"You have been assigned to task '{task.title}' in project '{task.project.name}'.",
            related_task=task,
        )

    @staticmethod
    def notify_moved_to_review(*, task) -> Notification | None:
        if not task.reviewer:
            return None
        return NotificationService.notify(
            recipient=task.reviewer,
            organization=task.project.organization,
            notification_type=NotificationType.MOVED_TO_REVIEW,
            title=f"Task ready for review: {task.title}",
            message=f"Task '{task.title}' has been moved to review and awaits your approval.",
            related_task=task,
        )

    @staticmethod
    def notify_review_rejected(*, task, actor) -> Notification | None:
        if not task.assignee:
            return None
        return NotificationService.notify(
            recipient=task.assignee,
            organization=task.project.organization,
            notification_type=NotificationType.REVIEW_REJECTED,
            title=f"Review rejected: {task.title}",
            message=f"Your task '{task.title}' was rejected by {actor.email}.",
            related_task=task,
        )

    @staticmethod
    def notify_overdue(*, task) -> Notification | None:
        if not task.assignee:
            return None
        return NotificationService.notify(
            recipient=task.assignee,
            organization=task.project.organization,
            notification_type=NotificationType.OVERDUE_DETECTED,
            title=f"Task overdue: {task.title}",
            message=f"Task '{task.title}' has passed its deadline and is now overdue.",
            related_task=task,
        )

    @staticmethod
    def mark_as_read(notification_id: int, user) -> bool:
        updated = Notification.objects.filter(
            pk=notification_id,
            recipient=user,
            organization=user.organization,
        ).update(is_read=True)
        return updated > 0
