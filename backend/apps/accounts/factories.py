"""Shared factory_boy factories for accounts models — synthetic data only."""

import factory

from apps.accounts.models import Permission, Role, RolePermission, User, UserRole
from apps.core.factories import FacilityFactory


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    facility = factory.SubFactory(FacilityFactory)
    email = factory.Sequence(lambda n: f"user{n}@fdo-hospital.test")
    first_name = "Test"
    last_name = "User"
    is_active = True

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or "Str0ngP@ssword!23")
        if create:
            self.save()


class RoleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Role

    name = factory.Sequence(lambda n: f"Test Role {n}")


class PermissionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Permission

    code = factory.Sequence(lambda n: f"testmodule.resource.action{n}")


class RolePermissionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RolePermission

    role = factory.SubFactory(RoleFactory)
    permission = factory.SubFactory(PermissionFactory)


class UserRoleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserRole

    user = factory.SubFactory(UserFactory)
    role = factory.SubFactory(RoleFactory)
