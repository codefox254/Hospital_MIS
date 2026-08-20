"""
Prescribing and dispensing (BRD §6.8; Solution Spec Flow 5.6). Stock
decrements happen inside a row-locked transaction (`select_for_update`) —
"decrements stock transactionally" is spec'd explicitly (Flow 5.6 step 3),
not just a nice-to-have, since two pharmacists confirming a dispense
against the same batch at the same moment must never both succeed against
stock that only covers one of them.
"""

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.pharmacy.models import DispenseRecord, Prescription, PrescriptionItem, StockBatch


class InsufficientStockError(Exception):
    pass


class WrongDrugForBatchError(Exception):
    pass


class OverDispenseError(Exception):
    pass


def create_prescription(
    *, consultation, patient, prescribed_by, items, actor=None, ip_address=None
):
    """`items` is a list of {"drug", "dosage", "frequency", "duration_days", "qty_prescribed"}."""
    prescription = Prescription(
        consultation=consultation, patient=patient, prescribed_by=prescribed_by
    )
    prescription.save(actor=actor, ip_address=ip_address)

    for item in items:
        prescription_item = PrescriptionItem(prescription=prescription, **item)
        prescription_item.save(actor=actor, ip_address=ip_address)

    return prescription


def check_patient_allergies(patient, drug):
    """
    Best-effort name-matching against the patient's recorded allergies —
    not a real drug-interaction database (out of scope for this phase),
    just a substring check surfaced to the dispensing pharmacist as a
    flag, never a hard block. Clinical judgment on an actual conflict
    stays with the pharmacist.
    """
    candidates = [drug.name, drug.generic_name]
    conflicts = []
    for allergy in patient.allergies.filter(deleted_at__isnull=True):
        for candidate in candidates:
            if candidate and candidate.lower() in allergy.substance.lower():
                conflicts.append(allergy)
                break
    return conflicts


def dispense_medication(
    prescription_item, *, batch, dispensed_by, qty_dispensed, actor=None, ip_address=None
):
    if batch.drug_id != prescription_item.drug_id:
        raise WrongDrugForBatchError(
            f"Batch {batch.batch_number} is {batch.drug}, not {prescription_item.drug}."
        )

    already_dispensed = (
        prescription_item.dispense_records.aggregate(total=Sum("qty_dispensed"))["total"] or 0
    )
    remaining = prescription_item.qty_prescribed - already_dispensed
    if qty_dispensed > remaining:
        raise OverDispenseError(
            f"Only {remaining} of {prescription_item.qty_prescribed} prescribed units remain."
        )

    with transaction.atomic():
        locked_batch = StockBatch.objects.select_for_update().get(pk=batch.pk)
        if locked_batch.quantity_on_hand < qty_dispensed:
            raise InsufficientStockError(
                f"Batch {locked_batch.batch_number} has {locked_batch.quantity_on_hand} on "
                f"hand, cannot dispense {qty_dispensed}."
            )

        locked_batch.quantity_on_hand -= qty_dispensed
        locked_batch.save(actor=actor, ip_address=ip_address)

        record = DispenseRecord(
            prescription_item=prescription_item,
            batch=locked_batch,
            dispensed_by=dispensed_by,
            qty_dispensed=qty_dispensed,
            dispensed_at=timezone.now(),
        )
        record.save(actor=actor, ip_address=ip_address)

    _refresh_prescription_status(prescription_item.prescription, actor=actor, ip_address=ip_address)
    _bill_dispense_record(record, actor=actor, ip_address=ip_address)
    return record


def _bill_dispense_record(record, *, actor=None, ip_address=None):
    """
    "Generates an InvoiceLineItem on creation" (Data Dictionary §7) — the
    one Pharmacy->Billing hook this codebase actually wires end-to-end,
    because StockBatch.unit_cost is real pricing data. OPD's consultation
    fee and Laboratory's per-test pricing don't get the same treatment:
    neither model defines a price field in the Data Dictionary, and
    inventing one would mean charging a number the spec never specified,
    not just deferring a mechanical wiring step.
    """
    if record.batch.unit_cost is None:
        return

    from apps.billing.services import add_line_item, get_or_create_open_invoice

    prescription = record.prescription_item.prescription
    visit = prescription.consultation.visit
    invoice = get_or_create_open_invoice(
        facility=visit.facility,
        patient=prescription.patient,
        visit=visit,
        created_by=record.dispensed_by,
        actor=actor,
        ip_address=ip_address,
    )
    add_line_item(
        invoice,
        source_module="pharmacy",
        source_reference_id=record.id,
        description=f"{record.batch.drug} x{record.qty_dispensed}",
        unit_price=record.batch.unit_cost,
        quantity=record.qty_dispensed,
        actor=actor,
        ip_address=ip_address,
    )


def _refresh_prescription_status(prescription, *, actor=None, ip_address=None):
    items = list(prescription.items.all())
    fully_dispensed = True
    any_dispensed = False
    for item in items:
        dispensed = item.dispense_records.aggregate(total=Sum("qty_dispensed"))["total"] or 0
        if dispensed > 0:
            any_dispensed = True
        if dispensed < item.qty_prescribed:
            fully_dispensed = False

    new_status = (
        Prescription.Status.DISPENSED
        if fully_dispensed
        else Prescription.Status.PARTIALLY_DISPENSED if any_dispensed else prescription.status
    )
    if new_status != prescription.status:
        prescription.status = new_status
        prescription.save(actor=actor, ip_address=ip_address)
