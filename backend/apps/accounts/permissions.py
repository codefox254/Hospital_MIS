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
    Views set one of, in priority order:
      - `permission_codes_by_action = {"list": "...", "create": "...",
        "deactivate": "..."}` — keyed by `view.action`, the precise
        mechanism for a ViewSet with custom `@action`s that share an HTTP
        method with a standard one (e.g. a custom POST action needs a
        different code than `create`'s POST).
      - `permission_codes_by_method = {"GET": "...", "POST": "..."}` — for
        plain APIViews with no `.action` attribute.
      - `permission_code = "module.resource.action"` — same code for every
        request this view handles.

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
        if code is None:
            # The view genuinely doesn't implement this HTTP method (e.g.
            # DELETE deliberately excluded from an audited ViewSet, TRD
            # §8.4). DRF checks permissions before it checks whether the
            # method is even handled, so denying here would surface as a
            # misleading 403 — deferring lets dispatch()'s own
            # http_method_names check produce the correct 405 instead.
            return True

        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False

        facility = getattr(request, "permission_facility", None)
        department = getattr(request, "permission_department", None)
        return user_has_permission(user, code, facility=facility, department=department)

    @staticmethod
    def _resolve_code(request, view):
        by_action = getattr(view, "permission_codes_by_action", None)
        action = getattr(view, "action", None)
        if by_action and action in by_action:
            return by_action[action]

        by_method = getattr(view, "permission_codes_by_method", None)
        if by_method and request.method in by_method:
            return by_method[request.method]

        code = getattr(view, "permission_code", None)
        if code:
            return code

        allowed_methods = getattr(view, "http_method_names", ())
        if request.method.lower() not in allowed_methods:
            return None

        raise ImproperlyConfigured(
            f"{view.__class__.__name__} uses HasModulePermission but declares no "
            "`permission_codes_by_action` / `permission_codes_by_method` / `permission_code` "
            f"for action={action!r} method={request.method!r}."
        )
