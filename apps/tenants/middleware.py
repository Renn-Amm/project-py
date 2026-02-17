import logging

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class TenantMiddleware(MiddlewareMixin):
    """Injects tenant context into every request based on authenticated user.

    Security: Rejects authenticated API requests where user has no tenant,
    preventing orphaned users from accessing any tenant data.
    """

    EXEMPT_PATHS = [
        "/api/auth/",
        "/admin/",
        "/api/evaluate/",
        "/api/health/",
    ]

    TENANT_REQUIRED_PATHS = [
        "/api/flags/",
        "/api/targeting/",
        "/api/policies/",
        "/api/audit/",
        "/api/analytics/",
        "/api/tenants/",
    ]

    def process_request(self, request):
        request.tenant = None

        if any(request.path.startswith(p) for p in self.EXEMPT_PATHS):
            return None

        if hasattr(request, "user") and request.user.is_authenticated:
            tenant = getattr(request.user, "tenant", None)
            if tenant is None and any(
                request.path.startswith(p) for p in self.TENANT_REQUIRED_PATHS
            ):
                logger.warning(
                    "Tenant-required request from user without tenant: %s %s",
                    request.user.email,
                    request.path,
                )
                return JsonResponse(
                    {"error": "User is not associated with any tenant."},
                    status=403,
                )
            if tenant and not tenant.is_active:
                return JsonResponse(
                    {"error": "Tenant account is deactivated."},
                    status=403,
                )
            request.tenant = tenant

        return None
