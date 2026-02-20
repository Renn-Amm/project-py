from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.tasks.models import TaskStatus
from apps.time_tracking.models import TimeEntry


class TimeEntryService:
    IMMUTABLE_AFTER = timedelta(hours=24)

    @staticmethod
    def _assert_task_allows_logging(*, task) -> None:
        if task.status == TaskStatus.ARCHIVED:
            raise ValidationError("Cannot log time on an archived task.")

    @staticmethod
    @transaction.atomic
    def create_time_entry(*, user, task, hours: Decimal, date) -> TimeEntry:
        if hours < 0:
            raise ValidationError("Cannot log negative time.")

        if user.organization_id != task.organization_id:
            raise ValidationError("Cross-organization access is not allowed.")

        TimeEntryService._assert_task_allows_logging(task=task)

        entry = TimeEntry.objects.create(user=user, task=task, hours=hours, date=date)
        TimeEntryService.recalculate_task_total(task)
        return entry

    @staticmethod
    @transaction.atomic
    def recalculate_task_total(task) -> None:
        total = (
            TimeEntry.objects
            .filter(task=task)
            .aggregate(total=Sum("hours"))
            .get("total")
            or Decimal("0")
        )
        task.total_logged_time_hours = total
        task.save(update_fields=["total_logged_time_hours", "updated_at"])

    @staticmethod
    def assert_entry_mutable(entry: TimeEntry) -> None:
        cutoff = entry.created_at + TimeEntryService.IMMUTABLE_AFTER
        if timezone.now() > cutoff:
            raise ValidationError("Time entries are immutable after 24 hours.")
