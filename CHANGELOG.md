# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Added (web console — Milestone 7, in progress)
- `web/`: React 19 + TypeScript SPA scaffolded with Vite, per TRD §5.1's
  stack — React Router (permission-gated route guards), TanStack Query
  for server state, Zustand for client/auth state (persisted to
  localStorage), React Hook Form + Zod for forms, axios with a JWT
  refresh interceptor (single in-flight refresh, not one per failed
  request).
- Auth: login page wired to the real `/api/v1/auth/token/` endpoint
  (MFA code field appears reactively if the server reports one's
  needed), token refresh, sign-out. Route guards (`RequireAuth`,
  `RequirePermission`) redirect rather than render-then-block, per TRD
  §5.1 — but this is UX only; the server's `HasModulePermission` is the
  only real enforcement, unchanged.
- `GET /api/v1/auth/me/` (backend addition, not in the original
  endpoint list): the frontend needs its own effective permission set
  to gate routes/nav before rendering, and the JWT carries no custom
  claims to read it from. Exposes exactly what
  `get_effective_permission_codes()` already computes server-side — the
  same function `HasModulePermission` calls on every request — so
  client-side gating and server-side enforcement read from one source
  and can't drift apart.
- App shell: sidebar navigation (only linking modules that actually
  exist on the backend today — Patients, Appointments, OPD, Laboratory,
  Pharmacy, Billing; the Solution Spec's fuller nav list includes
  modules like Inpatients/Radiology/Insurance/Inventory/HR/Reports that
  aren't built yet, and listing them would be dead links, not a
  preview), filtered per the logged-in user's permissions.
- Patients module (first full vertical slice, proving the pattern end
  to end against the real backend): list with search, registration
  form, detail view. Verified live against the running Docker stack via
  a headless-browser walkthrough (screenshots captured) — zero browser
  console errors, MRN generation, search, and detail navigation all
  working through the real API, not mocked.
- Found and fixed live: `CORS_ALLOWED_ORIGINS` (deliberately empty by
  default — see `config/settings/base.py`'s "locked down" comment) had
  no entry for the dev server's origin, so every request from the
  browser failed the CORS preflight before ever reaching Django. Added
  `http://localhost:5173` to `backend/.env` (gitignored, dev-only) and
  documented it in `.env.example`.
- Dashboard is deliberately minimal (name + facility only) rather than
  the Solution Spec's KPI-card mockup (§7.2.1: Today's Patients, OPD
  Visits, Bed Occupancy, Revenue Today, each with a trend delta) — no
  backend aggregation/analytics endpoint exists to back those numbers,
  and Inpatients/bed data isn't built at all. Fabricating the numbers
  would be worse than an honest placeholder.
- `GET /api/v1/core/departments/` and `GET /api/v1/accounts/users/`
  (backend additions): the booking/scheduling forms need to populate
  department and doctor pickers, and neither endpoint existed — every
  prior use of these models took a UUID the caller already knew. Both
  read-only, facility-scoped, gated by the standard `HasModulePermission`
  convention (`core.department.view`, `accounts.user.view`) — same
  reasoning as `/auth/me/`: exposing already-scoped data for browsing,
  not a new authorization decision.
- Appointments module: scheduling/booking form (patient typeahead,
  department/doctor pickers, live availability, slot picker), the
  appointment list with check-in/cancel actions and status pills, and a
  **live WebSocket queue panel** (TRD §5.2/§4.4) — the first real-time
  UI element, subscribing to the same `QueueConsumer` the backend
  shipped in Milestone 2. On any `queue_update` push it invalidates the
  query cache and lets the normal refetch pull the new state, rather
  than hand-merging the pushed payload — simpler, and correct even if a
  message is missed or arrives out of order.
- Two real bugs caught live by this module, both fixed at the root
  rather than papered over in the frontend:
  - `get_available_slots()` (`apps/appointments/services.py`) built its
    candidate-slot list without deduplicating across schedule rows — two
    overlapping `DoctorSchedule` entries for the same doctor/department/
    day produced the same slot twice. Surfaced as a React
    "duplicate key" console warning during the live browser walkthrough,
    traced back to a genuine duplicate in the API response, not a
    rendering bug. Fixed by building the candidate set as a `set`, not a
    list; regression test added.
  - `.slot-button`'s CSS lost a specificity fight with the more generic
    `.form-grid button` rule (equal specificity, later in the
    stylesheet) — every slot rendered as if selected. Scoped under
    `.slot-grid` to fix; also caught only by looking at the actual
    screenshot, not by the absence of a build/lint error.
