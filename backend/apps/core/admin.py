from django.contrib import admin
from django.contrib.auth.models import Group

from apps.core.models import Department, Facility

admin.site.site_header = "FDO Hospital MIS Administration"
admin.site.site_title = "FDO Hospital MIS Admin"
admin.site.index_title = "System Administration"

# django.contrib.auth's Group model plays no role here — every permission
# check goes through apps.accounts's own Role/Permission/UserRole system
# (HasModulePermission never looks at Group). Leaving it registered would
# just be a second, unused, decoy place to try to grant access from.
admin.site.unregister(Group)


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "type", "is_active")
    search_fields = ("name", "code")
    list_filter = ("type", "is_active")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "facility", "parent_department")
    search_fields = ("name", "code")
    list_filter = ("facility",)
