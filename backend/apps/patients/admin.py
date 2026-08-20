from django.contrib import admin

from apps.patients.models import (
    Allergy,
    ChronicCondition,
    Consent,
    EmergencyContact,
    Guardian,
    Patient,
    PatientInsurance,
)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("mrn", "first_name", "last_name", "facility", "is_provisional", "deleted_at")
    list_filter = ("facility", "is_provisional", "gender")
    search_fields = ("mrn", "first_name", "last_name", "phone", "national_id")
    readonly_fields = ("mrn",)


@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = ("name", "patient", "relationship", "phone", "access_revoked_at")
    search_fields = ("name", "patient__mrn")


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ("name", "patient", "relationship", "phone")
    search_fields = ("name", "patient__mrn")


@admin.register(Allergy)
class AllergyAdmin(admin.ModelAdmin):
    list_display = ("substance", "patient", "severity")
    list_filter = ("severity",)
    search_fields = ("substance", "patient__mrn")


@admin.register(ChronicCondition)
class ChronicConditionAdmin(admin.ModelAdmin):
    list_display = ("condition", "patient", "diagnosed_date")
    search_fields = ("condition", "patient__mrn")


@admin.register(Consent)
class ConsentAdmin(admin.ModelAdmin):
    list_display = ("patient", "type", "granted_at", "revoked_at")
    list_filter = ("type",)
    search_fields = ("patient__mrn",)


@admin.register(PatientInsurance)
class PatientInsuranceAdmin(admin.ModelAdmin):
    list_display = ("patient", "insurer_name", "policy_number", "is_primary")
    list_filter = ("is_primary",)
    search_fields = ("insurer_name", "policy_number", "patient__mrn")
