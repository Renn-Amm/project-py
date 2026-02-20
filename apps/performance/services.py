from __future__ import annotations

from decimal import Decimal

from apps.tasks.models import PRIORITY_WEIGHTS, Task, TaskStatus, TaskStatusChange


class PerformanceScoreService:
    """Calculates per-user performance metrics with weighted scoring."""

    # Weights for the scoring formula
    COMPLETION_WEIGHT = Decimal("10")
    OVERDUE_PENALTY = Decimal("15")
    REJECTION_PENALTY = Decimal("10")
    ACCURACY_BONUS = Decimal("5")

    @staticmethod
    def calculate(user, organization) -> dict:
        """Calculate performance metrics for a user within their organization."""
        tasks = Task.objects.filter(
            project__organization=organization,
            assignee=user,
        )

        total_assigned = tasks.count()
        if total_assigned == 0:
            return {
                "tasks_completed": 0,
                "total_assigned": 0,
                "overdue_rate": Decimal("0"),
                "review_rejection_rate": Decimal("0"),
                "avg_completion_time_hours": Decimal("0"),
                "time_accuracy_ratio": Decimal("0"),
                "weighted_score": Decimal("0"),
            }

        # Tasks completed
        completed = tasks.filter(status=TaskStatus.COMPLETED).count()

        # Overdue rate
        overdue_count = tasks.filter(is_overdue=True).count()
        overdue_rate = Decimal(str(overdue_count)) / Decimal(str(total_assigned))

        # Review rejection rate
        total_reviews = TaskStatusChange.objects.filter(
            task__in=tasks,
            to_status=TaskStatus.IN_REVIEW,
        ).count()
        rejections = TaskStatusChange.objects.filter(
            task__in=tasks,
            from_status=TaskStatus.IN_REVIEW,
            to_status=TaskStatus.BACKLOG,
        ).count()
        rejection_rate = (
            Decimal(str(rejections)) / Decimal(str(total_reviews))
            if total_reviews > 0
            else Decimal("0")
        )

        # Average completion time (hours)
        completed_tasks = tasks.filter(
            status=TaskStatus.COMPLETED,
            completed_at__isnull=False,
        )
        avg_completion_hours = Decimal("0")
        if completed_tasks.exists():
            total_hours = Decimal("0")
            count = 0
            for t in completed_tasks:
                if t.completed_at and t.created_at:
                    delta = t.completed_at - t.created_at
                    total_hours += Decimal(str(delta.total_seconds())) / Decimal("3600")
                    count += 1
            if count > 0:
                avg_completion_hours = total_hours / Decimal(str(count))

        # Time accuracy ratio (logged/estimated)
        estimated_tasks = tasks.filter(
            estimated_time_hours__isnull=False,
            estimated_time_hours__gt=0,
        )
        time_accuracy = Decimal("0")
        if estimated_tasks.exists():
            total_ratio = Decimal("0")
            count = 0
            for t in estimated_tasks:
                if t.total_logged_time_hours and t.estimated_time_hours:
                    ratio = t.total_logged_time_hours / t.estimated_time_hours
                    # Cap ratio between 0 and 2 for scoring
                    ratio = min(ratio, Decimal("2"))
                    total_ratio += ratio
                    count += 1
            if count > 0:
                time_accuracy = total_ratio / Decimal(str(count))

        # Weighted priority score for completed tasks
        priority_score = Decimal("0")
        for t in completed_tasks:
            weight = PRIORITY_WEIGHTS.get(t.priority, 1)
            priority_score += Decimal(str(weight))

        # Final weighted score
        score = (
            PerformanceScoreService.COMPLETION_WEIGHT * priority_score
            - PerformanceScoreService.OVERDUE_PENALTY * overdue_rate * Decimal(str(total_assigned))
            - PerformanceScoreService.REJECTION_PENALTY * rejection_rate * Decimal(str(total_reviews or 1))
            + PerformanceScoreService.ACCURACY_BONUS * time_accuracy * Decimal(str(completed))
        )

        return {
            "tasks_completed": completed,
            "total_assigned": total_assigned,
            "overdue_rate": round(overdue_rate, 4),
            "review_rejection_rate": round(rejection_rate, 4),
            "avg_completion_time_hours": round(avg_completion_hours, 2),
            "time_accuracy_ratio": round(time_accuracy, 4),
            "weighted_score": round(score, 2),
        }
