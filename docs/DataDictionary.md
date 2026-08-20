# FDO Hospital MIS — Phase 1 Data Dictionary & Entity Relationship Reference

> Converted from the source `.docx` for in-repo, greppable reference. Table structure was
> flattened during conversion (one cell/paragraph per line) — treat this as a faithful text
> extraction, not a pixel-exact re-render of the original tables.

Phase 1 Data Dictionary & Entity Relationship Reference  
Core · Patient Management · Appointments & Queue · OPD · Laboratory · Pharmacy · Billing  
Prepared for FDO Technologies  
Draft — Version 0.1  
August 2026  
Field  
Detail  
Document Status  
Draft — for internal review  
Version  
0.1  
Owner  
Solutions Architecture / Engineering  
Scope  
Phase 1 modules only, per the BRD roadmap (§5) — Core/Shared, Patient Management, Appointments & Queue, OPD, Laboratory, Pharmacy, Billing  
Companion Documents  
Business Requirements Document; Technical Requirements Document; Solution Specification & Architecture Document  
Table of Contents  
## 1. Introduction & Scope
This document is the build-ready data dictionary and entity-relationship reference for FDO Hospital MIS Phase 1 — the module set defined in the BRD's roadmap (§5) as the minimum for a single facility to run its full day-to-day OPD operation end-to-end: Core/Shared (Facility, Users, Roles), Patient Management, Appointments & Queue, OPD / Clinical, Laboratory (LIS), Pharmacy, and Billing & Revenue.  
Every entity below follows the conventions in the Technical Requirements Document (§8.1): UUID primary keys, a facility_id on every core table, created_at/updated_at/created_by/updated_by audit columns (omitted from the tables below for brevity, but present on every entity unless noted), and soft deletion (deleted_at) rather than destructive deletes on clinical and financial tables.  
This document is the direct engineering artifact for:  
Writing the Phase 1 Django models and migrations.  
Confirming every field referenced in the BRD's user stories and the Solution Specification's system flows actually has a home.  
Reviewing foreign-key relationships before they're locked in by a migration.  
### 1.1 Conventions Used Below
Convention  
Meaning  
UUID  
All primary keys and foreign keys use UUIDs, not sequential integers, to avoid record enumeration across facilities (TRD §8.1).  
Standard audit columns  
Every table listed below also carries created_at, updated_at, created_by, updated_by unless explicitly noted otherwise — omitted from the field tables to keep them scannable.  
Soft delete  
Clinical and financial tables carry deleted_at instead of supporting a hard DELETE.  
ENUM  
A fixed set of string values, implemented as a Django/Postgres choice field — the allowed values are listed in the Constraints or Description column.  
FK →  
Foreign key reference to the named entity's id column.  
## 2. Core / Shared Entities
Underpins every module: facility scoping, identity, and the RBAC permission engine defined in the BRD (§8) and TRD (§4.3).  
Facility  
Department  
User / Role / Permission  
AuditLogEntry  
Facility  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
Unique facility identifier  
name  
VARCHAR(150)  
NOT NULL  
Facility display name  
code  
VARCHAR(20)  
UNIQUE, NOT NULL  
Short code used in MRNs/invoice numbers  
type  
ENUM  
NOT NULL  
clinic | hospital | branch  
address  
TEXT  
—  
Physical address  
phone  
VARCHAR(20)  
—  
Primary contact number  
is_active  
BOOLEAN  
DEFAULT true  
Soft-enable/disable a facility  
Relationships  
Referenced by facility_id on every core table across every module (multi-branch scoping, TRD §8.1).  
Department  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
facility_id  
UUID  
FK → Facility, NOT NULL  
—  
name  
VARCHAR(100)  
NOT NULL  
e.g. OPD, Laboratory, Cardiology  
code  
VARCHAR(20)  
NOT NULL  
—  
parent_department_id  
UUID  
FK → Department, NULLABLE  
Supports sub-departments/specialties  
Relationships  
Referenced by Appointment, Visit, LabOrder, and staff scoping across the system.  
User  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
facility_id  
UUID  
FK → Facility, NOT NULL  
Home facility; multi-facility access via UserRole scoping  
email  
VARCHAR(255)  
UNIQUE, NOT NULL  
—  
phone  
VARCHAR(20)  
UNIQUE  
—  
password_hash  
VARCHAR(255)  
NOT NULL  
Argon2/bcrypt hash — never plaintext, never logged  
mfa_enabled  
BOOLEAN  
DEFAULT false  
Required true for privileged roles, TRD §3.3  
is_active  
BOOLEAN  
DEFAULT true  
Termination revokes access immediately, BRD §16 edge case  
last_login_at  
TIMESTAMP  
NULLABLE  
—  
Relationships  
1:N with UserRole (a user holds one or more roles, BRD §4).  
Role  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
name  
VARCHAR(100)  
NOT NULL  
e.g. Doctor, Lab Scientist, Billing Officer  
description  
TEXT  
—  
—  
Relationships  
N:M with Permission via RolePermission; N:M with User via UserRole.  
Permission  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
code  
VARCHAR(100)  
UNIQUE, NOT NULL  
module.resource.action, e.g. lab.result.verify  
description  
TEXT  
—  
—  
Relationships  
N:M with Role via RolePermission (BRD §8 permission engine).  
UserRole  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
user_id  
UUID  
FK → User, NOT NULL  
—  
role_id  
UUID  
FK → Role, NOT NULL  
—  
facility_id  
UUID  
FK → Facility, NULLABLE  
Scopes the role grant to one facility if set  
department_id  
UUID  
FK → Department, NULLABLE  
Scopes the role grant to one department if set  
Relationships  
Join table implementing the User ↔ Role ↔ scope model from BRD §8.2.  
AuditLogEntry  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
actor_id  
UUID  
FK → User, NULLABLE  
Null for system-actor writes  
facility_id  
UUID  
FK → Facility, NOT NULL  
—  
model_name  
VARCHAR(100)  
NOT NULL  
—  
record_id  
UUID  
NOT NULL  
—  
action  
ENUM  
NOT NULL  
create | update | soft_delete  
field_diff  
JSONB  
—  
Before/after values for changed fields  
ip_address  
VARCHAR(45)  
—  
—  
created_at  
TIMESTAMP  
NOT NULL  
—  
Relationships  
Independent append-only store, written to by every clinical/financial model's audit mixin (TRD §8.4).  
## 3. Patient Management
BRD §6.1 — the longitudinal patient record every other module reads from and writes back into.  
Patient  
Guardian / EmergencyContact  
Allergy / ChronicCondition  
Consent / PatientInsurance  
Patient  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
facility_id  
UUID  
FK → Facility, NOT NULL  
—  
mrn  
VARCHAR(20)  
UNIQUE, NOT NULL  
System-generated at registration, never client-supplied  
first_name  
VARCHAR(100)  
NOT NULL  
—  
last_name  
VARCHAR(100)  
NOT NULL  
—  
date_of_birth  
DATE  
NULLABLE  
Nullable to support provisional/unidentified registration  
gender  
ENUM  
—  
male | female | other | unspecified  
national_id  
VARCHAR(30)  
NULLABLE  
Unverified text unless government API integration is confirmed, TRD §10  
phone  
VARCHAR(20)  
—  
—  
email  
VARCHAR(255)  
NULLABLE  
—  
photo_url  
VARCHAR(500)  
NULLABLE  
Object storage reference  
blood_group  
VARCHAR(5)  
NULLABLE  
—  
is_provisional  
BOOLEAN  
DEFAULT false  
True for unidentified/emergency quick-registration, BRD §6.1 & §6.12 edge cases  
merged_into_patient_id  
UUID  
FK → Patient, NULLABLE  
Set when this record is merged as a duplicate  
deleted_at  
TIMESTAMP  
NULLABLE  
Soft delete only, TRD §8.1  
Relationships  
1:N Guardian, EmergencyContact, Allergy, ChronicCondition, Consent, PatientInsurance. Self-referencing merged_into_patient_id for de-duplication (BRD §6.1 edge case).  
Guardian  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
patient_id  
UUID  
FK → Patient, NOT NULL  
—  
name  
VARCHAR(150)  
NOT NULL  
—  
relationship  
VARCHAR(50)  
NOT NULL  
—  
phone  
VARCHAR(20)  
NOT NULL  
—  
access_revoked_at  
TIMESTAMP  
NULLABLE  
Supports per-guardian revocation, BRD §6.1 edge case  
Relationships  
N:1 Patient.  
EmergencyContact  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
patient_id  
UUID  
FK → Patient, NOT NULL  
—  
name  
VARCHAR(150)  
NOT NULL  
—  
relationship  
VARCHAR(50)  
—  
—  
phone  
VARCHAR(20)  
NOT NULL  
—  
Relationships  
N:1 Patient.  
Allergy  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
patient_id  
UUID  
FK → Patient, NOT NULL  
—  
substance  
VARCHAR(150)  
NOT NULL  
e.g. Penicillin, Peanuts  
reaction  
VARCHAR(255)  
—  
—  
severity  
ENUM  
—  
mild | moderate | severe  
Relationships  
N:1 Patient. Read by Pharmacy at dispensing time for the hard-stop interaction check (BRD §6.8 edge case).  
ChronicCondition  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
patient_id  
UUID  
FK → Patient, NOT NULL  
—  
condition  
VARCHAR(150)  
NOT NULL  
e.g. Hypertension, Diabetes Type 2  
diagnosed_date  
DATE  
NULLABLE  
—  
Relationships  
N:1 Patient.  
Consent  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
patient_id  
UUID  
FK → Patient, NOT NULL  
—  
type  
ENUM  
NOT NULL  
data_use | treatment | portal_release  
granted_at  
TIMESTAMP  
NOT NULL  
—  
revoked_at  
TIMESTAMP  
NULLABLE  
Revocation must never block emergency care, BRD §6.1 edge case  
Relationships  
N:1 Patient.  
PatientInsurance  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
patient_id  
UUID  
FK → Patient, NOT NULL  
—  
insurer_name  
VARCHAR(150)  
NOT NULL  
—  
policy_number  
VARCHAR(50)  
NOT NULL  
—  
member_number  
VARCHAR(50)  
—  
—  
is_primary  
BOOLEAN  
DEFAULT true  
Supports coordination-of-benefits, BRD §6.10 edge case  
Relationships  
N:1 Patient. Read by the Insurance module during eligibility verification (BRD §6.10).  
## 4. Appointments & Queue Management
BRD §6.2 — booking, scheduling, and the live queue.  
DoctorSchedule  
Appointment  
QueueEntry  
AppointmentReminder  
DoctorSchedule  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
user_id  
UUID  
FK → User, NOT NULL  
The doctor  
department_id  
UUID  
FK → Department, NOT NULL  
—  
day_of_week  
SMALLINT  
NOT NULL  
0–6  
start_time  
TIME  
NOT NULL  
—  
end_time  
TIME  
NOT NULL  
—  
slot_duration_minutes  
SMALLINT  
NOT NULL  
Drives availability calculation, TRD Flow 5.2  
Relationships  
N:1 User (doctor), N:1 Department.  
Appointment  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
facility_id  
UUID  
FK → Facility, NOT NULL  
—  
patient_id  
UUID  
FK → Patient, NOT NULL  
—  
doctor_id  
UUID  
FK → User, NOT NULL  
—  
department_id  
UUID  
FK → Department, NOT NULL  
—  
scheduled_at  
TIMESTAMP  
NOT NULL  
—  
duration_minutes  
SMALLINT  
NOT NULL  
—  
status  
ENUM  
NOT NULL, DEFAULT scheduled  
scheduled | checked_in | in_consultation | completed | no_show | cancelled  
booking_channel  
ENUM  
NOT NULL  
web | mobile | walk_in  
created_by  
UUID  
FK → User, NULLABLE  
Null if patient self-booked via mobile  
Relationships  
N:1 Patient, N:1 User (doctor), N:1 Department. 1:1 QueueEntry once checked in. 1:N AppointmentReminder.  
QueueEntry  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
appointment_id  
UUID  
FK → Appointment, UNIQUE, NOT NULL  
—  
queue_number  
INTEGER  
NOT NULL  
—  
priority  
ENUM  
DEFAULT normal  
normal | priority | emergency — supports queue-jump edge case, BRD §6.2  
called_at  
TIMESTAMP  
NULLABLE  
—  
Relationships  
1:1 Appointment. Drives the real-time queue display via WebSocket (Solution Spec Flow 5.2).  
AppointmentReminder  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
appointment_id  
UUID  
FK → Appointment, NOT NULL  
—  
channel  
ENUM  
NOT NULL  
sms | whatsapp | push | email  
scheduled_at  
TIMESTAMP  
NOT NULL  
—  
sent_at  
TIMESTAMP  
NULLABLE  
—  
status  
ENUM  
DEFAULT pending  
pending | sent | failed  
Relationships  
N:1 Appointment. Written and dispatched by Celery Beat/Celery Worker (Solution Spec Flow 5.2).  
## 5. OPD / Clinical Management
BRD §6.3 — the consultation record and the point at which Lab, Pharmacy, and (in Phase 2) Radiology orders originate.  
Visit  
Vitals  
Consultation  
Diagnosis / Addendum  
Visit  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
facility_id  
UUID  
FK → Facility, NOT NULL  
—  
patient_id  
UUID  
FK → Patient, NOT NULL  
—  
appointment_id  
UUID  
FK → Appointment, NULLABLE  
Null for walk-in/emergency visits  
doctor_id  
UUID  
FK → User, NOT NULL  
—  
department_id  
UUID  
FK → Department, NOT NULL  
—  
status  
ENUM  
NOT NULL  
in_progress | completed  
checked_in_at  
TIMESTAMP  
—  
—  
completed_at  
TIMESTAMP  
NULLABLE  
—  
Relationships  
N:1 Patient, N:1 Appointment (nullable), N:1 User (doctor). 1:N Vitals. 1:1 Consultation.  
Vitals  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
visit_id  
UUID  
FK → Visit, NOT NULL  
—  
recorded_by  
UUID  
FK → User, NOT NULL  
Typically a Nurse  
bp_systolic  
SMALLINT  
—  
—  
bp_diastolic  
SMALLINT  
—  
—  
pulse  
SMALLINT  
—  
—  
temperature_c  
DECIMAL(4,1)  
—  
—  
respiration_rate  
SMALLINT  
—  
—  
spo2_percent  
SMALLINT  
—  
—  
weight_kg  
DECIMAL(5,2)  
—  
—  
height_cm  
DECIMAL(5,2)  
—  
—  
recorded_at  
TIMESTAMP  
NOT NULL  
—  
Relationships  
N:1 Visit. Out-of-threshold values trigger a doctor notification (BRD §6.5 edge case).  
Consultation  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
visit_id  
UUID  
FK → Visit, UNIQUE, NOT NULL  
—  
chief_complaint  
TEXT  
—  
—  
history_of_present_illness  
TEXT  
—  
—  
examination_notes  
TEXT  
—  
—  
is_draft  
BOOLEAN  
DEFAULT true  
Supports interrupted-consultation recovery, BRD §6.3 edge case  
locked_at  
TIMESTAMP  
NULLABLE  
Set on Complete Consultation; further changes require an Addendum  
signed_by  
UUID  
FK → User, NULLABLE  
—  
Relationships  
1:1 Visit. 1:N Diagnosis, 1:N ConsultationAddendum. Triggers creation of LabOrder/RadiologyOrder/Prescription records on completion (Solution Spec Flow 5.3).  
Diagnosis  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
consultation_id  
UUID  
FK → Consultation, NOT NULL  
—  
icd_code  
VARCHAR(10)  
—  
e.g. I10, E11  
description  
VARCHAR(255)  
NOT NULL  
—  
type  
ENUM  
NOT NULL  
primary | secondary | differential  
Relationships  
N:1 Consultation.  
ConsultationAddendum  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
consultation_id  
UUID  
FK → Consultation, NOT NULL  
—  
author_id  
UUID  
FK → User, NOT NULL  
—  
text  
TEXT  
NOT NULL  
—  
created_at  
TIMESTAMP  
NOT NULL  
—  
Relationships  
N:1 Consultation. Enforces the never-silently-edit-a-signed-note rule (BRD §6.3 edge case).  
## 6. Laboratory Information System (LIS)
BRD §6.6 — order-to-verified-result, with the technician/scientist separation of duties enforced at the schema level via distinct entered_by / verified_by columns.  
LabOrder → LabOrderItem  
LabSample  
LabResult  
LabResultValue  
LabOrder  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
visit_id  
UUID  
FK → Visit, NOT NULL  
—  
ordered_by  
UUID  
FK → User, NOT NULL  
Doctor — cannot hold lab.result.enter/verify permissions  
facility_id  
UUID  
FK → Facility, NOT NULL  
—  
priority  
ENUM  
DEFAULT routine  
routine | stat  
status  
ENUM  
NOT NULL  
pending | collected | processing | completed  
ordered_at  
TIMESTAMP  
NOT NULL  
—  
Relationships  
N:1 Visit. 1:N LabOrderItem.  
LabOrderItem  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
lab_order_id  
UUID  
FK → LabOrder, NOT NULL  
—  
test_code  
VARCHAR(20)  
NOT NULL  
e.g. CBC, FBS, LIPID  
test_name  
VARCHAR(150)  
NOT NULL  
—  
Relationships  
N:1 LabOrder. 1:1 LabSample. 1:1 LabResult.  
LabSample  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
lab_order_item_id  
UUID  
FK → LabOrderItem, UNIQUE, NOT NULL  
—  
barcode  
VARCHAR(50)  
UNIQUE, NOT NULL  
—  
collected_by  
UUID  
FK → User, NOT NULL  
Lab Technician  
collected_at  
TIMESTAMP  
NOT NULL  
—  
status  
ENUM  
NOT NULL  
collected | rejected | received  
rejection_reason  
VARCHAR(255)  
NULLABLE  
e.g. hemolyzed, insufficient — BRD §6.6 edge case  
Relationships  
1:1 LabOrderItem.  
LabResult  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
lab_order_item_id  
UUID  
FK → LabOrderItem, UNIQUE, NOT NULL  
—  
entered_by  
UUID  
FK → User, NULLABLE  
Lab Technician  
entered_at  
TIMESTAMP  
NULLABLE  
—  
verified_by  
UUID  
FK → User, NULLABLE  
Lab Scientist — must differ from entered_by, BRD §6.6 permission rule  
verified_at  
TIMESTAMP  
NULLABLE  
—  
status  
ENUM  
NOT NULL  
entered | verified | amended  
is_critical  
BOOLEAN  
DEFAULT false  
Triggers the < 60s alert path, TRD §3.1  
released_to_portal_at  
TIMESTAMP  
NULLABLE  
—  
Relationships  
1:1 LabOrderItem. 1:N LabResultValue.  
LabResultValue  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
lab_result_id  
UUID  
FK → LabResult, NOT NULL  
—  
parameter  
VARCHAR(50)  
NOT NULL  
e.g. WBC, Hemoglobin  
value  
VARCHAR(30)  
NOT NULL  
—  
unit  
VARCHAR(20)  
—  
—  
reference_range  
VARCHAR(50)  
—  
—  
flag  
ENUM  
DEFAULT normal  
normal | low | high | critical  
Relationships  
N:1 LabResult.  
## 7. Pharmacy Management
BRD §6.8 — prescribing, stock, and dispensing, with batch-level traceability for recalls.  
Drug / StockBatch  
Prescription → PrescriptionItem  
DispenseRecord  
Drug  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
name  
VARCHAR(150)  
NOT NULL  
—  
generic_name  
VARCHAR(150)  
—  
—  
form  
VARCHAR(50)  
—  
tablet | syrup | injection | ...  
strength  
VARCHAR(30)  
—  
e.g. 500mg  
is_controlled  
BOOLEAN  
DEFAULT false  
Gates Pharmacy Technician access, BRD §6.8  
Relationships  
1:N StockBatch. Referenced by PrescriptionItem.  
Prescription  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
consultation_id  
UUID  
FK → Consultation, NOT NULL  
—  
patient_id  
UUID  
FK → Patient, NOT NULL  
—  
prescribed_by  
UUID  
FK → User, NOT NULL  
—  
status  
ENUM  
NOT NULL  
pending | partially_dispensed | dispensed | cancelled  
created_at  
TIMESTAMP  
NOT NULL  
—  
Relationships  
N:1 Consultation, N:1 Patient. 1:N PrescriptionItem.  
PrescriptionItem  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
prescription_id  
UUID  
FK → Prescription, NOT NULL  
—  
drug_id  
UUID  
FK → Drug, NOT NULL  
—  
dosage  
VARCHAR(50)  
NOT NULL  
—  
frequency  
VARCHAR(50)  
NOT NULL  
—  
duration_days  
SMALLINT  
—  
—  
qty_prescribed  
INTEGER  
NOT NULL  
—  
Relationships  
N:1 Prescription, N:1 Drug. 1:N DispenseRecord.  
StockBatch  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
drug_id  
UUID  
FK → Drug, NOT NULL  
—  
facility_id  
UUID  
FK → Facility, NOT NULL  
—  
batch_number  
VARCHAR(50)  
NOT NULL  
—  
expiry_date  
DATE  
NOT NULL  
—  
quantity_on_hand  
INTEGER  
NOT NULL  
—  
unit_cost  
DECIMAL(10,2)  
—  
—  
Relationships  
N:1 Drug. Referenced by DispenseRecord for batch traceability (BRD §6.8 recall edge case).  
DispenseRecord  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
prescription_item_id  
UUID  
FK → PrescriptionItem, NOT NULL  
—  
batch_id  
UUID  
FK → StockBatch, NOT NULL  
—  
dispensed_by  
UUID  
FK → User, NOT NULL  
—  
qty_dispensed  
INTEGER  
NOT NULL  
—  
dispensed_at  
TIMESTAMP  
NOT NULL  
—  
Relationships  
N:1 PrescriptionItem, N:1 StockBatch. Generates an InvoiceLineItem on creation.  
## 8. Billing & Revenue Management
BRD §6.9 — every module above generates InvoiceLineItem records here; this module never accepts a hand-entered charge.  
Invoice → InvoiceLineItem  
Payment  
MpesaTransaction  
Refund  
Invoice  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
facility_id  
UUID  
FK → Facility, NOT NULL  
—  
patient_id  
UUID  
FK → Patient, NOT NULL  
—  
visit_id  
UUID  
FK → Visit, NULLABLE  
—  
invoice_number  
VARCHAR(30)  
UNIQUE, NOT NULL  
—  
status  
ENUM  
NOT NULL  
open | pending_confirmation | paid | partially_paid | written_off  
subtotal  
DECIMAL(12,2)  
NOT NULL  
—  
discount  
DECIMAL(12,2)  
DEFAULT 0  
Above-threshold requires approval, BRD §6.9  
tax  
DECIMAL(12,2)  
DEFAULT 0  
—  
total  
DECIMAL(12,2)  
NOT NULL  
—  
balance  
DECIMAL(12,2)  
NOT NULL  
—  
created_by  
UUID  
FK → User, NOT NULL  
—  
Relationships  
N:1 Patient, N:1 Visit (nullable). 1:N InvoiceLineItem, 1:N Payment.  
InvoiceLineItem  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
invoice_id  
UUID  
FK → Invoice, NOT NULL  
—  
source_module  
VARCHAR(30)  
NOT NULL  
opd | laboratory | pharmacy | inpatient | ...  
source_reference_id  
UUID  
NOT NULL  
Points back to the originating record, never hand-entered  
description  
VARCHAR(255)  
NOT NULL  
—  
quantity  
INTEGER  
DEFAULT 1  
—  
unit_price  
DECIMAL(10,2)  
NOT NULL  
Locked at time of service — never retroactively repriced, BRD §6.9 edge case  
amount  
DECIMAL(12,2)  
NOT NULL  
—  
Relationships  
N:1 Invoice.  
Payment  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
invoice_id  
UUID  
FK → Invoice, NOT NULL  
—  
method  
ENUM  
NOT NULL  
cash | mpesa | card | bank | insurance  
amount  
DECIMAL(12,2)  
NOT NULL  
—  
reference  
VARCHAR(100)  
—  
—  
status  
ENUM  
NOT NULL  
pending | confirmed | failed | refunded  
received_by  
UUID  
FK → User, NULLABLE  
Cashier — null for patient-initiated mobile payments  
received_at  
TIMESTAMP  
NOT NULL  
—  
Relationships  
N:1 Invoice. 1:1 MpesaTransaction where method = mpesa.  
MpesaTransaction  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
payment_id  
UUID  
FK → Payment, UNIQUE, NOT NULL  
—  
checkout_request_id  
VARCHAR(100)  
UNIQUE, NOT NULL  
Idempotency key for the STK Push request  
mpesa_receipt_number  
VARCHAR(30)  
NULLABLE  
Populated on confirmed callback  
phone_number  
VARCHAR(20)  
NOT NULL  
—  
status  
ENUM  
NOT NULL  
requested | confirmed | failed  
callback_payload  
JSONB  
NULLABLE  
Raw Daraja callback, retained for reconciliation  
Relationships  
1:1 Payment. Processed asynchronously via Celery (Solution Spec Flow 5.7).  
Refund  
Field  
Type  
Constraints  
Description  
id  
UUID  
PK  
—  
invoice_id  
UUID  
FK → Invoice, NOT NULL  
—  
payment_id  
UUID  
FK → Payment, NOT NULL  
—  
amount  
DECIMAL(12,2)  
NOT NULL  
—  
reason  
TEXT  
NOT NULL  
—  
approved_by  
UUID  
FK → User, NOT NULL  
Accountant — never the cashier who took the payment, BRD §6.9  
approved_at  
TIMESTAMP  
NOT NULL  
—  
Relationships  
N:1 Invoice, N:1 Payment.  
## 9. Cross-Module Relationship Map
The table below is the fastest way to see how Phase 1's modules actually connect at the schema level — every row is a foreign key that crosses a module boundary, which is exactly where a migration ordering mistake or a missing index tends to surface.  
From  
To  
Cardinality  
Notes  
Patient.facility_id  
Facility.id  
N:1  
Every patient belongs to exactly one home facility  
Appointment.patient_id  
Patient.id  
N:1  
An appointment is always for one patient  
Appointment.doctor_id  
User.id  
N:1  
The assigned clinician  
QueueEntry.appointment_id  
Appointment.id  
1:1  
A queue slot exists once the patient checks in  
Visit.appointment_id  
Appointment.id  
N:1 (nullable)  
Null for walk-in/emergency visits with no prior booking  
Visit.patient_id  
Patient.id  
N:1  
A patient can have many visits over time  
Consultation.visit_id  
Visit.id  
1:1  
One active consultation per visit  
LabOrder.visit_id  
Visit.id  
N:1  
A visit can generate multiple lab orders  
LabOrder.ordered_by  
User.id  
N:1  
Must not equal LabResult.verified_by for the same order — enforced in application logic, not just the schema  
Prescription.consultation_id  
Consultation.id  
N:1  
A consultation can generate one prescription with multiple items  
DispenseRecord.batch_id  
StockBatch.id  
N:1  
Traceability from a dispensed dose back to its batch/expiry  
InvoiceLineItem.source_reference_id  
Varies (Consultation / LabOrderItem / DispenseRecord / ...)  
N:1 (polymorphic)  
Never a hand-typed charge — always traces to the record that generated it  
Payment.invoice_id  
Invoice.id  
N:1  
An invoice can be settled via multiple partial payments  
MpesaTransaction.payment_id  
Payment.id  
1:1  
Only present when Payment.method = mpesa  
## 10. Indexing & Performance Notes
Index every facility_id column — it is the first filter on nearly every query in a multi-branch-ready system (TRD §8.1).  
Composite index on Patient (facility_id, mrn) — the primary lookup path from every module.  
Composite index on Appointment (doctor_id, scheduled_at) and (department_id, scheduled_at) — powers both the doctor's daily list and the reception queue view (reference UI's Appointments panel).  
Composite index on LabResult (status, is_critical) — the critical-value alert path (TRD §3.1's <60s target) cannot afford a table scan under load.  
Composite index on Invoice (facility_id, status) — the billing dashboard and reconciliation job's primary access pattern.  
StockBatch (drug_id, expiry_date) — powers both the dispensing stock check and the expiry-alert scheduled job (BRD §6.8).  
All reporting/analytics queries (BRD §6.18 dashboards) run against the PostgreSQL read replica, never the primary — see TRD §8.1 and Solution Spec §3.2.  
Appendix A: Status Enumerations Used Across Phase 1  
Field  
Allowed Values  
Appointment.status  
scheduled, checked_in, in_consultation, completed, no_show, cancelled  
Visit.status  
in_progress, completed  
Consultation.is_draft / locked_at  
draft (is_draft=true) → finalized (locked_at set); further changes only via ConsultationAddendum  
LabOrder.status  
pending, collected, processing, completed  
LabSample.status  
collected, rejected, received  
LabResult.status  
entered, verified, amended  
Prescription.status  
pending, partially_dispensed, dispensed, cancelled  
Invoice.status  
open, pending_confirmation, paid, partially_paid, written_off  
Payment.status  
pending, confirmed, failed, refunded  
Payment.method  
cash, mpesa, card, bank, insurance  
