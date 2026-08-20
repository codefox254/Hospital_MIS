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

Milestone 0 (foundation) is in progress: project scaffolding, the `core`
(facility/department + shared base models), `accounts` (identity, RBAC, JWT
auth, MFA), and `audit` (independent audit log) Django apps. See
`CHANGELOG.md` for what has actually landed.

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
