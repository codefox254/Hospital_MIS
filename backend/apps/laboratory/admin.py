from django.contrib import admin

from apps.laboratory.models import LabOrder, LabOrderItem, LabResult, LabResultValue, LabSample


@admin.register(LabOrder)
class LabOrderAdmin(admin.ModelAdmin):
    list_display = ("visit", "ordered_by", "priority", "status", "ordered_at")
    list_filter = ("facility", "status", "priority")


@admin.register(LabOrderItem)
class LabOrderItemAdmin(admin.ModelAdmin):
    list_display = ("lab_order", "test_code", "test_name")


@admin.register(LabSample)
class LabSampleAdmin(admin.ModelAdmin):
    list_display = ("barcode", "lab_order_item", "collected_by", "status")
    list_filter = ("status",)


@admin.register(LabResult)
class LabResultAdmin(admin.ModelAdmin):
    list_display = ("lab_order_item", "status", "is_critical", "verified_by")
    list_filter = ("status", "is_critical")


@admin.register(LabResultValue)
class LabResultValueAdmin(admin.ModelAdmin):
    list_display = ("lab_result", "parameter", "value", "flag")
    list_filter = ("flag",)
