from apps.audit.models import AuditLog


class AuditService:
    @staticmethod
    def log(*, actor, tenant, action, object_type, object_id,
            object_repr="", metadata=None, ip_address=None, user_agent=""):
        return AuditLog.objects.create(
            actor=actor,
            tenant=tenant,
            action=action,
            object_type=object_type,
            object_id=str(object_id),
            object_repr=object_repr,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    def get_logs_for_tenant(tenant, filters=None):
        qs = AuditLog.objects.filter(tenant=tenant)
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
