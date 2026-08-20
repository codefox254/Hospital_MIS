"""
Appointments & Queue Management (BRD §6.2; Data Dictionary §4).

Scope notes worth flagging:
- DoctorSchedule and Appointment are audited (AuditableModel) — schedule and
  booking changes are operationally significant and reversible via soft
  delete, matching the pattern already established for Department/Patient.
- QueueEntry and AppointmentReminder are deliberately NOT audited: they are
  fast-changing operational/notification state tied 1:1 to an Appointment
  (which *is* audited), not clinical records in their own right. Auditing
  every queue-number bump would bloat the audit log without adding a real
  compliance signal — a judgment call, flagged here rather than silently
  applied.
"""

from django.conf import settings
from django.db import models

from apps.core.mixins import AuditableModel
from apps.core.models import Department, FacilityScopedModel, UUIDModel
from apps.patients.models import Patient


class DoctorSchedule(UUIDModel, AuditableModel):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="doctor_schedules"
    )
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="doctor_schedules"
    )
    day_of_week = models.SmallIntegerField(help_text="0=Monday .. 6=Sunday, ISO-style.")
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_duration_minutes = models.SmallIntegerField()

    class Meta:
        ordering = ["doctor", "day_of_week", "start_time"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(day_of_week__gte=0) & models.Q(day_of_week__lte=6),
                name="doctor_schedule_day_of_week_range",
            ),
            models.CheckConstraint(
                condition=models.Q(slot_duration_minutes__gt=0),
                name="doctor_schedule_positive_slot_duration",
            ),
        ]

    def __str__(self):
        return f"{self.doctor} — day {self.day_of_week} {self.start_time}-{self.end_time}"

    def _get_audit_facility_id(self):
        return self.department.facility_id


class Appointment(FacilityScopedModel, AuditableModel):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        CHECKED_IN = "checked_in", "Checked In"
        IN_CONSULTATION = "in_consultation", "In Consultation"
        COMPLETED = "completed", "Completed"
        NO_SHOW = "no_show", "No Show"
        CANCELLED = "cancelled", "Cancelled"

    class BookingChannel(models.TextChoices):
        WEB = "web", "Web"
        MOBILE = "mobile", "Mobile"
        WALK_IN = "walk_in", "Walk-in"

    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="appointments")
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="appointments"
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="appointments"
    )
    scheduled_at = models.DateTimeField()
    duration_minutes = models.SmallIntegerField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SCHEDULED
    )
    booking_channel = models.CharField(max_length=20, choices=BookingChannel.choices)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_appointments",
        help_text="Null if the patient self-booked via mobile.",
    )

    class Meta:
        ordering = ["scheduled_at"]
        indexes = [
            models.Index(fields=["doctor", "scheduled_at"]),
            models.Index(fields=["department", "scheduled_at"]),
        ]
        constraints = [
            # The real double-booking safety net (Solution Spec Flow 5.2):
            # a cancelled/no-show slot frees up, but any other status
            # blocks a second booking at the same doctor+time — enforced by
            # Postgres, not just an application-level check-then-create
            # race.
            models.UniqueConstraint(
                fields=["doctor", "scheduled_at"],
                condition=models.Q(
                    status__in=["scheduled", "checked_in", "in_consultation", "completed"]
                ),
                name="unique_active_appointment_per_doctor_slot",
            )
        ]

    def __str__(self):
        return f"{self.patient} with {self.doctor} @ {self.scheduled_at:%Y-%m-%d %H:%M}"


class QueueEntry(UUIDModel):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Priority(models.TextChoices):
        NORMAL = "normal", "Normal"
        PRIORITY = "priority", "Priority"
        EMERGENCY = "emergency", "Emergency"

    appointment = models.OneToOneField(
        Appointment, on_delete=models.CASCADE, related_name="queue_entry"
    )
    queue_number = models.IntegerField()
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    called_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-priority", "queue_number"]

    def __str__(self):
        return f"#{self.queue_number} — {self.appointment}"


class AppointmentReminder(UUIDModel):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Channel(models.TextChoices):
        SMS = "sms", "SMS"
        WHATSAPP = "whatsapp", "WhatsApp"
        PUSH = "push", "Push"
        EMAIL = "email", "Email"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    appointment = models.ForeignKey(
        Appointment, on_delete=models.CASCADE, related_name="reminders"
    )
    channel = models.CharField(max_length=20, choices=Channel.choices)
    scheduled_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    class Meta:
        ordering = ["scheduled_at"]

    def __str__(self):
        return f"{self.channel} reminder for {self.appointment} ({self.status})"
