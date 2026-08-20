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
