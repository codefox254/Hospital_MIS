# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Added
- Repository scaffolding: monorepo layout, `.gitignore`, root `README.md`,
  in-repo Markdown copies of the Solution Spec, TRD, and Phase 1 Data
  Dictionary under `docs/`.
- `docker-compose.yml` for local development (Postgres, Redis, Django API,
  Celery worker, Celery beat).
- Django project skeleton (`backend/config`) with environment-split settings
  (base/dev/staging/production).
- `core` app: `Facility`, `Department` models, `FacilityScopedModel` abstract
  base, `FacilityScopedManager` for query-layer facility scoping, the
  standard `{"error": {...}}` API error envelope.
- `accounts` app: custom `User` model and the `Role`/`Permission`/
  `RolePermission`/`UserRole` schema implementing the `module.resource.action`
  permission engine.
- JWT authentication (`POST /api/v1/auth/token/`, `/token/refresh/`) with
  per-client-type refresh lifetimes (web 7d, mobile 30d), the
  `HasModulePermission` DRF permission class every endpoint enforces through,
  TOTP-based MFA (setup/activate/enforced-at-login) for privileged roles, and
  break-glass emergency access (`BreakGlassGrant`) with mandatory reason and
  automatic expiry.
- `audit` app: independent, append-only `AuditLogEntry` store with a
  read-only, facility-scoped query API, and the `AuditableModel` mixin
  (field-level diffing on every write, `soft_delete()`, hard `delete()`
  disabled) — wired into `Department` as its first real consumer.
- CI pipeline (`.github/workflows/backend-ci.yml`): lint, migration-drift
  check, smoke + full regression suite with an 80% coverage gate, dependency
  vulnerability scan, SAST, secrets scan, and a Docker build check that
  fails if secrets or the dev virtualenv end up baked into the image.
- Pre-commit hooks mirroring the same lint/format/security gates locally.
- Celery application bootstrap (`config/celery.py`) and a trivial
  `apps.core.tasks.ping` task proving the Celery/Redis wiring works
  end-to-end.
- `patients` app (Milestone 1): `Patient` model with server-generated MRNs
  (`register_patient()`, never client-supplied), full CRUD + search API
  scoped to the requester's facility, and a separately permission-gated
  `deactivate` action (soft delete) instead of DELETE — hard delete stays
  disabled via `AuditableModel`. `HasModulePermission` gained
  `permission_codes_by_action` so a ViewSet's custom actions (like
  `deactivate`) can require a different permission than `create` even
  though both are POST.
- `patients` app, Milestone 1 completion: `Guardian`, `EmergencyContact`,
  `Allergy`, `ChronicCondition`, `Consent`, and `PatientInsurance` — each
  scoped to its parent `Patient`, full CRUD + `deactivate` API, own
  permission codes. `AuditableModel` gained `_get_audit_facility_id()` so
  child records without their own `facility` column (these six — Data
  Dictionary §3 doesn't define one for them) resolve it through their
  parent instead of denormalizing a column the schema doesn't have.
- `appointments` app (Milestone 2): `DoctorSchedule`, `Appointment`,
  `QueueEntry`, `AppointmentReminder`, availability computation, booking
  with a real DB-level double-booking guard (`UniqueConstraint` on
  doctor+scheduled_at for active statuses, not just an app-level check),
  check-in with a live queue publish over Django Channels, and a custom
  JWT auth middleware for the WebSocket layer (the API is JWT bearer, not
  session cookies, so Channels' stock `AuthMiddlewareStack` doesn't apply).
- `opd` app (Milestone 3): `Visit`, `Vitals`, `Consultation`, `Diagnosis`,
  `ConsultationAddendum` (Data Dictionary §5; Solution Spec Flow 5.3).
  `start_visit()` creates a Visit and its empty draft Consultation
  together and, when started from a checked-in Appointment, moves it to
  `in_consultation`. Vitals/Diagnosis/Addendum are create-and-view-only —
  point-in-time clinical facts corrected by adding a new one, never by
  editing history. `complete_consultation()` locks the note (BRD §6.3:
  further changes require an addendum, never a silent edit) and closes
  out the Visit and its Appointment. Out-of-threshold vitals readings
  enqueue a notification task — currently a stub, since the dedicated
  notifications app doesn't exist yet (same gap already flagged in
  `appointments`). Dispatching Lab/Radiology/Pharmacy orders and
  generating billing line items on consultation completion (Solution Spec
  Flow 5.3 steps 4 and 6) is deliberately not done here either — those
  apps are later milestones; flagged, not silently skipped.
