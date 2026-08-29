# GeoAttend — Progress Tracker

> Read this first when resuming work. It records what's actually built, what decisions are locked in, and what's next. `PLAN.md` has the full phase breakdown; `docs/` has the underlying specs.

## Status: Phase 3 complete — verified in the browser, including a real bug found and fixed there — ready to start Phase 4

## Decisions locked in so far
- **Authentication changed from Google OAuth to GeoAttend-managed email/password auth** (2026-08-28, requested after Phase 0, before Phase 1 started). No third-party identity provider. Password hashing: **Argon2id**. Session mechanism unchanged (HttpOnly cookies). No self-service signup in the MVP — accounts are provisioned via the Phase 2 seed script (email + role + initial password), since students/faculty need institution-assigned academic identity (PRN, employee ID, etc.) a signup form can't supply. All six `docs/` files plus `PLAN.md` updated accordingly; see `docs/PRODUCT.md` §4, `docs/SECURITY.md` §5–9/§62/§65, `docs/API.md` §5–6 for the current design.
- **Face recognition finalized**: self-hosted, open-source, via **DeepFace**, model **Facenet512** (512-dim embeddings), detector **retinaface**, similarity threshold **0.30** — see the Phase 3 log below for the evaluation spike and the real dependency issues hit along the way (`tf-keras`, broken `opencv` detector backend, a latent SQLAlchemy model-registration bug).
- Session mechanism: secure HttpOnly cookies (implemented in Phase 1).
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

### Phase 1 — Authentication — COMPLETE
Arcjet explicitly skipped per instruction — `/auth/*` ships without rate limiting for now (tracked as a gap; revisit in Phase 7 or sooner).

