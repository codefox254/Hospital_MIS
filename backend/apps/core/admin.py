from django.contrib import admin

from apps.core.models import Department, Facility


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
