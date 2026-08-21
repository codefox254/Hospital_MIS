from django.contrib import admin

from apps.accounts.models import Permission, Role, RolePermission, User, UserRole


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 1
    autocomplete_fields = ["permission"]


class UserRoleInline(admin.TabularInline):
    model = UserRole
    fk_name = "user"
    extra = 1
    autocomplete_fields = ["role", "facility", "department"]


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    ordering = ("email",)
    list_display = ("email", "facility", "is_active", "mfa_enabled", "is_staff")
    list_filter = ("facility", "is_active", "mfa_enabled", "is_staff")
    search_fields = ("email", "phone", "first_name", "last_name")
    readonly_fields = ("last_login_at", "mfa_secret_encrypted")
    exclude = ("password",)
    inlines = [UserRoleInline]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "permission_count")
    search_fields = ("name",)
    inlines = [RolePermissionInline]

    @admin.display(description="Permissions")
    def permission_count(self, obj):
        return obj.permissions.count()


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("code", "description")
    search_fields = ("code", "description")


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ("role", "permission")
    list_filter = ("role",)
    autocomplete_fields = ["role", "permission"]


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "facility", "department")
    list_filter = ("role", "facility")
    autocomplete_fields = ["user", "role", "facility", "department"]
