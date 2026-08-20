from django.contrib import admin

from apps.pharmacy.models import DispenseRecord, Drug, Prescription, PrescriptionItem, StockBatch


@admin.register(Drug)
class DrugAdmin(admin.ModelAdmin):
    list_display = ("name", "generic_name", "form", "strength", "is_controlled")
    list_filter = ("is_controlled", "form")
    search_fields = ("name", "generic_name")


@admin.register(StockBatch)
class StockBatchAdmin(admin.ModelAdmin):
    list_display = ("drug", "batch_number", "expiry_date", "quantity_on_hand", "facility")
    list_filter = ("facility",)


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ("patient", "prescribed_by", "status", "created_at")
    list_filter = ("status",)


@admin.register(PrescriptionItem)
class PrescriptionItemAdmin(admin.ModelAdmin):
    list_display = ("prescription", "drug", "dosage", "qty_prescribed")


@admin.register(DispenseRecord)
class DispenseRecordAdmin(admin.ModelAdmin):
    list_display = ("prescription_item", "batch", "dispensed_by", "qty_dispensed", "dispensed_at")
