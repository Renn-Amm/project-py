import json
import logging

from django.utils.deprecation import MiddlewareMixin

from apps.audit.services import AuditService

logger = logging.getLogger(__name__)

AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

AUDIT_PATH_PREFIXES = [
    "/api/flags/",
    "/api/targeting/",
    "/api/policies/",
    "/api/tenants/",
]


class AuditMiddleware(MiddlewareMixin):
    """Automatically logs mutating API requests to the audit log."""

    def process_response(self, request, response):
        if request.method not in AUDIT_METHODS:
            return response

        if not any(request.path.startswith(p) for p in AUDIT_PATH_PREFIXES):
            return response

        if not hasattr(request, "user") or not request.user.is_authenticated:
            return response

        if response.status_code >= 400:
            return response

        try:
            action = self._determine_action(request)
            object_type, object_id = self._extract_object_info(request, response)
            tenant = getattr(request, "tenant", None) or getattr(request.user, "tenant", None)

            if tenant and object_type:
                ip = self._get_client_ip(request)
                AuditService.log(
                    actor=request.user,
                    tenant=tenant,
                    action=action,
                    object_type=object_type,
                    object_id=object_id or "unknown",
                    metadata=self._safe_get_body(request),
                    ip_address=ip,
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                )
        except Exception:
            logger.exception("Failed to create audit log entry")

        return response

    def _determine_action(self, request):
        path = request.path.lower()
        if "archive" in path:
            return "archive"
        if "toggle" in path:
            return "toggle"
        if "approve" in path:
            return "approve"
        if "reject" in path:
            return "reject"
        if "kill-switch" in path:
            return "kill_switch"

        method_map = {
            "POST": "create",
            "PUT": "update",
            "PATCH": "update",
            "DELETE": "delete",
        }
        return method_map.get(request.method, "update")

    def _extract_object_info(self, request, response):
        path_parts = [p for p in request.path.split("/") if p]
        object_type = "unknown"
        object_id = "unknown"

        if "flags" in path_parts:
            object_type = "FeatureFlag"
        elif "targeting" in path_parts or "rules" in path_parts:
            object_type = "TargetingRule"
        elif "policies" in path_parts:
            object_type = "Policy"
        elif "approvals" in path_parts:
            object_type = "ApprovalRequest"
        elif "tenants" in path_parts:
            object_type = "Tenant"

        for part in path_parts:
            if part.isdigit():
                object_id = part
                break

        if object_id == "unknown" and response.status_code == 201:
            try:
                data = json.loads(response.content)
                object_id = str(data.get("id", "unknown"))
            except (json.JSONDecodeError, AttributeError):
                pass

        return object_type, object_id

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    def _safe_get_body(self, request):
        try:
            if request.body:
                data = json.loads(request.body)
                sensitive_keys = {"password", "token", "secret"}
                return {
                    k: "***" if k in sensitive_keys else v
                    for k, v in data.items()
                }
        except (json.JSONDecodeError, AttributeError):
            pass
        return {}
