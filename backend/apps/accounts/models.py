"""
Identity & RBAC models (BRD §8 permission engine, TRD §4.3; Data Dictionary
§2). Role/Permission/UserRole implement the module.resource.action model —
every module's endpoints are gated through this engine, never a bespoke
per-module check (TRD §2).

Deviation from the Data Dictionary worth flagging: the User table there
lists no display-name field, but the Solution Spec's reference UI (the top
bar's "Dr. John Mwangi / Administrator" badge, BRD-cited journeys) requires
one — `first_name`/`last_name` are added here as a load-bearing addition,
not scope creep. The Data Dictionary's `password_hash` column maps onto
Django's built-in `AbstractBaseUser.password` field, which already stores a
hash under `PASSWORD_HASHERS` (Argon2 first, TRD §8.1) — it is not
duplicated as a second field.
"""

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone

from apps.core.models import Department, Facility, TimeStampedModel, UUIDModel


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, UUIDModel, TimeStampedModel):
    """
    Deliberately does not inherit django.contrib.auth's PermissionsMixin:
    authorization is 100% the custom Role/Permission/UserRole engine below,
    never contrib.auth's Group/Permission tables (TRD §2, §4.3). is_staff/
    is_superuser exist only to gate the Django admin site, not API access.
    """

    facility = models.ForeignKey(
        Facility,
        on_delete=models.PROTECT,
        related_name="users",
        help_text="Home facility; multi-facility access via UserRole scoping.",
    )
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    mfa_enabled = models.BooleanField(default=False)
    mfa_secret_encrypted = models.CharField(max_length=255, blank=True, editable=False)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    last_login_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["facility_id"]

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

    def has_perm(self, perm, obj=None):
        # Django-admin-only bypass; the API never consults this — see
        # apps.accounts.permissions.HasModulePermission (added in the
        # auth/permission-engine milestone).
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser


class Role(UUIDModel, TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(
        "accounts.Permission", through="accounts.RolePermission", related_name="roles"
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Permission(UUIDModel, TimeStampedModel):
    code = models.CharField(
        max_length=100,
        unique=True,
        help_text="module.resource.action, e.g. lab.result.verify",
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.code


class RolePermission(UUIDModel, TimeStampedModel):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(
        Permission, on_delete=models.CASCADE, related_name="permission_roles"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["role", "permission"], name="unique_role_permission")
        ]

    def __str__(self):
        return f"{self.role} → {self.permission}"


class UserRole(UUIDModel, TimeStampedModel):
    """User ↔ Role ↔ scope grant (BRD §8.2). A null facility/department means
    the role grant is unscoped (applies everywhere the user has access)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_roles"
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_users")
    facility = models.ForeignKey(
        Facility, null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    department = models.ForeignKey(
        Department, null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )

    class Meta:
        constraints = [
            # nulls_distinct=False (Django 5.1+/Postgres 15+): an unscoped
            # grant (facility/department NULL) must still be deduplicated —
            # standard SQL NULL-distinct semantics would otherwise silently
            # allow the same user/role/NULL/NULL grant to be inserted twice.
            models.UniqueConstraint(
                fields=["user", "role", "facility", "department"],
                name="unique_user_role_scope",
                nulls_distinct=False,
            )
        ]

    def __str__(self):
        return f"{self.user} — {self.role}"


class BreakGlassGrant(UUIDModel, TimeStampedModel):
    """
    Emergency access (TRD §4.3, BRD §7.3): a single permission, at a single
    facility, for a mandatory reason, that always expires — never a standing
    grant. Distinct from UserRole so it can never be mistaken for routine
    access in a permission review. Self-documenting as an append-only record
    (who granted it, to whom, why, when it expires); the audit milestone
    additionally mirrors every grant/use into the central audit trail.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="break_glass_grants"
    )
    permission = models.ForeignKey(
        Permission, on_delete=models.PROTECT, related_name="break_glass_grants"
    )
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name="+")
    reason = models.TextField()
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="break_glass_grants_issued",
    )
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(reason=""),
                name="break_glass_reason_required",
            )
        ]

    def __str__(self):
        return f"{self.user} — {self.permission} @ {self.facility} (expires {self.expires_at})"

    def is_active(self):
        return self.revoked_at is None and self.expires_at > timezone.now()
