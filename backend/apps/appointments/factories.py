import datetime

import factory
from django.utils import timezone

from apps.accounts.factories import UserFactory
from apps.appointments.models import Appointment, AppointmentReminder, DoctorSchedule, QueueEntry
from apps.core.factories import DepartmentFactory
from apps.patients.factories import PatientFactory


class DoctorScheduleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DoctorSchedule

    doctor = factory.SubFactory(UserFactory)
    department = factory.SubFactory(DepartmentFactory)
    day_of_week = 0
    start_time = datetime.time(9, 0)
    end_time = datetime.time(17, 0)
    slot_duration_minutes = 30


class AppointmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Appointment

    department = factory.SubFactory(DepartmentFactory)
    facility = factory.SelfAttribute("department.facility")
    patient = factory.SubFactory(
        PatientFactory, facility=factory.SelfAttribute("..department.facility")
    )
    doctor = factory.SubFactory(
        UserFactory, facility=factory.SelfAttribute("..department.facility")
    )
    scheduled_at = factory.LazyFunction(
        lambda: timezone.now().replace(minute=0, second=0, microsecond=0)
        + datetime.timedelta(days=1)
    )
    duration_minutes = 30
    booking_channel = Appointment.BookingChannel.WALK_IN


class QueueEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = QueueEntry

    appointment = factory.SubFactory(AppointmentFactory)
    queue_number = factory.Sequence(lambda n: n + 1)


class AppointmentReminderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AppointmentReminder

    appointment = factory.SubFactory(AppointmentFactory)
    channel = AppointmentReminder.Channel.SMS
    scheduled_at = factory.LazyFunction(timezone.now)
