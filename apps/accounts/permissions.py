from rest_framework.permissions import BasePermission

from apps.accounts.models import UserRole, ROLE_HIERARCHY


class IsOwner(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.OWNER


class IsAdminOrAbove(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role_level >= ROLE_HIERARCHY[UserRole.ADMIN]
        )


class IsDeveloperOrAbove(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role_level >= ROLE_HIERARCHY[UserRole.DEVELOPER]
        )


class IsViewer(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated


class RoleBasedPermission(BasePermission):
    """Dynamic role-based permission that checks minimum role level."""

    role_map = {
        "GET": UserRole.VIEWER,
        "HEAD": UserRole.VIEWER,
        "OPTIONS": UserRole.VIEWER,
        "POST": UserRole.DEVELOPER,
        "PUT": UserRole.DEVELOPER,
        "PATCH": UserRole.DEVELOPER,
        "DELETE": UserRole.ADMIN,
    }

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        minimum_role = self.role_map.get(request.method, UserRole.OWNER)
        return request.user.has_role_level(minimum_role)
