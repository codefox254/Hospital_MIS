import pytest
from django.core.management import call_command

from apps.accounts.constants import PRIVILEGED_ROLE_NAMES
from apps.accounts.management.commands.seed_rbac import (
    _FACILITY_ADMIN_EXCLUDED_CODES,
    PERMISSION_CATALOGUE,
)
from apps.accounts.models import Permission, Role

pytestmark = pytest.mark.django_db


class TestSeedRbac:
    def test_seeds_every_cataloged_permission(self):
        call_command("seed_rbac")

        assert Permission.objects.count() == len(PERMISSION_CATALOGUE)
        for code in PERMISSION_CATALOGUE:
            assert Permission.objects.filter(code=code).exists()

    def test_administrator_role_holds_every_permission_except_platform_tenancy(self):
        """Administrator is the per-facility ("Facility Admin") tier — it
        must hold everything operational but none of core.facility.*,
        which is Super Admin-only (managing tenants, not one tenant's
        clinical/billing data)."""
        call_command("seed_rbac")

        admin_role = Role.objects.get(name="Administrator")
        admin_codes = set(admin_role.permissions.values_list("code", flat=True))
        assert admin_codes == set(PERMISSION_CATALOGUE) - _FACILITY_ADMIN_EXCLUDED_CODES
        assert admin_codes.isdisjoint(_FACILITY_ADMIN_EXCLUDED_CODES)

    def test_super_admin_role_holds_only_platform_tenancy_codes(self):
        """The inverse of the Administrator check — Super Admin must never
        pick up a facility-scoped clinical/billing/etc. permission, since
        the SaaS model deliberately keeps it out of tenant data."""
        call_command("seed_rbac")

        super_admin_role = Role.objects.get(name="Super Admin")
        super_admin_codes = set(super_admin_role.permissions.values_list("code", flat=True))
        assert _FACILITY_ADMIN_EXCLUDED_CODES <= super_admin_codes
        clinical_codes = {
            c for c in PERMISSION_CATALOGUE if c.split(".")[0] not in ("core", "accounts")
        }
        assert super_admin_codes.isdisjoint(clinical_codes)

    def test_privileged_role_names_all_get_seeded(self):
        """Every name accounts.constants.PRIVILEGED_ROLE_NAMES enforces MFA
        for must correspond to a real seeded Role, or the MFA-required check
        silently never matches anyone holding that title."""
        call_command("seed_rbac")

        seeded_names = set(Role.objects.values_list("name", flat=True))
        assert PRIVILEGED_ROLE_NAMES <= seeded_names

    def test_running_twice_is_idempotent(self):
        call_command("seed_rbac")
        call_command("seed_rbac")

        assert Permission.objects.count() == len(PERMISSION_CATALOGUE)
        admin_role = Role.objects.get(name="Administrator")
        assert admin_role.permissions.count() == len(PERMISSION_CATALOGUE) - len(
            _FACILITY_ADMIN_EXCLUDED_CODES
        )
