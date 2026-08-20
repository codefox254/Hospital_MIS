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

### Fixed
- The standard error envelope was reading an exception's *class* default
  code instead of its actual per-instance code, and separately mishandled
  `djangorestframework-simplejwt`'s differently-shaped exceptions — both
  caused API error responses to report the wrong `error.code`.
- A missing `backend/.dockerignore` was baking `.env` secrets and the dev
  `.venv` into the built Docker image.
- `drf-spectacular` schema generation crashed on the audit API because
  `get_queryset()` assumed an authenticated user during introspection.
