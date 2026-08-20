from django.contrib import admin

from apps.patients.models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("mrn", "first_name", "last_name", "facility", "is_provisional", "deleted_at")
    list_filter = ("facility", "is_provisional", "gender")
    search_fields = ("mrn", "first_name", "last_name", "phone", "national_id")
    readonly_fields = ("mrn",)
