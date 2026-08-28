# GeoAttend — Phased Implementation Plan

> Durable, in-repo version of the implementation plan. See `PROGRESS.md` for what has actually been built so far and which decisions below have been locked in. See `docs/` for the underlying product/architecture/database/API/security/UI specifications this plan implements.

## Context

This repository starts from six detailed specification documents (`docs/PRODUCT.md`, `docs/ARCHITECTURE.md`, `docs/DATABASE.md`, `docs/API.md`, `docs/SECURITY.md`, `docs/UI.md`) describing **GeoAttend**: a web attendance system for schools combining Google OAuth, geolocation verification, and face-recognition verification, with Student/Faculty/Admin roles.

The docs are unusually implementation-ready — they already fix the stack, the full DB schema, the full REST API contract with a suggested endpoint build order (`docs/API.md` §69), and a UI build-priority order (`docs/UI.md` §63). Rather than implementing all of this in one continuous pass, the work is broken into phases that each ship something demoable (backend + frontend together), verify against explicit exit criteria, and record progress durably in `PROGRESS.md` — so a future session (or a fresh context window) can pick up exactly where things left off instead of re-deriving state from scratch.

### Key decisions locked in before Phase 0

- **Face recognition**: self-hosted, open-source (not a managed cloud face API), to keep biometric data inside our own infrastructure and match the docs' privacy-by-design principle and "modular monolith" philosophy (`docs/ARCHITECTURE.md` §35–36). Library family: **DeepFace** (pip-installable, no dlib/cmake build pain, supports strong open embeddings like ArcFace/Facenet512, includes face detection and future anti-spoofing hooks for the post-MVP liveness phase). The *exact* backend model within it is decided by a short evaluation spike at the start of Phase 3 — this mirrors how `face_profiles.model_name`/`model_version` (`docs/DATABASE.md` §31) exist specifically to make that swap safe later.
- **`AGENTS.md`**: all six docs reference this file as authoritative coding-agent guidance, but it didn't exist. It is created in Phase 0 from `docs/ARCHITECTURE.md` §37's 20 contributor rules.

## Working process

