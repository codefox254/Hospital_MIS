"""
Visit lifecycle, vitals, and the consultation draft/lock/addendum rules
(BRD §6.3; Solution Spec Flow 5.3).
"""

from django.utils import timezone

from apps.opd.models import Consultation, Diagnosis, Visit, Vitals

# Standard adult reference ranges — outside these, a nurse-recorded reading
# is flagged for the doctor (BRD §6.5 edge case). Not a diagnosis, just a
# threshold check; clinical judgment on what to do about it stays with the
# doctor.
VITALS_RANGES = {
    "bp_systolic": (90, 140),
    "bp_diastolic": (60, 90),
    "pulse": (60, 100),
    "temperature_c": (36.1, 37.5),
    "respiration_rate": (12, 20),
    "spo2_percent": (95, 100),
}


class InvalidVisitStartError(Exception):
    pass


class ConsultationLockedError(Exception):
    pass


class ConsultationNotLockedError(Exception):
    pass


def start_visit(
    *, facility, patient, doctor, department, appointment=None, actor=None, ip_address=None
):
    """
    Starts a Visit and its (empty, draft) Consultation together — the
    doctor's workspace (Solution Spec Flow 5.3 step 2) always finds one
    waiting rather than having to create it on first access.

    If `appointment` is given, it must currently be checked_in — starting
    the visit is what actually puts the doctor's consultation in progress,
    so the appointment moves to in_consultation alongside it.
    """
    now = timezone.now()

    if appointment is not None:
        from apps.appointments.models import Appointment

        if appointment.status != Appointment.Status.CHECKED_IN:
            raise InvalidVisitStartError(
                f"Cannot start a visit from an appointment with status={appointment.status!r}."
            )
        appointment.status = Appointment.Status.IN_CONSULTATION
        appointment.save(actor=actor, ip_address=ip_address)

    visit = Visit(
        facility=facility,
        patient=patient,
        appointment=appointment,
        doctor=doctor,
        department=department,
        checked_in_at=now,
    )
    visit.save(actor=actor, ip_address=ip_address)

    consultation = Consultation(visit=visit)
    consultation.save(actor=actor, ip_address=ip_address)

    return visit


def _out_of_range_fields(vitals):
    flagged = []
    for field, (low, high) in VITALS_RANGES.items():
        value = getattr(vitals, field)
        if value is not None and not (low <= float(value) <= high):
            flagged.append(field)
    return flagged


def record_vitals(visit, *, recorded_by, actor=None, ip_address=None, **readings):
    vitals = Vitals(visit=visit, recorded_by=recorded_by, recorded_at=timezone.now(), **readings)
    vitals.save(actor=actor, ip_address=ip_address)

    if _out_of_range_fields(vitals):
        from apps.opd.tasks import notify_abnormal_vitals

        notify_abnormal_vitals.delay(str(vitals.id))

    return vitals


def update_consultation_draft(consultation, *, actor=None, ip_address=None, **fields):
    if consultation.locked_at is not None:
        raise ConsultationLockedError(
            "This consultation is locked — use add_addendum() instead of editing it."
        )
    for attr, value in fields.items():
        setattr(consultation, attr, value)
    consultation.save(actor=actor, ip_address=ip_address)
    return consultation


def add_diagnosis(consultation, *, description, type, icd_code="", actor=None, ip_address=None):
    if consultation.locked_at is not None:
        raise ConsultationLockedError(
            "This consultation is locked — a diagnosis can no longer be added directly; "
            "use add_addendum() to record the correction."
        )
    diagnosis = Diagnosis(
        consultation=consultation, description=description, type=type, icd_code=icd_code
    )
    diagnosis.save(actor=actor, ip_address=ip_address)
    return diagnosis


def complete_consultation(consultation, *, actor, ip_address=None):
    """
    Locks the consultation (BRD §6.3: further changes require an addendum,
    never an edit) and closes out the visit.

    Solution Spec Flow 5.3 steps 4 and 6 — dispatching Lab/Radiology/
    Pharmacy orders and generating the billing line items — are deliberately
    NOT done here: those apps don't exist yet (later milestones). Flagged,
    not silently skipped.
    """
    if consultation.locked_at is not None:
        raise ConsultationLockedError("This consultation is already locked.")

    now = timezone.now()
    consultation.is_draft = False
    consultation.locked_at = now
    consultation.signed_by = actor
    consultation.save(actor=actor, ip_address=ip_address)

    visit = consultation.visit
    visit.status = Visit.Status.COMPLETED
    visit.completed_at = now
    visit.save(actor=actor, ip_address=ip_address)

    if visit.appointment_id is not None:
        from apps.appointments.models import Appointment

        appointment = visit.appointment
        appointment.status = Appointment.Status.COMPLETED
        appointment.save(actor=actor, ip_address=ip_address)

    return consultation


def add_addendum(consultation, *, author, text, actor=None, ip_address=None):
    from apps.opd.models import ConsultationAddendum

    if consultation.locked_at is None:
        raise ConsultationNotLockedError(
            "This consultation isn't locked yet — edit the draft directly instead of "
            "adding an addendum."
        )
    addendum = ConsultationAddendum(consultation=consultation, author=author, text=text)
    addendum.save(actor=actor, ip_address=ip_address)
    return addendum
