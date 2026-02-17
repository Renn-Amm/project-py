from django.db.models import Count
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone

from apps.analytics.models import EvaluationEvent


class AnalyticsService:
    @staticmethod
    def record_evaluation(flag, user_identifier, variant, environment_name):
        return EvaluationEvent.objects.create(
            flag=flag,
            flag_key=flag.key,
            user_identifier=user_identifier,
            evaluated_variant=variant,
            environment_name=environment_name,
        )

    @staticmethod
    def get_flag_evaluation_summary(flag, days=7):
        since = timezone.now() - timezone.timedelta(days=days)
        events = EvaluationEvent.objects.filter(
            flag=flag,
            timestamp__gte=since,
        )

        total = events.count()
        unique_users = events.values("user_identifier").distinct().count()

        variant_distribution = (
            events.values("evaluated_variant")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        daily_counts = (
            events.annotate(date=TruncDate("timestamp"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        return {
            "total_evaluations": total,
            "unique_users": unique_users,
            "variant_distribution": list(variant_distribution),
            "daily_counts": list(daily_counts),
            "period_days": days,
        }

    @staticmethod
    def get_tenant_analytics_summary(tenant, days=7):
        since = timezone.now() - timezone.timedelta(days=days)
        events = EvaluationEvent.objects.filter(
            flag__environment__tenant=tenant,
            timestamp__gte=since,
        )

        total = events.count()
        unique_users = events.values("user_identifier").distinct().count()
        unique_flags = events.values("flag_key").distinct().count()

        hourly_counts = (
            events.annotate(hour=TruncHour("timestamp"))
            .values("hour")
            .annotate(count=Count("id"))
            .order_by("hour")
        )

        top_flags = (
            events.values("flag_key")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        return {
            "total_evaluations": total,
            "unique_users": unique_users,
            "unique_flags": unique_flags,
            "hourly_counts": list(hourly_counts),
            "top_flags": list(top_flags),
            "period_days": days,
        }

    @staticmethod
    def get_experiment_results(flag, days=30):
        since = timezone.now() - timezone.timedelta(days=days)
        events = EvaluationEvent.objects.filter(
            flag=flag,
            timestamp__gte=since,
        )

        variant_stats = (
            events.values("evaluated_variant")
            .annotate(
                count=Count("id"),
                unique_users=Count("user_identifier", distinct=True),
            )
            .order_by("-count")
        )

        return {
            "flag_key": flag.key,
            "total_evaluations": events.count(),
            "variant_stats": list(variant_stats),
            "period_days": days,
        }
