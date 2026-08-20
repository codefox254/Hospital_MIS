from django.contrib import admin

from apps.appointments.models import Appointment, AppointmentReminder, DoctorSchedule, QueueEntry


@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(admin.ModelAdmin):
    list_display = ("doctor", "department", "day_of_week", "start_time", "end_time")
    list_filter = ("department", "day_of_week")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "department", "scheduled_at", "status")
    list_filter = ("facility", "department", "status", "booking_channel")
    search_fields = ("patient__mrn", "patient__first_name", "patient__last_name")


@admin.register(QueueEntry)
class QueueEntryAdmin(admin.ModelAdmin):
    list_display = ("appointment", "queue_number", "priority", "called_at")
    list_filter = ("priority",)


@admin.register(AppointmentReminder)
class AppointmentReminderAdmin(admin.ModelAdmin):
    list_display = ("appointment", "channel", "scheduled_at", "sent_at", "status")
    list_filter = ("channel", "status")
