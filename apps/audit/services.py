from apps.audit.models import ActivityEntry, AuditLog


class AuditService:
    @staticmethod
    def log(
        *,
        actor,
        organization,
        action,
        object_type,
        object_id,
        object_repr="",
        metadata=None,
        ip_address=None,
        user_agent="",
    ):
        return AuditLog.objects.create(
            actor=actor,
            organization=organization,
            action=action,
            object_type=object_type,
            object_id=str(object_id),
            object_repr=object_repr,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    def get_logs_for_organization(organization, filters=None):
        qs = AuditLog.objects.filter(organization=organization)
        if filters:
            if "action" in filters:
                qs = qs.filter(action=filters["action"])
            if "object_type" in filters:
                qs = qs.filter(object_type=filters["object_type"])
            if "actor_id" in filters:
                qs = qs.filter(actor_id=filters["actor_id"])
            if "from_date" in filters:
                qs = qs.filter(timestamp__gte=filters["from_date"])
            if "to_date" in filters:
                qs = qs.filter(timestamp__lte=filters["to_date"])
        return qs

    @staticmethod
    def get_logs_for_object(object_type, object_id):
        return AuditLog.objects.filter(
            object_type=object_type,
            object_id=str(object_id),
        )


class ActivityFeedService:
    """Append-only activity feed. Entries are never updated or deleted."""

    @staticmethod
    def record(
        *,
        organization,
        actor,
        activity_type: str,
        description: str,
        task=None,
        metadata=None,
    ) -> ActivityEntry:
        return ActivityEntry.objects.create(
            organization=organization,
            actor=actor,
            activity_type=activity_type,
            task=task,
            description=description,
            metadata=metadata or {},
        )
