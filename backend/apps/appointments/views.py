"""
Appointments & Queue API (BRD §6.2; Solution Spec Flow 5.2). Booking and
check-in always go through apps.appointments.services — never a bare
ModelViewSet.perform_create() — so the double-booking guard, reminder
scheduling, and live queue publish stay in one place.
"""

from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers as drf_serializers
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasModulePermission
from apps.appointments.models import Appointment, AppointmentReminder, DoctorSchedule, QueueEntry
from apps.appointments.serializers import (
    AppointmentReminderSerializer,
    AppointmentSerializer,
    AvailabilityQuerySerializer,
    BookAppointmentSerializer,
    DoctorScheduleSerializer,
    QueueEntrySerializer,
)
from apps.appointments.services import (
    InvalidCheckInError,
    SlotAlreadyBookedError,
    book_appointment,
    check_in_appointment,
    get_available_slots,
)
from apps.core.models import Department


class DoctorScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = DoctorScheduleSerializer
    permission_classes = [HasModulePermission]
    permission_codes_by_action = {
        "list": "appointments.doctor_schedule.view",
        "retrieve": "appointments.doctor_schedule.view",
        "create": "appointments.doctor_schedule.create",
        "update": "appointments.doctor_schedule.update",
        "partial_update": "appointments.doctor_schedule.update",
        "deactivate": "appointments.doctor_schedule.deactivate",
    }
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["doctor", "department", "day_of_week"]
    queryset = DoctorSchedule.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return DoctorSchedule.objects.none()
        return DoctorSchedule.objects.filter(
            department__facility=self.request.user.facility, deleted_at__isnull=True
        )

    def perform_create(self, serializer):
        instance = DoctorSchedule(**serializer.validated_data)
        instance.save(actor=self.request.user, ip_address=self.request.META.get("REMOTE_ADDR"))
        serializer.instance = instance

    def perform_update(self, serializer):
        instance = serializer.instance
        for attr, value in serializer.validated_data.items():
            setattr(instance, attr, value)
        instance.save(actor=self.request.user, ip_address=self.request.META.get("REMOTE_ADDR"))

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        instance = self.get_object()
        instance.soft_delete(actor=request.user, ip_address=request.META.get("REMOTE_ADDR"))
        return Response(status=status.HTTP_204_NO_CONTENT)


class AvailabilityView(APIView):
    """GET /api/v1/appointments/availability/ — Solution Spec Flow 5.2 step 1."""

    permission_classes = [HasModulePermission]
    permission_code = "appointments.appointment.view"

    def get(self, request):
        query = AvailabilityQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        department = get_object_or_404(
            Department, pk=query.validated_data["department"], facility=request.user.facility
        )
        from apps.accounts.models import User

        doctor = get_object_or_404(
            User, pk=query.validated_data["doctor"], facility=request.user.facility
        )

        slots = get_available_slots(
            doctor=doctor, department=department, date=query.validated_data["date"]
        )
        return Response({"slots": [slot.isoformat() for slot in slots]})


class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [HasModulePermission]
    permission_codes_by_action = {
        "list": "appointments.appointment.view",
        "retrieve": "appointments.appointment.view",
        "create": "appointments.appointment.create",
        "update": "appointments.appointment.update",
        "partial_update": "appointments.appointment.update",
        "check_in": "appointments.appointment.check_in",
        "cancel": "appointments.appointment.cancel",
    }
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["doctor", "department", "patient", "status"]
    queryset = Appointment.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Appointment.objects.none()
        return Appointment.objects.filter(
            facility=self.request.user.facility, deleted_at__isnull=True
        )

    def get_serializer_class(self):
        if self.action == "create":
            return BookAppointmentSerializer
        return AppointmentSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from apps.accounts.models import User
        from apps.patients.models import Patient

        patient = get_object_or_404(Patient, pk=data["patient"], facility=request.user.facility)
        doctor = get_object_or_404(User, pk=data["doctor"], facility=request.user.facility)
        department = get_object_or_404(
            Department, pk=data["department"], facility=request.user.facility
        )

        try:
            appointment = book_appointment(
                facility=request.user.facility,
                patient=patient,
                doctor=doctor,
                department=department,
                scheduled_at=data["scheduled_at"],
                duration_minutes=data["duration_minutes"],
                booking_channel=data["booking_channel"],
                created_by=request.user,
                actor=request.user,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except SlotAlreadyBookedError as exc:
            raise drf_serializers.ValidationError(str(exc), code="slot_already_booked")

        output = AppointmentSerializer(appointment)
        return Response(output.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        instance = serializer.instance
        for attr, value in serializer.validated_data.items():
            setattr(instance, attr, value)
        instance.save(actor=self.request.user, ip_address=self.request.META.get("REMOTE_ADDR"))

    @action(detail=True, methods=["post"])
    def check_in(self, request, pk=None):
        appointment = self.get_object()
        try:
            queue_entry = check_in_appointment(
                appointment, actor=request.user, ip_address=request.META.get("REMOTE_ADDR")
            )
        except InvalidCheckInError as exc:
            raise drf_serializers.ValidationError(str(exc), code="invalid_check_in")
        return Response(QueueEntrySerializer(queue_entry).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        appointment.status = Appointment.Status.CANCELLED
        appointment.save(actor=request.user, ip_address=request.META.get("REMOTE_ADDR"))
        return Response(AppointmentSerializer(appointment).data)


class QueueEntryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = QueueEntrySerializer
    permission_classes = [HasModulePermission]
    permission_codes_by_action = {
        "list": "appointments.queue.view",
        "retrieve": "appointments.queue.view",
        "call": "appointments.queue.call",
    }
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["appointment__department"]
    queryset = QueueEntry.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return QueueEntry.objects.none()
        return QueueEntry.objects.filter(appointment__facility=self.request.user.facility)

    @action(detail=True, methods=["post"])
    def call(self, request, pk=None):
        from django.utils import timezone

        entry = self.get_object()
        entry.called_at = timezone.now()
        entry.save(update_fields=["called_at"])
        return Response(QueueEntrySerializer(entry).data)


class AppointmentReminderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AppointmentReminderSerializer
    permission_classes = [HasModulePermission]
    permission_code = "appointments.reminder.view"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["appointment", "status"]
    queryset = AppointmentReminder.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return AppointmentReminder.objects.none()
        return AppointmentReminder.objects.filter(appointment__facility=self.request.user.facility)
