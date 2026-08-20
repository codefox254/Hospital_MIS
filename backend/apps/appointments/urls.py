from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.appointments.views import (
    AppointmentReminderViewSet,
    AppointmentViewSet,
    AvailabilityView,
    DoctorScheduleViewSet,
    QueueEntryViewSet,
)

app_name = "appointments"

router = DefaultRouter()
router.register("schedules", DoctorScheduleViewSet, basename="doctor-schedule")
router.register("appointments", AppointmentViewSet, basename="appointment")
router.register("queue-entries", QueueEntryViewSet, basename="queue-entry")
router.register("reminders", AppointmentReminderViewSet, basename="reminder")

urlpatterns = [
    path("availability/", AvailabilityView.as_view(), name="availability"),
] + router.urls