- One phase at a time. Each phase ends in something runnable/demoable (backend endpoint(s) + the frontend screen(s) that consume them), not "API done, UI later."
- After each phase: run its verification steps, update `PROGRESS.md` (what shipped, decisions locked in, what's next), then stop for review before starting the next phase.
- Within a phase, backend ships first (OpenAPI `/docs` + passing tests = "backend done" checkpoint), then frontend integrates against it.
- This phase list was validated against all six docs and reshaped from an initial 10-phase skeleton into the 12 phases below — mainly by splitting two overloaded phases and pulling security/testing infrastructure earlier instead of bolting it on at the end.

## Phase breakdown

### Phase 0 — Foundational setup
- Git init; monorepo layout: `docs/` (untouched), `frontend/` (Next.js + TS + Tailwind + TanStack Query + Zustand), `backend/` (FastAPI, layered per `docs/ARCHITECTURE.md` §12), `PLAN.md`, `PROGRESS.md`, `AGENTS.md`.
- Tooling: linting/formatting for both, `pyproject.toml`/`package.json`, pre-commit hooks.
- Postgres via Docker using a pgvector-precompiled image from the start (even though `CREATE EXTENSION vector` itself isn't needed until Phase 3 — swapping base images later is annoying); frontend/backend run natively for fast dev iteration.
- `.env.example` / `.gitignore` per `docs/SECURITY.md` §46; health-check endpoints (`GET /health`, `GET /health/db`).
- Configurability pattern (named settings module, not magic numbers) for values the docs explicitly defer (GPS accuracy cutoff, face similarity threshold, verification TTL) — actual values are tuned just-in-time in the phases that need them.
- Test framework + DB fixture strategy (pytest + transactional rollback fixtures for backend, Vitest for frontend).
- Global exception handler mapping to the `{error:{code,message}}` contract (`docs/API.md` §3.2/§52) and basic request-id logging middleware.
- Dev-mode CORS allowing `http://localhost:3000`.
- Start Google OAuth credential provisioning and Arcjet account setup now — both are external dependencies with possible approval delays.
- **Exit criteria:** both dev servers run, hit each other, Postgres is reachable with the vector extension available, `AGENTS.md`/`PLAN.md`/`PROGRESS.md` committed.

### Phase 1 — Authentication
- Google OAuth end-to-end; session mechanism: secure HttpOnly cookies (`docs/SECURITY.md` §8/§44).
- `users` table + Alembic migration; `GET /auth/me`, `POST /auth/logout`.
- Explicit role-provisioning strategy (a Google login must never imply a role per `docs/PRODUCT.md` §4/`docs/SECURITY.md` §13) — decided jointly with Phase 2's seed script (pre-seeded `users` rows keyed by email/`google_id`, since there's no admin UI yet to assign roles manually).
- Arcjet applied to `/auth/*` now — its first real consumer.
- Frontend: `/login`, route groups `(auth)`/`(student)`/`(faculty)`/`(admin)`, auth state via TanStack Query.
- **Exit criteria:** a real Google login round-trip creates/loads a `users` row with the correct pre-seeded role and establishes a session; logout works; unauthenticated requests get 401.

### Phase 2 — Academic data model + seed script
- Migrations for `institutions`, `academic_years`, `branches`, `divisions`, `subjects`, `students`, `faculty`, `classes`, `class_enrollments` per `docs/DATABASE.md` §9–19.
- Idempotent seed script (upsert by natural key — PRN / institution code), separate from Alembic — the Phase 2–8 substitute for admin CRUD UI, matching `docs/UI.md` §63. Extended later (Phase 6b) with backdated attendance history.
- `GET /students/me`, `GET /faculty/me`.
- **Exit criteria:** seed script produces a coherent institution → year → branch → division → students/faculty → classes → enrollments graph; both identity endpoints return real seeded data for a logged-in user.

### Phase 3 — Face registration
- Model spike first: a standalone script evaluating 1-2 DeepFace backend models for accuracy/speed/embedding dimension before wiring anything into the schema.
- `face_profiles` table (pgvector column, dimension from the spike) + migration; both the Postgres `vector` extension and the `pgvector-python` client type adapter.
- `POST/GET /students/me/face`; Arcjet on the face endpoint.
- Frontend: face-registration flow (camera permission → guided capture → confirmation) per `docs/UI.md` §16–18.
- Security tests: "face not registered" → 409, "cannot register another student's face."
- **Exit criteria:** a student can register a face; the embedding is stored via pgvector; re-registration replaces the profile; unauthorized attempts are rejected.

### Phase 4 — Attendance sessions (faculty side)
- `attendance_sessions` table + migration; `POST /attendance/sessions`, `GET /attendance/sessions/{id}`, `POST /attendance/sessions/{id}/end`, and the **student-facing** `GET /attendance/sessions/active` (per `docs/API.md` §18 — not faculty-only).
- Faculty authorization (owns/assigned to class) as a reusable dependency — reused in Phase 6a.
- Session-conflict rule: reject overlapping active sessions for the same class (409 `SESSION_CONFLICT`, `docs/API.md` §42).
- Frontend: faculty "Create Session" form, faculty dashboard active-session card.
- **Exit criteria:** faculty can create/end a session for an owned class; cannot touch another faculty member's session (403); overlapping sessions rejected; session appears in eligible student's active-sessions list.

### Phase 5a — Verification: location slice
- Resolves a schema gap between `docs/API.md` §26–35's verification-context state machine (`CREATED → LOCATION_VERIFIED → FACE_VERIFIED → COMPLETED/FAILED/EXPIRED`) and `docs/DATABASE.md`'s entity list (which only has the one-row-per-attempt `attendance_verification_attempts`, not a mutable in-flight state machine) — adds the needed table/columns and updates `docs/DATABASE.md`.
- `POST /attendance/sessions/{id}/verification` (create context), `POST /attendance/verifications/{id}/location` (server-authoritative distance + accuracy calc).
- Minimal student entry point into the flow (active-session card → "Continue" → location step).
- **Exit criteria:** a student can start a verification context from an eligible session and get a real server-computed distance/accuracy result; expired/ineligible sessions rejected with correct error codes.

### Phase 5b — Verification: face + complete
- `POST /attendance/verifications/{id}/face` (reusing Phase 3's model service), `POST /attendance/verifications/{id}/complete` — revalidates everything even though earlier steps already passed, per `docs/API.md` §32.
- `attendance` table + migration, including `UNIQUE(session_id, student_id)`, enforced at the DB level with graceful handling of the resulting integrity error under concurrent requests.
- Full camera-guided verification UI (`docs/UI.md` §16–21).
- Core `docs/SECURITY.md` §69 tests: duplicate marking, expired session, outside radius, missing face verification, wrong student.
- **Exit criteria:** full session → location → face → complete → attendance-created flow works end-to-end; a second attempt gets 409 `ATTENDANCE_ALREADY_MARKED`; concurrent duplicate requests still produce exactly one attendance row.

### Phase 6a — Faculty live monitoring + rich dashboards
- `GET /attendance/sessions/{id}/attendance` (live roster: present/pending/failed), search/filter by name/PRN, TanStack Query polling refetch (no WebSockets/SSE per `docs/API.md` §25).
- Rich student dashboard (attendance %, subject breakdown) and rich faculty dashboard (today's classes aggregation).
- **Exit criteria:** faculty watching an active session see present/pending/failed counts update via polling; both dashboards show real aggregated data.

### Phase 6b — History
- `GET /students/me/attendance`, `GET /students/me/attendance/summary`, `GET /students/me/classes/{id}/attendance`, faculty attendance history.
- Extend the seed script with backdated attendance rows.
- "Cannot access another user's attendance" test.
- **Exit criteria:** paginated history renders correctly for both roles; cross-user access attempts return 403/404.

### Phase 7 — Security hardening completion
- Deliberately lighter than a typical "security phase" since most of it ships incrementally per-phase already.
- Remaining: widen Arcjet coverage, rate-limit-bypass test, CORS lockdown for prod, security headers, final cookie-flag pass, `audit_logs` table + key events, consolidated regression run against the full `docs/SECURITY.md` §69 list.
- **Exit criteria:** all 8 items in `docs/SECURITY.md` §69 pass as automated tests; audit log captures the listed event types.

### Phase 8 — Reports & admin
- `GET /faculty/me/reports/attendance` reusing Phase 6b's history query/service logic (`docs/API.md` §44 discourages a separate reporting layer).
- Minimal admin CRUD only where the seed script genuinely can't substitute anymore + admin dashboard.
- **Exit criteria:** faculty reports return correct filtered/paginated data; any admin screens built are read/write-correct and role-gated.

### Phase 9 — Testing gaps + deployment prep
- Deployment-specific: hosting choice, production env vars, TLS, production CORS origin.
- One end-to-end smoke test covering login → session → location → face → attendance (`docs/ARCHITECTURE.md` §32).
- Final pass against `docs/SECURITY.md` §72's production checklist.
- **Exit criteria:** checklist fully checked off; smoke test green against a prod-like environment.

## Sequencing risks (recorded so they aren't rediscovered)
- Alembic + async SQLAlchemy commonly needs a sync-driver config for the migration runner even though the app uses `asyncpg` — handle in Phase 0.
- `pgvector` needs both the Postgres extension *and* the `pgvector-python` client type adapter.
- Google OAuth consent-screen and Arcjet account provisioning are external, potentially slow — start in Phase 0.
- Timestamp handling (UTC storage → local display) is cross-cutting frontend work from Phase 4 onward — pick the date library once, early.
- `docs/DATABASE.md` and `docs/PRODUCT.md` disagree on whether `audit_logs` is MVP or post-MVP scope — Phase 7 resolves this by just building it.

## Verification approach
- Per phase: automated tests (pytest/Vitest) plus a manual run-through of the phase's user-facing flow via the dev servers (`/docs` for API contract checks, browser for UI).
- Phase 5b and Phase 7 additionally run the specific attack-scenario tests enumerated in `docs/SECURITY.md` §69 as living regression tests.
- `PROGRESS.md` is updated at the end of every phase.