- OPD module: visit list, a walk-in "start visit" flow, and the
  consultation workspace — vitals entry, the draft clinical note
  (autosaves on blur per field), diagnosis, "Complete consultation"
  (locks it), and an addenda section that only appears once locked.
  Solution Spec §7.2.3 describes a fuller split-panel workspace
  (Investigations/Prescription/Procedures/Documents as separate
  sections); this builds the clinically load-bearing subset as one
  scrolling workspace instead — Investigations and Prescription aren't
  duplicated here since Laboratory and Pharmacy already have their own
  modules for that. Starting a visit from a specific checked-in
  appointment (the backend supports `appointment` as an optional field,
  verified in the live UAT walkthrough) isn't wired into this UI yet —
  only the walk-in-style patient/doctor/department form is; there's no
  queue-side "start visit for this patient" action to drive it from.
  Verified end-to-end live: started a visit, recorded vitals, wrote and
  saved a full clinical note, added a diagnosis, locked the
  consultation, confirmed the locked fields render disabled, and added
  a real addendum afterward — zero console errors throughout.
- Laboratory module: order list, an "Order tests" form (reachable
  standalone or, more naturally, via a new "Order labs" link on the OPD
  consultation workspace that presets the current visit), and an order
  detail page driving the full per-test lifecycle — collect sample,
  enter result, verify. Verified end-to-end live: ordered two tests
  against a real visit from inside the consultation workspace,
  collected both samples, entered both results, watched the order's own
  status move pending → processing as a pure consequence of those
  actions (no status field the UI sets directly) — zero console errors.
- Pharmacy module: a drugs-and-stock catalog screen (add drugs, add
  stock batches), prescriptions list, a "Prescribe" flow reachable from
  the OPD consultation workspace (presets the current consultation, same
  pattern as "Order labs"), and a prescription detail page driving
  dispensing per item — allergy conflicts surfaced inline before
  dispensing (not a blocking modal; the pharmacist sees it and makes the
  call, matching the backend's "flag, never a hard block" design), and
  controlled drugs requiring the elevated permission before the dispense
  form even renders. Verified end-to-end live: added a real drug and
  stock batch, prescribed it against a real consultation, dispensed it,
  watched stock decrement for real (200 → 185) and the prescription
  status flip to `dispensed` — zero console errors.
- Billing module (Milestone 7 vertical slices complete — all six Phase 1
  modules now have working screens): invoice list, and a detail page
  driving line items, payment recording (cash/card/bank/insurance),
  M-Pesa STK push with the invoice polling every 3s while
  `pending_confirmation` (the one screen with no WebSocket channel to
  subscribe to instead — polling is the only mechanism here, not a
  fallback for one that exists), payments, and refund approval.

  **A real, serious bug caught live**: approving a *partial* refund
  unconditionally flipped the original payment's status to `refunded` —
  Payment.Status has no "partially refunded" state (Data Dictionary
  §8). Since `_recompute_totals()` only counted `CONFIRMED` payments as
  "paid", that made the *entire* original payment stop counting, not
  just the refunded slice — refunding 10 of a 127.50 payment pushed the
  invoice's balance to 137.50, *more than the invoice's own total*.
  Reproduced live: paid an invoice in full via the console, refunded a
  small amount as one user, watched the balance go higher than the
  total instead of down. Fixed at the root in
  `apps/billing/services.py`: `approve_refund()` now only flips a
  payment to `refunded` once its *cumulative* refunded amount reaches
  its full value (tracked via `payment.refunds`, not a single refund's
  amount), and `RefundExceedsPaymentError` now checks against what
  actually remains refundable, not the original payment amount — so two
  partial refunds can no longer together exceed the payment either
  (that was silently possible before). `_recompute_totals()` itself
  also changed: `paid` now includes both `CONFIRMED` and `REFUNDED`
  payments (a refunded payment still represents money that was really
  received; the `Refund` row is what nets it back out), with a
  `net_paid = paid - refunded` used consistently for both `balance` and
  the open/partially-paid/paid status transitions — a fully-refunded
  invoice now correctly reopens (`OPEN`, balance = total) instead of
  showing a nonsensical inflated balance. 4 regression tests added,
  including one asserting two partial refunds together can't exceed the
  payment.

  Verified end-to-end live twice more after the fix: a same-user refund
  attempt correctly rejected with the error rendering inline (not a
  silent failure), and the identical refund succeeded when approved by
  a different (accountant) user, with the invoice balance landing on
  the correct number both times.
- Milestone 7's vertical-slice pass across all six modules is done.
  Remaining: the shared design-system extraction the TRD calls for
  (now that six modules exist, what's actually shared is knowable
  rather than guessed upfront), and Milestone 8 (the FDO Health mobile
  app) hasn't started.

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
