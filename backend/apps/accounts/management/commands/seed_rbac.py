"""
Seeds the permission catalogue and canonical roles (BRD §8.2's Role →
Permission → User model). Before this command existed, every environment's
Role/Permission rows came from ad-hoc shell/UAT scripts that were never
committed — a fresh `migrate` left HasModulePermission fully wired but with
nothing in the database to grant, so no non-superuser could do anything.
This is the seed that fixes that, and it's the reviewable, extendable
source of truth going forward: run again after adding a new
`permission_codes_by_action` entry and it picks it up.

Idempotent (get_or_create throughout) — safe to run on every deploy.

The operational roles (Receptionist, Doctor, Nurse, Lab Technician, Lab
Scientist, Pharmacist, Cashier, Billing Officer) map directly and
unambiguously to the modules they work in — see PERMISSION_CATALOGUE below,
which is generated from grep'ing every permission_codes_by_action across
apps/*/views.py, not guessed.

The four non-operational privileged roles named in TRD §3.3
(accounts/constants.py's PRIVILEGED_ROLE_NAMES) — Finance Manager, IT
Administrator, Medical Director, Insurance Officer — have no BRD to define
their scope precisely (docs/README.md flags the missing BRD). Their grants
below are conservative, reasonable defaults inferred from the role name
alone; treat them as a placeholder to correct once the real BRD role
matrix is available, same as PRIVILEGED_ROLE_NAMES itself already is.
"""

from django.core.management.base import BaseCommand

from apps.accounts.models import Permission, Role, RolePermission

# code -> human description. One entry per permission_codes_by_action value
# referenced anywhere in apps/*/views.py.
PERMISSION_CATALOGUE = {
    "accounts.user.view": "View staff user directory",
    "accounts.user.create": "Create a staff user account",
    "core.facility.view": "View facility (tenant) records",
    "core.facility.create": "Create a facility (onboard a new hospital)",
    "core.facility.update": "Update a facility's details",
    "core.facility.deactivate": "Deactivate a facility",
    "appointments.appointment.cancel": "Cancel an appointment",
    "appointments.appointment.check_in": "Check in a patient for their appointment",
    "appointments.appointment.create": "Book an appointment",
    "appointments.appointment.update": "Update an appointment",
    "appointments.appointment.view": "View appointments",
    "appointments.doctor_schedule.create": "Create a doctor's schedule",
    "appointments.doctor_schedule.deactivate": "Deactivate a doctor's schedule",
    "appointments.doctor_schedule.update": "Update a doctor's schedule",
    "appointments.doctor_schedule.view": "View doctor schedules",
    "appointments.queue.call": "Call the next patient in the live queue",
    "appointments.queue.view": "View the live queue",
    "appointments.reminder.view": "View appointment reminders",
    "audit.log.view": "View the audit log",
    "billing.invoice.create": "Create an invoice",
    "billing.invoice.discount": "Apply a discount to an invoice",
    "billing.invoice.discount_approve": "Approve a discount above the threshold",
    "billing.invoice.view": "View invoices",
    "billing.payment.create": "Record a payment",
    "billing.payment.view": "View payments",
    "billing.refund.create": "Approve a refund",
    "billing.refund.view": "View refunds",
    "core.department.view": "View departments",
    "laboratory.lab_order.create": "Order a lab test",
    "laboratory.lab_order.view": "View lab orders",
    "laboratory.lab_result.create": "Enter a lab result",
    "laboratory.lab_result.verify": "Verify a lab result",
    "laboratory.lab_result.view": "View lab results",
    "laboratory.lab_sample.create": "Collect a lab sample",
    "laboratory.lab_sample.reject": "Reject a lab sample",
    "laboratory.lab_sample.view": "View lab samples",
    "opd.addendum.create": "Add an addendum to a locked consultation",
    "opd.addendum.view": "View consultation addenda",
    "opd.consultation.complete": "Complete and lock a consultation",
    "opd.consultation.update": "Update a consultation draft",
    "opd.consultation.view": "View consultations",
    "opd.diagnosis.create": "Record a diagnosis",
    "opd.diagnosis.view": "View diagnoses",
    "opd.visit.create": "Start a visit",
    "opd.visit.view": "View visits",
    "opd.vitals.create": "Record vitals",
    "opd.vitals.view": "View vitals",
    "patients.patient.create": "Register a patient",
    "patients.patient.deactivate": "Deactivate a patient record",
    "patients.patient.update": "Update a patient record",
    "patients.patient.view": "View patient records",
    "pharmacy.dispense_record.create": "Dispense a prescription",
    "pharmacy.dispense_record.create_controlled": "Dispense a controlled drug",
    "pharmacy.dispense_record.view": "View dispense records",
    "pharmacy.drug.create": "Add a drug to the catalogue",
    "pharmacy.drug.update": "Update a drug catalogue entry",
    "pharmacy.drug.view": "View the drug catalogue",
    "pharmacy.prescription.cancel": "Cancel a prescription",
    "pharmacy.prescription.create": "Prescribe medication",
    "pharmacy.prescription.view": "View prescriptions",
    "pharmacy.stock_batch.create": "Receive a stock batch",
    "pharmacy.stock_batch.update": "Update a stock batch",
    "pharmacy.stock_batch.view": "View stock batches",
}

