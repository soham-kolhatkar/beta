# GeoAttend — Coding-Agent Instructions

This file is referenced by all documents in `docs/` as authoritative guidance for anyone (human or AI agent) implementing GeoAttend. It did not exist when this repository contained only specs; it is created here to close that gap.

Read `PROGRESS.md` first to see what's already built and which decisions are locked in. Read `PLAN.md` for the phase-by-phase roadmap. Read the relevant files in `docs/` for the specification of whatever you're about to touch.

## Architectural rules (from `docs/ARCHITECTURE.md` §37)

1. Do not bypass FastAPI for database access.
2. Do not put authoritative business logic in Next.js.
3. Do not trust frontend verification flags (`locationVerified`, `faceVerified`, etc.) — the backend independently re-derives every security-sensitive decision.
4. Do not use Zustand as an API cache.
5. Use TanStack Query for server state.
6. Use SQLAlchemy 2.x patterns.
7. Use Alembic for database schema changes.
8. Keep routers thin.
9. Put business logic in services.
10. Keep database operations in repositories/data-access modules where appropriate.
11. Validate authorization on the backend.
12. Enforce important invariants at the database level (e.g. `UNIQUE(session_id, student_id)`).
13. Do not introduce unnecessary infrastructure (no premature microservices, queues, Redis, Kubernetes, multiple databases).
14. Do not add dependencies without justification.
15. Update architecture documentation (`docs/`) when significant decisions change.
16. Never commit secrets.
17. Do not store sensitive data in logs (tokens, face images/embeddings, passwords, auth headers).
18. Prefer small, focused modules over large files.
19. Add tests for important business rules.
20. Preserve backward compatibility when modifying established API contracts unless a breaking change is intentional and documented.

## Working conventions for this repository

- Before implementing or changing an endpoint, check `docs/API.md` for the existing contract; update it if the contract changes (`docs/API.md` §70).
- Follow the phase order in `PLAN.md`. Don't jump ahead to a later phase's scope even if it seems convenient.
- After finishing a phase's work, update `PROGRESS.md`: what shipped, any decisions locked in, what's next. This is the persistence mechanism across sessions — don't skip it.
- Errors follow the `{"error": {"code": "...", "message": "..."}}` contract (`docs/API.md` §52) — never leak stack traces or internal exception text to clients.
- All timestamps are stored in UTC; convert to local time only in the frontend.
- Coordinates, thresholds (GPS accuracy cutoff, face similarity threshold, verification TTL) live in backend settings/config, never as inline magic numbers.
