"""
register_patient() is the only supported way to create a Patient — MRN
generation is server-side, never client-supplied (Data Dictionary §3,
Solution Spec Flow 5.1). Format: {FACILITY_CODE}-{YEAR}-{SEQUENCE}, e.g.
NBI01-2026-000123, scoped per facility per year.

Concurrency: the per-facility-per-year sequence isn't locked, so two
simultaneous registrations can compute the same candidate MRN — the `mrn`
column's UNIQUE constraint is the real safety net, and a collision here just
means "retry with the next candidate," not a correctness bug.
"""

import datetime

from django.db import IntegrityError, transaction

from apps.patients.models import Patient

MAX_MRN_ATTEMPTS = 5


def _next_mrn_candidate(facility):
    year = datetime.date.today().year
    prefix = f"{facility.code}-{year}-"
    last = (
        Patient.objects.filter(facility=facility, mrn__startswith=prefix).order_by("-mrn").first()
    )
    next_seq = 1
    if last:
        try:
            next_seq = int(last.mrn.rsplit("-", 1)[-1]) + 1
        except ValueError:
            next_seq = 1
    return f"{prefix}{next_seq:06d}"


def register_patient(*, facility, actor=None, ip_address=None, **fields):
    fields.pop("mrn", None)  # never trust a client-supplied MRN, even if sent

    for _ in range(MAX_MRN_ATTEMPTS):
        mrn = _next_mrn_candidate(facility)
        patient = Patient(facility=facility, mrn=mrn, **fields)
        try:
            with transaction.atomic():
                patient.save(actor=actor, ip_address=ip_address)
            return patient
        except IntegrityError:
            continue

    raise RuntimeError(
        f"Could not generate a unique MRN for facility {facility.code} "
        f"after {MAX_MRN_ATTEMPTS} attempts."
    )