- `laboratory` app (Milestone 4): `LabOrder`, `LabOrderItem`, `LabSample`,
  `LabResult`, `LabResultValue` (Data Dictionary §6; Solution Spec Flow
  5.4). Order status moves pending → collected → processing → completed
  automatically as samples get collected and results get verified — no
  separate status-update endpoint, it's a consequence of the real
  actions. `verify_result()` enforces the technician/scientist separation
  of duties at the service layer (BRD §6.6: the person who entered a
  result can never also verify it) — `SelfVerificationError` if they
  match. A critical value marks the result `is_critical` at entry but the
  urgent (<60s, TRD §3.1) notification only fires on verify, matching
  Flow 5.4 step 5 — same notifications-app stub gap already flagged in
  `appointments`/`opd`.
- `pharmacy` app (Milestone 5): `Drug`, `Prescription`, `PrescriptionItem`,
  `StockBatch`, `DispenseRecord` (Data Dictionary §7; Solution Spec Flow
  5.6). `Drug` is deliberately not facility-scoped or audited — the Data
  Dictionary defines no `facility_id` for it (unlike every other model in
  this app) and `AuditLogEntry.facility` is a required FK, so it's shared
  reference-catalog data, not a per-facility clinical/financial record;
  `StockBatch` is where the real per-facility, audited inventory state
  lives. `dispense_medication()` decrements stock inside a
  `select_for_update()`-locked transaction (Flow 5.6 step 3 spells out
  "transactionally" explicitly) and tracks partial dispensing against
  `qty_prescribed` across multiple dispense events, flipping
  `Prescription.status` to `partially_dispensed`/`dispensed` as a
  consequence. `is_controlled` drugs require a separate elevated
  permission (`pharmacy.dispense_record.create_controlled`) beyond the
  base dispense permission, checked once the specific drug is known (BRD
  §6.8: gates Pharmacy Technician access) — the one place in this
  codebase where a single request's permission requirement depends on
  data resolved mid-request, not just the action name. `allergy_check`
  is a best-effort substring match against the patient's recorded
  allergies (Flow 5.6 step 2), surfaced as a flag for the pharmacist —
  explicitly not a real drug-interaction database, which is out of scope
  for this phase; final clinical judgment stays with the pharmacist.
  Flow 5.6 step 5's reorder-threshold stock-request event is not
  implemented at all (not even a stub) — Inventory & Procurement isn't a
  Phase 1 module per the Data Dictionary's own roadmap.
