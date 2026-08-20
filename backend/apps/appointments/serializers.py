from rest_framework import serializers

from apps.appointments.models import Appointment, AppointmentReminder, DoctorSchedule, QueueEntry

COMMON_READ_ONLY_FIELDS = ["id", "created_at", "updated_at"]


class DoctorScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorSchedule
        fields = [
            "id",
            "doctor",
            "department",
            "day_of_week",
            "start_time",
            "end_time",
            "slot_duration_minutes",
            "deleted_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = COMMON_READ_ONLY_FIELDS + ["deleted_at"]


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = [
            "id",
            "facility",
            "patient",
            "doctor",
            "department",
            "scheduled_at",
            "duration_minutes",
            "status",
            "booking_channel",
            "created_by",
            "deleted_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "facility",
            "status",
            "created_by",
            "deleted_at",
            "created_at",
            "updated_at",
        ]


class QueueEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = QueueEntry
        fields = [
            "id",
            "appointment",
            "queue_number",
            "priority",
            "called_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "appointment", "queue_number", "created_at", "updated_at"]


class AppointmentReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentReminder
        fields = [
            "id",
            "appointment",
            "channel",
            "scheduled_at",
            "sent_at",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AvailabilityQuerySerializer(serializers.Serializer):
    doctor = serializers.UUIDField()
    department = serializers.UUIDField()
    date = serializers.DateField()


class BookAppointmentSerializer(serializers.Serializer):
    patient = serializers.UUIDField()
    doctor = serializers.UUIDField()
    department = serializers.UUIDField()
    scheduled_at = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField(min_value=1)
    booking_channel = serializers.ChoiceField(choices=Appointment.BookingChannel.choices)
