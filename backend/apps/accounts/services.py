"""
Permission resolution — the one place that turns a user's UserRole grants
(plus any active break-glass grant) into an effective set of
module.resource.action codes for a given facility/department (BRD §8,
TRD §4.3). Every permission check in the system goes through this, never a
bespoke per-view query, so the scoping rule only has to be right once.

Scoping rule: a UserRole grant applies if its facility is unset (global) or
matches the requested facility, and — independently — its department is
unset (facility-wide) or matches the requested department. `facility`
defaults to the user's home facility when not given explicitly.
"""

from apps.accounts.models import BreakGlassGrant, UserRole


def get_effective_permission_codes(user, *, facility=None, department=None):
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return set()

    if facility is None:
        facility = user.facility

    codes = set()

    grants = (
        UserRole.objects.filter(user=user)
        .select_related("role")
        .prefetch_related("role__permissions")
    )
    for grant in grants:
        facility_ok = grant.facility_id is None or grant.facility_id == facility.id
        department_ok = grant.department_id is None or (
            department is not None and grant.department_id == department.id
        )
        if facility_ok and department_ok:
            codes.update(grant.role.permissions.values_list("code", flat=True))

    break_glass_grants = BreakGlassGrant.objects.filter(
        user=user, facility=facility, revoked_at__isnull=True
    ).select_related("permission")
    for grant in break_glass_grants:
        if grant.is_active():
            codes.add(grant.permission.code)

    return codes


def user_has_permission(user, code, *, facility=None, department=None):
    return code in get_effective_permission_codes(user, facility=facility, department=department)
