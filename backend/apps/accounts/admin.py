from django.contrib import admin

from apps.accounts.models import Permission, Role, RolePermission, User, UserRole


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    ordering = ("email",)
    list_display = ("email", "facility", "is_active", "mfa_enabled", "is_staff")
    list_filter = ("facility", "is_active", "mfa_enabled", "is_staff")
    search_fields = ("email", "phone", "first_name", "last_name")
    readonly_fields = ("last_login_at", "mfa_secret_encrypted")
    exclude = ("password",)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("code", "description")
    search_fields = ("code",)


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ("role", "permission")
    list_filter = ("role",)


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "facility", "department")
    list_filter = ("role", "facility")
