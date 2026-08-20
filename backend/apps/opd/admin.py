from django.contrib import admin

from apps.opd.models import Consultation, ConsultationAddendum, Diagnosis, Visit, Vitals


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "department", "status", "checked_in_at")
    list_filter = ("facility", "department", "status")
    search_fields = ("patient__mrn", "patient__first_name", "patient__last_name")


@admin.register(Vitals)
class VitalsAdmin(admin.ModelAdmin):
    list_display = ("visit", "recorded_by", "recorded_at")


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ("visit", "is_draft", "locked_at", "signed_by")
    list_filter = ("is_draft",)


@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    list_display = ("consultation", "icd_code", "description", "type")
    list_filter = ("type",)


@admin.register(ConsultationAddendum)
class ConsultationAddendumAdmin(admin.ModelAdmin):
    list_display = ("consultation", "author", "created_at")
