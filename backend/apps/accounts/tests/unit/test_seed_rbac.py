import pytest
from django.core.management import call_command

from apps.accounts.constants import PRIVILEGED_ROLE_NAMES
from apps.accounts.management.commands.seed_rbac import PERMISSION_CATALOGUE
from apps.accounts.models import Permission, Role

pytestmark = pytest.mark.django_db


class TestSeedRbac:
    def test_seeds_every_cataloged_permission(self):
        call_command("seed_rbac")

        assert Permission.objects.count() == len(PERMISSION_CATALOGUE)
        for code in PERMISSION_CATALOGUE:
            assert Permission.objects.filter(code=code).exists()

    def test_administrator_role_holds_every_permission(self):
        call_command("seed_rbac")

        admin_role = Role.objects.get(name="Administrator")
        assert admin_role.permissions.count() == len(PERMISSION_CATALOGUE)

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
        assert admin_role.permissions.count() == len(PERMISSION_CATALOGUE)
