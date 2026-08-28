# GeoAttend — Progress Tracker

> Read this first when resuming work. It records what's actually built, what decisions are locked in, and what's next. `PLAN.md` has the full phase breakdown; `docs/` has the underlying specs.

## Status: Phase 0 complete — ready to start Phase 1

## Decisions locked in so far
- **Authentication changed from Google OAuth to GeoAttend-managed email/password auth** (2026-08-28, requested after Phase 0, before Phase 1 started). No third-party identity provider. Password hashing: **Argon2id**. Session mechanism unchanged (HttpOnly cookies). No self-service signup in the MVP — accounts are provisioned via the Phase 2 seed script (email + role + initial password), since students/faculty need institution-assigned academic identity (PRN, employee ID, etc.) a signup form can't supply. All six `docs/` files plus `PLAN.md` updated accordingly; see `docs/PRODUCT.md` §4, `docs/SECURITY.md` §5–9/§62/§65, `docs/API.md` §5–6 for the current design.
- Face recognition: self-hosted, open-source, via **DeepFace**. Exact backend model (ArcFace/Facenet512/etc.) not yet chosen — pending the Phase 3 evaluation spike. Not yet added as a dependency (deferred to Phase 3, per "don't add dependencies without justification").
- Session mechanism: secure HttpOnly cookies (planned for Phase 1, not yet implemented).
- Dev database: Docker Postgres using the `pgvector/pgvector:pg16` image (pgvector 0.8.5 confirmed available via `pg_available_extensions`, not yet `CREATE EXTENSION`'d — that's Phase 3).
- Package managers: `uv` for Python (backend), `npm` for the Next.js frontend.
- Monorepo layout: `docs/` (specs, untouched) + `frontend/` + `backend/` + root-level `PLAN.md`/`PROGRESS.md`/`AGENTS.md`.
- **Backend dev port is 8001, not the 8000 the docs use as an example** (`docs/API.md` §2) — port 8000 on this dev machine is already occupied by an unrelated process. `frontend/.env.example`'s `NEXT_PUBLIC_API_URL` reflects this. Revisit if this ever runs on a different machine where 8000 is free — either port is fine, just keep them consistent.
- Alembic uses the async-native `env.py` pattern (`AsyncEngine` + `connection.run_sync(...)`) directly against `asyncpg`, so no second sync DB driver dependency was needed — the "sequencing risk" noted in `PLAN.md` turned out to have a clean fix rather than requiring a workaround.
- pytest-asyncio is configured with a **session-scoped** event loop (`asyncio_default_fixture_loop_scope = "session"`), not the function-scoped default — the module-level SQLAlchemy async `engine` singleton doesn't tolerate a fresh loop per test (connections get pooled across closed loops → `RuntimeError: Event loop is closed`). Keep this in mind if adding new async fixtures later.

## Environment quirks discovered (not GeoAttend-specific, but relevant if this repo moves machines)
- This machine's global `~/.npmrc` points npm at a corporate (MSCI) Azure Artifacts feed whose auth token is expired, which breaks any `npm install`/`npx` for this unrelated personal project. Fixed with a project-local `.npmrc` (`registry=https://registry.npmjs.org/`) at the repo root — but note npm only reads `.npmrc` from the exact working directory, not ancestor directories, so `create-next-app`'s internal `npm install` (run from inside `frontend/`) needed `npm_config_registry=https://registry.npmjs.org/` set as an env var instead. Prefix any one-off `npm`/`npx` command with that env var if it fails with `E401` inside `frontend/`.
- Port 8000 is occupied by an unrelated pre-existing process on this dev machine — see the port-8001 decision above.

## Phase log