_CLINICAL_VIEW = [
    "patients.patient.view",
    "appointments.appointment.view",
    "opd.visit.view",
    "opd.consultation.view",
    "opd.diagnosis.view",
    "opd.vitals.view",
    "opd.addendum.view",
    "laboratory.lab_order.view",
    "laboratory.lab_result.view",
    "pharmacy.prescription.view",
]

# role name -> permission codes granted. Administrator gets every code in
# PERMISSION_CATALOGUE (computed below, not listed here) since "all
# permissions" would otherwise silently drift out of sync as the catalogue
# grows.
ROLE_CATALOGUE = {
    "Receptionist": [
        "patients.patient.view",
        "patients.patient.create",
        "patients.patient.update",
        "appointments.appointment.view",
        "appointments.appointment.create",
        "appointments.appointment.update",
        "appointments.appointment.check_in",
        "appointments.appointment.cancel",
        "appointments.doctor_schedule.view",
        "appointments.queue.view",
        "appointments.reminder.view",
        "core.department.view",
        "accounts.user.view",
    ],
    "Doctor": [
        "patients.patient.view",
        "appointments.appointment.view",
        "appointments.doctor_schedule.view",
        "appointments.queue.view",
        "appointments.queue.call",
        "opd.visit.view",
        "opd.visit.create",
        "opd.consultation.view",
        "opd.consultation.update",
        "opd.consultation.complete",
        "opd.diagnosis.view",
        "opd.diagnosis.create",
        "opd.vitals.view",
        "opd.addendum.view",
        "opd.addendum.create",
        "laboratory.lab_order.view",
        "laboratory.lab_order.create",
        "laboratory.lab_result.view",
        "pharmacy.prescription.view",
        "pharmacy.prescription.create",
        "pharmacy.prescription.cancel",
        "pharmacy.drug.view",
        "core.department.view",
        "accounts.user.view",
    ],
    "Nurse": [
        "patients.patient.view",
        "appointments.appointment.view",
        "appointments.queue.view",
        "opd.visit.view",
        "opd.consultation.view",
        "opd.vitals.view",
        "opd.vitals.create",
        "opd.diagnosis.view",
        "laboratory.lab_order.view",
        "core.department.view",
    ],
    "Lab Technician": [
        "patients.patient.view",
        "laboratory.lab_order.view",
        "laboratory.lab_sample.view",
        "laboratory.lab_sample.create",
        "laboratory.lab_sample.reject",
        "core.department.view",
    ],
    "Lab Scientist": [
        "patients.patient.view",
        "laboratory.lab_order.view",
        "laboratory.lab_sample.view",
        "laboratory.lab_result.view",
        "laboratory.lab_result.create",
        "laboratory.lab_result.verify",
        "core.department.view",
    ],
    "Pharmacist": [
        "patients.patient.view",
        "pharmacy.drug.view",
        "pharmacy.drug.create",
        "pharmacy.drug.update",
        "pharmacy.stock_batch.view",
        "pharmacy.stock_batch.create",
        "pharmacy.stock_batch.update",
        "pharmacy.prescription.view",
        "pharmacy.dispense_record.view",
        "pharmacy.dispense_record.create",
        "pharmacy.dispense_record.create_controlled",
        "core.department.view",
    ],
    "Cashier": [
        "patients.patient.view",
        "billing.invoice.view",
        "billing.invoice.create",
        "billing.payment.view",
        "billing.payment.create",
        "billing.refund.view",
        "core.department.view",
    ],
    "Billing Officer": [
        "patients.patient.view",
        "billing.invoice.view",
        "billing.invoice.create",
        "billing.invoice.discount",
        "billing.invoice.discount_approve",
        "billing.payment.view",
        "billing.refund.view",
        "billing.refund.create",
        "core.department.view",
    ],
    # --- Privileged roles (TRD §3.3 / accounts.constants.PRIVILEGED_ROLE_NAMES).
    # No BRD role matrix exists yet (docs/README.md) — these four are
    # best-effort defaults from the role name alone, not a confirmed spec.
    "Finance Manager": [
        "billing.invoice.view",
        "billing.invoice.discount_approve",
        "billing.payment.view",
        "billing.refund.view",
        "billing.refund.create",
        "audit.log.view",
    ],
    "IT Administrator": [
        "accounts.user.view",
        "audit.log.view",
        "core.department.view",
    ],
    "Medical Director": _CLINICAL_VIEW + ["core.department.view", "accounts.user.view"],
    "Insurance Officer": [
        "patients.patient.view",
        "billing.invoice.view",
    ],
    # --- SaaS tenancy tier (Facility = tenant record; see core/serializers.py).
    # Super Admin is platform-wide (unscoped UserRole grant, enforced in
    # create_user_with_role) and deliberately holds none of the
    # facility-scoped clinical/billing/etc. codes below — it manages
    # tenants (Facility rows) and onboards each tenant's first admin, not
    # their patients' records. Administrator is the per-tenant ("Facility
    # Admin") role and is the opposite: everything *except* core.facility.*,
    # which only Super Admin may hold.
    "Super Admin": [
        "core.facility.view",
        "core.facility.create",
        "core.facility.update",
        "core.facility.deactivate",
        "accounts.user.view",
        "accounts.user.create",
    ],
}