- `billing` app (Milestone 6, Phase 1 complete): `Invoice`,
  `InvoiceLineItem`, `Payment`, `MpesaTransaction`, `Refund` (Data
  Dictionary §8; Solution Spec Flow 5.7). Invoice numbering
  (`INV-{FACILITY}-{YEAR}-{SEQ}`) mirrors `patients.services`' MRN
  pattern exactly — server-side generation, retry-on-collision against
  the UNIQUE constraint. `get_or_create_open_invoice()` means every
  service-generating action for the same visit lands on one invoice, not
  a new one per line item. `InvoiceLineItem` has no create/update
  endpoint at all — `add_line_item()` is the only way one gets created,
  living up to the Data Dictionary's own framing that "this module never
  accepts a hand-entered charge." M-Pesa is a stub (no Daraja
  sandbox/production credentials available) but a real one:
  `initiate_mpesa_stk_push()` creates genuine, queryable Payment/
  MpesaTransaction rows a real integration would create too, and
  `process_mpesa_callback()` is idempotent against a retried callback,
  matching Flow 5.7 step 5's idempotency-key requirement, verified with a
  test that deliberately retries a callback with different (wrong) data
  and confirms it's a no-op. The callback endpoint itself is
  unauthenticated (`AllowAny`) since it's called by Safaricom's
  infrastructure, not a logged-in user — flagged in its own docstring
  that a real deployment needs real webhook auth (IP allowlisting or a
  shared secret) this stub doesn't have credentials to implement.
  `approve_refund()` enforces BRD §6.9's separation of duties (the
  cashier who took a payment can never approve its own refund) the same
  shape as laboratory's entered-by/verified-by rule. Discounts above
  `DISCOUNT_APPROVAL_THRESHOLD` require a second, distinct permission
  (`billing.invoice.discount_approve`) beyond the base discount
  permission — a placeholder threshold value, since the BRD document
  itself isn't in this repo to read the real figure from (see
  `docs/README.md`), flagged as such in the constant's own comment
  rather than presented as a real spec'd number.
  **Cross-module integration**: `pharmacy.services.dispense_medication()`
  now calls `add_line_item()` for real — `StockBatch.unit_cost` is the
  one place in the whole Phase 1 schema where genuine per-unit pricing
  data exists. OPD's consultation fee and Laboratory's per-test pricing
  are deliberately **not** wired the same way: neither `Consultation` nor
  `LabOrderItem` defines a price field anywhere in the Data Dictionary,
  and inventing one would mean charging a number the spec never
  specified — a different kind of gap than "not yet wired," flagged as
  such rather than blurred together.

### Security
- **Cross-facility IDOR in every child-resource FK field.** DRF's default
  `PrimaryKeyRelatedField` queryset is unscoped unless a view validates
  the referenced object's facility by hand; several didn't. Affected:
  all six `patients` related-entity endpoints (Guardian, EmergencyContact,
  Allergy, ChronicCondition, Consent, PatientInsurance — create and
  update), `appointments`' `DoctorSchedule` (create and update) and
  `Appointment` (update only — create was already safe), and `opd`'s
  Vitals/Diagnosis/ConsultationAddendum (create). A user could reference
  a parent object belonging to a *different facility* and it would
  validate successfully — a real cross-tenant data leak/injection path
  in a system holding clinical records. Fixed with
  `apps.core.serializers.FacilityScopedPrimaryKeyRelatedField`, applied
  at every affected field; 12 regression tests confirm cross-facility
  references now return 400. Found while building `laboratory` — its
  `LabSample.lab_order_item` field had the identical bug, which is what
  prompted auditing the rest of the codebase for the same pattern.

### Fixed
- The standard error envelope was reading an exception's *class* default
  code instead of its actual per-instance code, and separately mishandled
  `djangorestframework-simplejwt`'s differently-shaped exceptions — both
  caused API error responses to report the wrong `error.code`.
- A missing `backend/.dockerignore` was baking `.env` secrets and the dev
  `.venv` into the built Docker image.
- `drf-spectacular` schema generation crashed on the audit API because
  `get_queryset()` assumed an authenticated user during introspection.
- `docker-compose.yml` referenced a Celery app module that didn't exist yet
  (`celery -A config`) — both Celery containers were crash-looping since
  Milestone 0's first commit.
- `HasModulePermission` crashed with an uncaught 500 (instead of a clean
  405) on any HTTP method a view deliberately doesn't implement, since DRF
  checks permissions before checking whether the method is even handled.
- A serializer-level bug where `serializer.save(actor=..., ip_address=...)`
  would have silently discarded the audit actor/IP on every `PATCH`/`PUT`
  by smuggling them into `validated_data` instead of `AuditableModel.save()`'s
  real parameters — caught before merging, not after.
