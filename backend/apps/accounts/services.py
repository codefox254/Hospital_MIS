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

from apps.accounts.models import BreakGlassGrant, User, UserRole


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


def create_user_with_role(
    *, email, password, first_name, last_name, facility, role=None, phone="", actor=None
):
    """Creates a staff user and, if a role is given, grants it immediately
    — used by the admin-onboarding flow (Super Admin creating a facility's
    first admin, or a Facility Admin adding their own staff) so a new
    account isn't left holding zero permissions until someone remembers a
    second step.

    A grant of the "Super Admin" role is always unscoped (facility=None)
    regardless of the new user's home facility, matching the SaaS model:
    Super Admin authority is platform-wide by definition, not tied to any
    one tenant. Every other role's grant is scoped to `facility`.
    """
    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        phone=phone or None,
        facility=facility,
    )
    if role is not None:
        UserRole.objects.create(
            user=user,
            role=role,
            facility=None if role.name == "Super Admin" else facility,
            department=None,
        )
    return user