### Phase 0 — Foundational setup — COMPLETE
- [x] Git repository initialized (`main` branch).
- [x] `PLAN.md`, `PROGRESS.md` created at repo root.
- [x] `AGENTS.md` created from `docs/ARCHITECTURE.md` §37.
- [x] `frontend/` — Next.js 16 (App Router, Turbopack) + TypeScript + Tailwind + TanStack Query + Zustand + axios scaffolded. Zustand installed but no store created yet (nothing to hold — first store arrives with Phase 1/5a's workflow state).
- [x] `backend/` — FastAPI layered structure scaffolded (`app/{api/routes,core}`; `models/schemas/services/repositories` intentionally not created yet — no content for them until Phase 1, per `docs/ARCHITECTURE.md` §12 "don't create empty structures prematurely"), `pyproject.toml` via `uv`.
- [x] Docker Compose for Postgres (`pgvector/pgvector:pg16`), verified healthy and vector extension available.
- [x] `.env.example` (both `backend/` and `frontend/`) / `.gitignore` (root + frontend-specific, both excluding `.env*` except `.env.example`).
- [x] Health-check endpoints (`GET /api/v1/health`, `GET /api/v1/health/db`) — verified over real HTTP, not just the test client.
- [x] Settings module (`backend/app/core/config.py`) for configurable thresholds (GPS accuracy, face similarity, verification TTL) — placeholders, values TBD in the phases that need them.
- [x] Test framework: pytest + pytest-asyncio + httpx (backend, with transactional-rollback DB fixture in `tests/conftest.py`) — 2/2 tests passing. Vitest for frontend not yet added (no frontend logic worth unit-testing yet beyond the one query hook exercised manually below; add it in Phase 1 alongside the first real component).
- [x] Global exception handler → `{error:{code,message}}` contract (`backend/app/core/errors.py`); request-id logging middleware (`backend/app/core/logging.py`), confirmed `X-Request-ID` header present on real responses.
- [x] Dev CORS for `http://localhost:3000` — verified via a real preflight + credentialed GET from that origin.
- [x] End-to-end connectivity proven: `frontend` (`src/queries/use-health.ts` + `src/app/page.tsx`) fetches `backend`'s `/health` through axios/TanStack Query; frontend build + lint clean; backend ruff lint + format clean.
- [ ] Arcjet account setup — not started (needs a human to create the account/key; flagging for Phase 1 kickoff rather than blocking Phase 0 on it). Google OAuth credential provisioning is no longer needed — see the authentication decision above.

### Phase 1 — Authentication — NOT STARTED
Blocked on: an Arcjet account/key (see checklist above) — obtain this first. No longer blocked on Google OAuth credentials.
### Phase 2 — Academic data model + seed script — NOT STARTED
### Phase 3 — Face registration — NOT STARTED
### Phase 4 — Attendance sessions (faculty side) — NOT STARTED
### Phase 5a — Verification: location slice — NOT STARTED
### Phase 5b — Verification: face + complete — NOT STARTED
### Phase 6a — Faculty live monitoring + rich dashboards — NOT STARTED
### Phase 6b — History — NOT STARTED
### Phase 7 — Security hardening completion — NOT STARTED
### Phase 8 — Reports & admin — NOT STARTED
### Phase 9 — Testing gaps + deployment prep — NOT STARTED

## Known doc inconsistencies (not yet resolved in `docs/`)
- `docs/DATABASE.md` §46 lists `audit_logs` as a "potential post-MVP" entity, but `docs/PRODUCT.md` §25 lists "audit information" under MVP scope. Plan: build it in Phase 7 regardless; update `docs/DATABASE.md` to reflect this once built.
- `docs/DATABASE.md`'s entity list has no table matching `docs/API.md`'s verification-context state machine (`CREATED/LOCATION_VERIFIED/FACE_VERIFIED/COMPLETED/FAILED/EXPIRED` + `expires_at`). `attendance_verification_attempts` is close but models a completed attempt log, not in-flight state. To be resolved in Phase 5a with a `docs/DATABASE.md` update.

## Environment notes
- Verified available in the dev environment: Node v22.23.1, npm 10.9.8, Python 3.10.12, `uv` 0.11.29, Docker 29.6.1 (daemon running), Docker Compose v5.3.1, git 2.34.1, psql 14.24.

## What's next
Phase 0 is done and verified end-to-end (see checklist above). Stopped here for review per the working process in `PLAN.md`.

Before Phase 1 can start, an Arcjet account/key needs human setup (not something an agent can do) — Google OAuth is no longer part of the design, so no Google Cloud Console setup is needed. Phase 1 now implements email/password authentication end-to-end (Argon2id hashing, `/auth/login`) plus the role-provisioning strategy, and applies Arcjet to `/auth/*`.

## How to run this locally
- `docker compose up -d postgres` — starts Postgres (pgvector image) on port 5432.
- Backend: `cd backend && cp .env.example .env` (trim to just `ENVIRONMENT`/`DATABASE_URL`/`CORS_ALLOW_ORIGINS` for now — the rest are unset placeholders until later phases), then `uv run uvicorn app.main:app --port 8001`.
- Frontend: `cd frontend && cp .env.example .env.local && npm run dev -- --port 3000`.
- Backend tests: `cd backend && uv run pytest`. Lint: `uv run ruff check .` / `uv run ruff format .`.
