# Backend — FDO Hospital MIS

Django + DRF modular monolith (TRD §4.1) — one app per BRD module under `apps/`.

## Local setup

```bash
docker-compose up -d postgres redis   # from repo root
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt
cp .env.example .env                  # then fill in secrets for your machine
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Pre-push check suite

Run all of this before every push (CLAUDE.md §11 Quick Reference); CI
(`.github/workflows/backend-ci.yml`) runs the same gates on every PR:

```bash
pytest -m smoke -v          # fail fast
pytest -v                   # full regression + coverage gate (≥80%)
black --check apps/ config/
isort --check apps/ config/
flake8 apps/ config/
bandit -r apps/
pip-audit -r requirements/base.txt
gitleaks detect --source .. --no-git=false
```

## App layout

Each Django app under `apps/` owns one BRD module (`core`, `accounts`,
`audit`, `patients`, ...). No app queries another app's tables directly —
cross-module access goes through that module's serializers/service layer
(TRD §3.5), even inside the monolith, to keep the future service-extraction
path open (TRD §4.5).
