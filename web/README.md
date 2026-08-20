# FDO Hospital MIS — Web Console

The staff-facing React SPA (Milestone 7). Serves every staff role from one
build, UI rendered conditionally by the logged-in user's permissions — see
[`docs/`](../docs/) at the repo root for the Solution Spec and TRD this is
built against.

## Stack

- React 19 + TypeScript, scaffolded with Vite
- React Router — permission-gated route guards (redirect, not
  render-then-block)
- TanStack Query for server state, Zustand for client/auth state
- React Hook Form + Zod for forms
- axios, with a JWT access/refresh interceptor

## Local development

```bash
cp .env.example .env   # points at the backend; edit if yours isn't on :8011
npm install
npm run dev
```

Requires the backend running (see `../backend/README.md` or
`../docker-compose.yml`) and `CORS_ALLOWED_ORIGINS` in `backend/.env` to
include this dev server's origin — it's empty by default (locked down,
see `config/settings/base.py`), so a fresh backend checkout needs that
added explicitly.

## Structure

```
src/lib/            api client, auth store, query client
src/components/     shared layout (sidebar, route guards)
src/pages/<module>/ one directory per backend module, each with its own
                     hooks.ts (TanStack Query hooks) and screens
src/types/          TypeScript types mirroring backend serializer shapes
```

Only modules that actually exist on the backend get a sidebar entry and a
`src/pages/` directory — see `CHANGELOG.md` for what's landed so far.