Backend:
- [x] `app/models/user.py` — `User` model (`email` unique, `password_hash`, `name`, `profile_image_url` nullable, `role` as a `UserRole` enum → Postgres `user_role`, `is_active`, timestamps). No `google_id`.
- [x] `app/models/session.py` — `UserSession` model backing the session cookie: stores only `token_hash` (sha256 of the raw token), never the raw token. Named `UserSession` (not `Session`) to avoid clashing with `sqlalchemy.orm.Session`.
- [x] `app/core/security.py` — Argon2id password hashing (`argon2-cffi`, library defaults, not yet tuned) + session token generation/hashing helpers.
- [x] `app/core/config.py` — `session_cookie_name`, `session_ttl_seconds` (7 days); no signing secret needed since session tokens are opaque and DB-verified, not JWTs.
- [x] `app/schemas/auth.py`, `app/repositories/{user,session}_repository.py`, `app/services/auth_service.py` (`authenticate()` pays the Argon2 cost even for unknown emails via a dummy hash, so response timing doesn't leak account existence), `app/api/deps.py` (`get_current_user`), `app/api/routes/auth.py` (`POST /auth/login`, `GET /auth/me`, `POST /auth/logout`).
- [x] Alembic migration `19ffe46df3cc` — `users` + `sessions` tables, applied.
- [x] `backend/scripts/seed.py` — idempotent dev seed for 3 users (student/faculty/admin @example.com, password `password123`); Phase 2 will extend it with the full academic graph.
- [x] Tests: `tests/test_auth.py` (integration, 6 tests — login success/wrong-password/unknown-email-parity/unauthenticated/logout/inactive-user, real Postgres via the transactional-rollback fixture) + `tests/test_security.py` (unit, 4 tests — hashing/token primitives, no DB). 12/12 passing. Test emails use a `test-`/`nobody@` prefix distinct from `scripts/seed.py`'s fixture data — there's one shared dev database, not a separate test DB, so this is what actually prevents collisions (deliberate simplification, not an oversight).
- [x] Manually verified over real HTTP with cookies (not just the in-process test client): login sets the cookie, `/me` reads it, wrong password and unknown email return byte-identical `401 INVALID_CREDENTIALS`, logout clears the cookie and invalidates the session server-side.

Frontend:
- [x] `src/lib/types.ts` (`User`, `dashboardPathForRole`), `src/queries/use-current-user.ts` (treats 401 as "not logged in", not an error), `use-login.ts`, `use-logout.ts`.
- [x] `src/app/(auth)/login/page.tsx` — email/password form.
- [x] `src/components/require-role.tsx` — role guard, redirects to `/login` if unauthenticated or to the correct dashboard if the role doesn't match the section.
- [x] Real (non-parenthesized) `student/`, `faculty/`, `admin/` route segments with a guarded `layout.tsx` + placeholder `dashboard/page.tsx` each — chosen over parenthesized route groups because `docs/UI.md` §62 specifies literal `/student/dashboard` etc. URLs, which route groups wouldn't produce.
- [x] Root `page.tsx` now redirects by auth state instead of the Phase 0 health-check placeholder; the now-unused `use-health.ts` hook was deleted.
- [x] Build + lint clean.
- [x] **Manually verified in a real browser by the user**: unauthenticated `/` → `/login` redirect, login → correct dashboard, wrong password shows inline error, role guard redirects away from the wrong section, logout clears the session and going back requires logging in again.

Docs synced to match what was actually built (session mechanism is no longer "TBD"):
- [x] `docs/DATABASE.md` §8 renamed "Password Storage & Sessions", `sessions` table schema added, added to the §46 entity list.
- [x] `docs/API.md` §71 / `docs/SECURITY.md` §74 / `docs/SECURITY.md` §8: removed "exact session mechanism" from open items, pointed at the concrete implementation.

Dev tooling added (not part of the phase plan, but requested alongside it):
- [x] Root-level `scripts/{start-docker,start-backend,start-frontend}.sh` — each resolves its own paths via `dirname "$0"` so they work regardless of invocation context; `start-backend.sh` polls `docker compose exec postgres pg_isready` before starting uvicorn (`--reload` now enabled) so it doesn't race Postgres startup.
- [x] `.vscode/tasks.json` — "GeoAttend: Docker/Backend/Frontend" tasks each with `"panel": "dedicated"` (own persistent terminal, reused on rerun) + a "GeoAttend: Start All" compound task running all three in parallel. Verified by running all three scripts concurrently exactly as the tasks would.

### Phase 2 — Academic data model + seed script — COMPLETE
- [x] Models: `Institution`, `AcademicYear`, `Branch`, `Division`, `Subject`, `Student`, `Faculty`, `ClassEnrollment`, and `ClassOffering` (Python class name deliberately not `Class` — reads oddly next to the `class` keyword everywhere in the codebase; `__tablename__` stays `classes` to match every other doc/endpoint reference). Relationships used for eager loading are declared `lazy="raise"` so any accidental un-eager-loaded access fails loudly instead of silently attempting a lazy load (which breaks or N+1s under async SQLAlchemy).
- [x] Migration `883034a9022d` — all 8 new tables with the FKs/unique constraints/indexes from `docs/DATABASE.md` §9–19 and its §38 indexing recommendations, applied.
- [x] Repositories: one per entity, natural-key lookups for seed idempotency (`get_by_code`, `get_by_institution_and_code`, etc.) plus eager-loaded `get_by_user_id` for `Student`/`Faculty`.
- [x] `app/services/{student,faculty}_service.py` — `get_my_profile()`, 404 `RESOURCE_NOT_FOUND` if the authenticated user has no matching profile (e.g., an admin hitting `/students/me`).
- [x] `GET /students/me`, `GET /faculty/me` — response shapes match `docs/API.md` §10 exactly (nested `user`/`branch`/`division`/`academic_year` briefs).
- [x] `scripts/seed.py` extended: 1 institution → 1 academic year → 1 branch → 1 division → 1 subject → student/faculty profiles for the Phase 1 seed users → 1 class → 1 enrollment. Verified idempotent (re-run produces zero duplicate rows).
- [x] Tests: `tests/test_academic.py` (4 integration tests) — 16/16 total passing. Same test-email-prefix convention as Phase 1 to avoid colliding with `scripts/seed.py`'s fixture data (hit this exact collision again while writing these tests — a real footgun worth remembering, not just a one-off).
- [x] Manually verified over real HTTP against the actual seeded data: `/students/me` and `/faculty/me` return the expected nested shape; a student hitting `/faculty/me` correctly gets 404, not data leakage or a 500.
- [x] `docs/DATABASE.md` §9 updated: dropped `face_embedding_id` from the `students` schema (redundant with `face_profiles.student_id`, §28) — a deliberate simplification, not an oversight.

Deliberately deferred (not in this phase's scope, don't be surprised they're missing): `/students/me/classes`, `/faculty/me/classes` (these are API.md's own "Phase 3 — Academic data" endpoints, distinct from this project's Phase 2; they'll land naturally once something needs them — likely Phase 4), any admin CRUD UI (seed script remains the substitute through at least Phase 7 per `PLAN.md`).

### Phase 3 — Face registration — COMPLETE
- [x] **Model spike** (`backend/scripts/face_model_spike.py`): evaluated Facenet512 vs ArcFace via DeepFace (both 512-dim). Facenet512 showed much cleaner same/different-person separation (0.266 vs 1.005, threshold 0.30) than ArcFace (0.557 vs 0.930, threshold 0.68) on this small, non-rigorous test — **Facenet512 chosen**. This is a smoke-level sanity check, not the real FAR/FRR validation `docs/SECURITY.md` §27 requires before production (needs real classroom conditions/volume).
- [x] **Real dependency gotchas hit and fixed** (all documented in code comments, not just here): (1) TensorFlow 2.21's Keras-3 default breaks `retinaface` — needed the `tf-keras` compat package. (2) `opencv-python` 5.0.0 no longer bundles Haar cascade XML files, breaking DeepFace's default `opencv` detector backend — switched to `detector_backend="retinaface"` explicitly (also more accurate). (3) **A real, previously-latent bug**: `app/models/__init__.py` was empty, so models only referenced by string in a `ForeignKey()` (`Institution`, `AcademicYear`, `Branch`, `Division`, `ClassOffering`, `ClassEnrollment`) were never actually registered with SQLAlchemy in the real running app — reads worked fine, but the first real INSERT/flush needing FK-based table sorting crashed with `NoReferencedTableError`. Fixed by having `app/models/__init__.py` import every model and `app/main.py`/`alembic/env.py` both import `app.models` explicitly. This had been latent since Phase 2 (masked because tests and `scripts/seed.py` happen to import every model directly) and would have hit in Phase 4 regardless — worth remembering if a similar "works in tests, fails for real" gap shows up again.
- [x] Settings for the whole pipeline: model name, detector backend, embedding dimension (512), similarity threshold (0.30, DeepFace's own calibrated default — not yet tuned against real usage), min detection confidence (0.90), upload size/dimension limits.
- [x] `app/core/face_model.py` — `warm_up()` (loads both models once at FastAPI startup via `lifespan`, confirmed via timing: ~8.6s app startup vs. ~30-45s cold-load on first request if not pre-warmed) and `extract_embedding()` (maps DeepFace's `FaceNotDetected` and multi-face/low-confidence cases to `docs/API.md` §53 error codes).
- [x] `FaceProfile` model + migration (enables the `vector` Postgres extension and creates `face_profiles` with a `vector(512)` column) — note: pgvector's Alembic autogenerate omits the `import pgvector.sqlalchemy` line; had to add it by hand or the migration fails at import time.
- [x] `app/services/face_service.py` — validates content-type/size/decodability/dimensions (never trusts the declared MIME type, decodes via OpenCV per `docs/SECURITY.md` §40), then calls `face_model`, then upserts via `face_profile_repository` and flips `student.face_registered`.
- [x] `POST/GET /students/me/face` — response shapes match `docs/API.md` §16-17. Re-registration replaces the profile (upsert, not a new row) — verified both by a dedicated test and by hand.
- [x] `tests/fixtures/face.jpg` — a resized (31KB), MIT-licensed copy of one of DeepFace's own test images, committed so tests exercise the real detection/embedding pipeline end-to-end rather than mocking it (mocking is exactly what would hide detection/embedding regressions).
- [x] 7 new tests (23/23 total passing): register success, replace-on-re-register (scoped by `student_id` — the dev DB is shared, so an unfiltered "count all rows" assertion is wrong here, not just in theory: it broke the moment a second student's profile existed from manual testing), no-face-detected, unsupported content type, non-student caller (404), unauthenticated (401), status defaults to unregistered.
- [x] Manually verified over real HTTP end-to-end against the real seeded student, including confirming re-registration doesn't duplicate the row in Postgres directly.
- [x] Refactored `test_academic.py`'s inline fixture-building into `tests/factories.py`, now shared with `test_face.py`.

Frontend (verified by the user in their own browser — camera access can't be meaningfully automated in this sandbox: no `chromium-cli`, and the Playwright Chromium download stalled/was abandoned):
- [x] `src/components/face/camera-capture.tsx` — reusable (Phase 5b will need the same UX for live verification): explains camera use before requesting permission (`docs/UI.md` §52), live preview with an oval guide overlay, **manual capture only** — no live client-side face-detection guidance ("move closer"/"hold still" per `docs/UI.md` §17 would need its own client-side model evaluation, deliberately out of scope for this phase, not an oversight). Stops all camera tracks on unmount.
- [x] `src/app/student/face-registration/page.tsx` — capture → preview (retake/confirm) → upload → success, surfacing the backend's own error messages directly (they're already written in the plain-language style `docs/UI.md` §3.4 asks for).
- [x] `use-face-status`/`use-register-face` query/mutation hooks; student dashboard now shows a "Register your face" prompt card when unregistered.
- [x] **Verified end-to-end in the user's real browser** (camera access can't be meaningfully automated in this sandbox — no `chromium-cli`, Playwright's Chromium download stalled). Found and fixed a real bug this way that no amount of static analysis would have caught: the video preview showed solid black after granting camera permission. Root cause — a React ref-timing bug in `camera-capture.tsx`: `videoRef.current.srcObject = stream` was set *before* `setState("streaming")`, but the `<video>` element is conditionally rendered and only exists in the DOM once state is already `"streaming"` — so the assignment silently hit a `null` ref and the video element mounted with no source. Fixed by moving the `srcObject` assignment into a `useEffect` keyed on `state === "streaming"`, which runs after React has actually mounted the element; added an explicit `.play()` call too for browsers that need it after an imperative `srcObject` set. Confirmed fixed — full flow (permission → live preview → capture → confirm → success, dashboard prompt disappears afterward) now works.

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
Phase 3 is done, including in-browser verification. Stopped here for review per the working process in `PLAN.md`. Next up is Phase 4 — attendance sessions (faculty side): `attendance_sessions` table, session create/list/end endpoints, faculty authorization (a faculty member can't touch another faculty member's sessions), the student-facing "active sessions" endpoint, and the faculty "create session" UI.

## How to run this locally
**Preferred:** VS Code → Command Palette → "Tasks: Run Task" → **"GeoAttend: Start All"** (or run the three "GeoAttend: Docker/Backend/Frontend" tasks individually) — each opens its own dedicated terminal. Backed by `scripts/start-{docker,backend,frontend}.sh`; `start-backend.sh` waits for Postgres to be ready before starting uvicorn.

Manual equivalent:
- `docker compose up postgres` — starts Postgres (pgvector image) on port 5432.
- Backend: `cd backend && cp .env.example .env` (trim to just `ENVIRONMENT`/`DATABASE_URL`/`CORS_ALLOW_ORIGINS` for now), then `uv run uvicorn app.main:app --port 8001 --reload`.
- Frontend: `cd frontend && cp .env.example .env.local && npm run dev -- --port 3000`.
- Seed dev users (idempotent): `cd backend && uv run python scripts/seed.py` — creates `student@example.com` / `faculty@example.com` / `admin@example.com`, all with password `password123`.
- Backend tests: `cd backend && uv run pytest`. Lint: `uv run ruff check .` / `uv run ruff format .`.
- Frontend build/lint: `cd frontend && npm run build` / `npm run lint`.
