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
  base, `FacilityScopedManager` for query-layer facility scoping.
