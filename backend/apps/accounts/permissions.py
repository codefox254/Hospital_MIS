"""
HasModulePermission — the single DRF permission class every module's views
use to enforce the module.resource.action engine (TRD §2, §4.3). A view
declares what it requires; this class is the only thing that ever resolves
"does this user actually have that" — no module implements its own check.
"""

from django.core.exceptions import ImproperlyConfigured
from rest_framework.permissions import BasePermission

from apps.accounts.services import user_has_permission


class HasModulePermission(BasePermission):
    """
    Views set one of:
      - `permission_code = "module.resource.action"` (same code for every
        method), or
      - `permission_codes_by_method = {"GET": "...", "POST": "..."}` when
        different HTTP methods need different permissions.

    The facility a request is checked against defaults to the requesting
    user's home facility; a view can override this by setting
    `request.permission_facility` (e.g. from a URL-scoped resource) before
    this permission class runs — DRF permission classes run after the view's
    `initial()`, so `initialize_request`/dispatch-time attributes are
    visible here.
    """

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        code = self._resolve_code(request, view)

        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False

        facility = getattr(request, "permission_facility", None)
        department = getattr(request, "permission_department", None)
        return user_has_permission(user, code, facility=facility, department=department)

    @staticmethod
    def _resolve_code(request, view):
        code = getattr(view, "permission_code", None)
        if code:
            return code

        by_method = getattr(view, "permission_codes_by_method", None)
        if by_method and request.method in by_method:
            return by_method[request.method]

        raise ImproperlyConfigured(
            f"{view.__class__.__name__} uses HasModulePermission but declares no "
            "`permission_code` / `permission_codes_by_method`."
        )