# Facility Admin (role name kept as "Administrator" — established elsewhere
# in this codebase, e.g. tests/UAT fixtures) gets every operational
# permission except the platform-tenancy ones, which are Super Admin-only.
_FACILITY_ADMIN_EXCLUDED_CODES = {
    "core.facility.view",
    "core.facility.create",
    "core.facility.update",
    "core.facility.deactivate",
}


class Command(BaseCommand):
    help = "Seeds the permission catalogue and canonical roles (idempotent)."

    def handle(self, *args, **options):
        permissions = {}
        created_perms = 0
        for code, description in PERMISSION_CATALOGUE.items():
            perm, created = Permission.objects.get_or_create(
                code=code, defaults={"description": description}
            )
            if not created and perm.description != description:
                perm.description = description
                perm.save()
            permissions[code] = perm
            created_perms += created
        self.stdout.write(f"Permissions: {len(permissions)} total, {created_perms} created")

        role_catalogue = dict(ROLE_CATALOGUE)
        role_catalogue["Administrator"] = [
            code for code in PERMISSION_CATALOGUE if code not in _FACILITY_ADMIN_EXCLUDED_CODES
        ]

        created_roles = 0
        for role_name, codes in role_catalogue.items():
            role, created = Role.objects.get_or_create(
                name=role_name,
                defaults={"description": f"{role_name} — seeded by seed_rbac"},
            )
            created_roles += created
            for code in codes:
                RolePermission.objects.get_or_create(role=role, permission=permissions[code])
        self.stdout.write(f"Roles: {len(role_catalogue)} total, {created_roles} created")
        self.stdout.write(self.style.SUCCESS("RBAC seed complete."))
