"""
Custom DRF permission classes (Layer 2 of the security model).

The frontend has its own route guards (Layer 1), but a malicious user can
bypass the UI and call the API directly. These classes block such requests
server-side by inspecting the authenticated user's role.
"""
from rest_framework import permissions


class IsAgencyStaff(permissions.BasePermission):
    """Allow only internal staff (employees + admins) to access /api/v1/crm/*."""

    def has_permission(self, request, view):
        # Must be authenticated AND have an internal role
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ('employee', 'admin')
        )


class IsPortalClient(permissions.BasePermission):
    """Allow only external clients to access /api/v1/portal/*."""

    def has_permission(self, request, view):
        # Clients are the only role allowed into the portal gateway
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'client'
        )


class IsAdmin(permissions.BasePermission):
    """Allow only admins (full read/write across the CRM)."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'admin'
        )
