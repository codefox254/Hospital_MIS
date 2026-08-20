# FDO Hospital MIS

A hospital management information system built for FDO Technologies:
a Django/DRF backend, a React web console for staff, and a React Native
mobile app (FDO Health) for patients.

See [`docs/`](docs/) for the Solution Specification, Technical Requirements
Document, and Phase 1 Data Dictionary this codebase is built against — and the
note there on the currently-missing Business Requirements Document.

## Repository layout

```
backend/    Django + DRF API (modular monolith, one app per BRD module)
web/        React web console (staff-facing) — added from Milestone 7
mobile/     React Native app, FDO Health (patient-facing) — added from Milestone 8
docs/       In-repo reference documents
```

## Status

Phase 1 backend is complete (Milestones 0-6): `core`, `accounts`, `audit`,
`patients`, `appointments`, `opd`, `laboratory`, `pharmacy`, and `billing` —
the full module set the Data Dictionary defines as the minimum for a single
facility to run its day-to-day OPD operation end-to-end. See
`CHANGELOG.md` for what actually landed in each, including the deliberately
deferred integration points (no pricing catalog for OPD/Lab billing, no
notifications app yet, M-Pesa is a stub pending real Daraja credentials).
`web/` and `mobile/` (Milestones 7-8) haven't started.

## Local development

```bash
docker-compose up -d postgres redis
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt
python manage.py migrate
python manage.py runserver
```

Full pre-push check suite: see `backend/README.md`.
