"""
Lab order lifecycle: pending -> collected -> processing -> completed
(BRD §6.6; Solution Spec Flow 5.4).
"""

from django.utils import timezone

from apps.laboratory.models import LabOrder, LabOrderItem, LabResult, LabResultValue, LabSample


class SelfVerificationError(Exception):
    pass


class AlreadyVerifiedError(Exception):
    pass


def create_lab_order(
    *,
    facility,
    visit,
    ordered_by,
    items,
    priority=LabOrder.Priority.ROUTINE,
    actor=None,
    ip_address=None,
):
    """`items` is a list of {"test_code": ..., "test_name": ...} dicts."""
    order = LabOrder(
        facility=facility,
        visit=visit,
        ordered_by=ordered_by,
        priority=priority,
        ordered_at=timezone.now(),
    )
    order.save(actor=actor, ip_address=ip_address)

    for item in items:
        order_item = LabOrderItem(
            lab_order=order, test_code=item["test_code"], test_name=item["test_name"]
        )
        order_item.save(actor=actor, ip_address=ip_address)

    return order


def collect_sample(lab_order_item, *, collected_by, barcode, actor=None, ip_address=None):
    sample = LabSample(
        lab_order_item=lab_order_item,
        barcode=barcode,
        collected_by=collected_by,
        collected_at=timezone.now(),
    )
    sample.save(actor=actor, ip_address=ip_address)

    order = lab_order_item.lab_order
    all_collected = not order.items.exclude(sample__isnull=False).exists()
    if all_collected and order.status == LabOrder.Status.PENDING:
        order.status = LabOrder.Status.COLLECTED
        order.save(actor=actor, ip_address=ip_address)

    return sample


def reject_sample(sample, *, reason, actor=None, ip_address=None):
    sample.status = LabSample.Status.REJECTED
    sample.rejection_reason = reason
    sample.save(actor=actor, ip_address=ip_address)
    return sample


def enter_result(lab_order_item, *, entered_by, values, actor=None, ip_address=None):
    """`values` is a list of {"parameter", "value", "unit", "reference_range", "flag"} dicts."""
    result = LabResult(
        lab_order_item=lab_order_item,
        entered_by=entered_by,
        entered_at=timezone.now(),
        status=LabResult.Status.ENTERED,
        is_critical=any(v.get("flag") == LabResultValue.Flag.CRITICAL for v in values),
    )
    result.save(actor=actor, ip_address=ip_address)

    for value in values:
        result_value = LabResultValue(lab_result=result, **value)
        result_value.save(actor=actor, ip_address=ip_address)

    order = lab_order_item.lab_order
    if order.status in (LabOrder.Status.PENDING, LabOrder.Status.COLLECTED):
        order.status = LabOrder.Status.PROCESSING
        order.save(actor=actor, ip_address=ip_address)

    return result


def verify_result(lab_result, *, verified_by, actor=None, ip_address=None):
    if lab_result.status == LabResult.Status.VERIFIED:
        raise AlreadyVerifiedError("This result has already been verified.")
    if verified_by == lab_result.entered_by:
        raise SelfVerificationError("The technician who entered a result cannot also verify it.")

    now = timezone.now()
    lab_result.verified_by = verified_by
    lab_result.verified_at = now
    lab_result.status = LabResult.Status.VERIFIED
    lab_result.released_to_portal_at = now
    lab_result.save(actor=actor, ip_address=ip_address)

    if lab_result.is_critical:
        from apps.laboratory.tasks import notify_critical_result

        notify_critical_result.delay(str(lab_result.id))

    order = lab_result.lab_order_item.lab_order
    all_verified = not order.items.exclude(result__status=LabResult.Status.VERIFIED).exists()
    if all_verified:
        order.status = LabOrder.Status.COMPLETED
        order.save(actor=actor, ip_address=ip_address)

    return lab_result
