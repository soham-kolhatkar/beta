# GeoAttend — System Architecture

## 1. Purpose

This document defines the technical architecture of GeoAttend.

It describes:

* System components
* Responsibilities of each component
* Communication between frontend and backend
* Authentication architecture
* Database access
* Attendance verification flow
* Face recognition architecture
* Geolocation architecture
* State management
* Security boundaries
* Deployment boundaries

This document is an architectural reference for development and should be updated whenever a significant architectural decision changes.

---

# 2. Architecture Overview

GeoAttend uses a decoupled frontend/backend architecture.

```text
                         ┌──────────────────────┐
                         │       Student        │
                         │   Mobile Browser     │
                         └──────────┬───────────┘
                                    │
                                    │ HTTPS
                                    ▼
                         ┌──────────────────────┐
                         │       Next.js        │
                         │    Web Application   │
                         │                      │
                         │ TypeScript           │
                         │ Tailwind CSS         │
                         │ TanStack Query       │
                         │ Zustand              │
                         └──────────┬───────────┘
                                    │
                                    │ HTTPS / REST
                                    ▼
                         ┌──────────────────────┐
                         │       FastAPI        │
                         │      REST API        │
                         │                      │
                         │ Authentication       │
                         │ Authorization        │
                         │ Business Logic       │
                         │ Attendance           │
                         │ Geolocation          │
                         │ Face Verification    │
                         └──────┬───────┬───────┘
                                │       │
                    ┌───────────┘       └────────────┐
                    ▼                                ▼
          ┌──────────────────┐             ┌──────────────────┐
          │   PostgreSQL     │             │  Face Processing │
          │                  │             │                  │
          │ Users            │             │ Face Detection   │
          │ Students         │             │ Embeddings       │
          │ Faculty          │             │ Verification     │
          │ Classes          │             │ Liveness*        │
          │ Sessions         │             │                  │
          │ Attendance       │             └──────────────────┘
          └──────────────────┘

                    ▲
                    │
             ┌──────┴──────┐
             │   Arcjet    │
             │             │
             │ Rate Limit  │
             │ Security    │
             └─────────────┘
```

`*` Liveness detection is a post-MVP capability.

---

# 3. Architectural Principles

## 3.1 Backend is authoritative

The frontend is never considered a trusted source for security-sensitive decisions.

The backend must independently validate:

* Authentication
* Authorization
* User role
* Session status
* Class membership
* Location
* Location accuracy
* Face verification
* Duplicate attendance

For example, the frontend must never send:

```json
{
  "locationVerified": true,
  "faceVerified": true
}
```

and expect the backend to trust those values.

Instead:

```text
Frontend
   ↓
Raw evidence
   ↓
FastAPI
   ↓
Validation
   ↓
Decision
```

---

## 3.2 Separate server state from client state

The application uses two state-management mechanisms with different responsibilities.

### TanStack Query

Responsible for server state:

* API data
* Students
* Classes
* Sessions
* Attendance
* Reports
* User profile
* Faculty data

### Zustand

Responsible only for genuine client-side state:

* UI preferences
* Temporary attendance workflow state
* Camera state
* Local navigation state
* Temporary form/workflow state

Do not duplicate API/server state inside Zustand unless there is a specific architectural reason.

---

## 3.3 Business logic belongs in FastAPI

Next.js should not implement authoritative business rules.

Incorrect:

```text
Next.js
 ├── calculate attendance eligibility
 ├── determine GPS validity
 └── decide face match
```

Correct:

```text
Next.js
 └── collect input / display result

FastAPI
 ├── validate
 ├── calculate
 ├── authorize
 └── persist
```

---

## 3.4 Database access is backend-only

The browser must never directly connect to PostgreSQL.

```text
Browser
   ↓
Next.js
   ↓
FastAPI
   ↓
SQLAlchemy
   ↓
PostgreSQL
```

---

# 4. Frontend Architecture

## 4.1 Technology

The frontend uses:

* Next.js
* React
* TypeScript
* App Router
* Tailwind CSS
* TanStack Query
* Zustand

The frontend is responsive and optimized for both mobile and desktop.

---

# 5. Next.js Responsibilities

Next.js is responsible for:

* Rendering application UI
* Routing
* User interaction
* Camera access
* Browser geolocation access
* API communication
* Client-side validation for UX
* Loading/error states
* Responsive UI
* Presenting backend results

Next.js is not responsible for authoritative:

* Authorization
* Attendance decisions
* Location verification
* Face verification
* Database operations

---

# 6. Frontend Routing

The application should use route groups to separate role-specific experiences.

Conceptual structure:

```text
app/
│
├── (auth)/
│   └── login/
│
├── (student)/
│   ├── dashboard/
│   ├── attendance/
│   ├── history/
│   └── profile/
│
├── (faculty)/
│   ├── dashboard/
│   ├── classes/
│   ├── sessions/
│   └── attendance/
│
└── (admin)/
    ├── dashboard/
    ├── students/
    ├── faculty/
    ├── classes/
    ├── subjects/
    └── reports/
```

Actual routing may evolve as the product develops.

---

# 7. Frontend Component Architecture

Components should be divided into reusable UI primitives and domain-specific components.

```text
components/
│
├── ui/
│   ├── button
│   ├── dialog
│   ├── badge
│   ├── table
│   └── ...
│
├── attendance/
│   ├── attendance-card
│   ├── attendance-status
│   ├── verification-flow
│   └── ...
│
├── location/
│   ├── location-status
│   └── ...
│
├── face/
│   ├── camera-view
│   ├── face-status
│   └── ...
│
└── dashboard/
    ├── student
    ├── faculty
    └── admin
```

Components should have a single clear responsibility.

---

# 8. TanStack Query Architecture

TanStack Query is the primary server-state layer.

Example conceptual query structure:

```text
queries/
│
├── use-current-user
├── use-student-profile
├── use-active-sessions
├── use-attendance-history
├── use-student-attendance
├── use-faculty-classes
└── use-session-attendance
```

Mutations include:

```text
use-register-face
use-create-session
use-end-session
use-mark-attendance
```

Query invalidation should be used after successful mutations where appropriate.

Example:

```text
Create attendance
       ↓
Mutation succeeds
       ↓
Invalidate session attendance
       ↓
Live attendance refreshes
```

---

# 9. Zustand Architecture

Zustand should remain intentionally small.

Potential store responsibilities:

```text
app-store
├── sidebar state
├── UI preferences
└── temporary UI state
```

Attendance-specific temporary state may include:

```text
attendance-flow-store
├── current step
├── camera status
├── location status
└── temporary verification UI state
```

Do not use Zustand as a replacement for TanStack Query.

---

# 10. Backend Architecture

FastAPI is the central application backend.

It is responsible for:

* Authentication integration
* Authorization
* User management
* Academic management
* Attendance sessions
* Attendance verification
* Geolocation calculations
* Face processing
* Database access
* Validation
* Security controls
* Audit information

---

# 11. FastAPI Layered Architecture

The backend should follow a layered structure.

```text
HTTP Request
     │
     ▼
Router
     │
     ▼
Dependency / Authentication
     │
     ▼
Schema Validation
     │
     ▼
Service
     │
     ▼
Repository / Data Access
     │
     ▼
PostgreSQL
```

The responsibilities are:

### Router

Handles:

* HTTP method
* Path
* Request/response schema
* Dependency injection

Routers should remain thin.

---

### Schema

Handles:

* Request validation
* Response serialization
* API contracts

Schemas should not contain large amounts of business logic.

---

### Service

Contains business logic.

Examples:

```text
attendance_service
location_service
face_service
session_service
user_service
```

---

### Repository

Handles database operations.

Repositories should not decide business rules.

For example:

```text
Repository:
"Find attendance for student X in session Y."

Service:
"Student already has attendance, therefore reject."
```

---

# 12. Backend Directory Structure

Target structure:

```text
backend/
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── deps.py
│   │   └── routes/
│   │       ├── auth.py
│   │       ├── users.py
│   │       ├── students.py
│   │       ├── faculty.py
│   │       ├── classes.py
│   │       ├── sessions.py
│   │       └── attendance.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── database.py
│   │
│   ├── models/
│   │
│   ├── schemas/
│   │
│   ├── services/
│   │
│   ├── repositories/
│   │
│   └── utils/
│
├── alembic/
├── tests/
├── pyproject.toml
└── alembic.ini
```

Folders should only be created when required rather than creating empty structures prematurely.

---

# 13. API Architecture

The API follows REST conventions.

Conceptual endpoint structure:

```text
/api/v1
│
├── /auth
│
├── /users
│
├── /students
│
├── /faculty
│
├── /classes
│
├── /subjects
│
├── /sessions
│
└── /attendance
```

Versioning is included from the beginning:

```text
/api/v1/...
```

This allows future API versions without immediately breaking clients.

---

# 14. API Contract Principle

The frontend and backend should communicate through explicit request/response schemas.

Example:

```text
Next.js
   │
   │ POST /api/v1/attendance/verify
   │
   │ location
   │ session ID
   │ face data
   ▼
FastAPI
   │
   ▼
Validation
   │
   ▼
Response
```

The frontend should not depend on undocumented fields.

Changes to API contracts should be documented.

---

# 15. Authentication Architecture

Google OAuth is used as the external identity provider.

Conceptual flow:

```text
Browser
   │
   ▼
Google OAuth
   │
   ▼
Authenticated Google identity
   │
   ▼
GeoAttend authentication layer
   │
   ▼
GeoAttend user
   │
   ▼
Application session
```

Google establishes identity.

GeoAttend establishes:

* Application user
* Role
* Academic association
* Permissions

---

# 16. Authorization

Authorization is enforced by FastAPI.

Conceptually:

```text
Request
  ↓
Authenticate user
  ↓
Load GeoAttend user
  ↓
Determine role
  ↓
Check permission
  ↓
Execute operation
```

Example:

```text
POST /sessions
```

requires:

```text
Authenticated
AND
role = FACULTY
```

Example:

```text
POST /attendance/mark
```

requires:

```text
Authenticated
AND
role = STUDENT
```

Additional resource-level authorization is required.

A faculty member must not automatically be able to modify sessions belonging to another faculty member.

---

# 17. PostgreSQL Architecture

PostgreSQL is the primary persistent data store.

It stores:

* Users
* Students
* Faculty
* Academic structure
* Subjects
* Classes
* Attendance sessions
* Attendance records
* Verification/audit information

PostgreSQL is accessed through:

```text
FastAPI
   ↓
SQLAlchemy 2
   ↓
asyncpg
   ↓
PostgreSQL
```

---

# 18. Database Migrations

Alembic is used for schema migrations.

The development workflow is:

```text
Modify SQLAlchemy model
        ↓
Generate migration
        ↓
Review migration
        ↓
Run migration
        ↓
Test
```

Schema changes must not rely on manually changing production databases.

---

# 19. Face Recognition Architecture

Face recognition is considered a backend capability.

Initial conceptual pipeline:

```text
Browser
   │
   │ Camera image
   ▼
FastAPI
   │
   ▼
Face detection
   │
   ▼
Face processing
   │
   ▼
Face representation
   │
   ▼
Compare with registered representation
   │
   ▼
Verification result
```

The exact face recognition model is intentionally not fixed in this document.

It must be evaluated based on:

* Recognition accuracy
* Speed
* Mobile capture quality
* CPU/memory requirements
* Deployment requirements
* Licensing
* Privacy
* Spoof resistance

---

# 20. Face Embeddings

The system should prefer storing a mathematical face representation rather than unnecessarily retaining raw photographs.

Potential architecture:

```text
Face Image
    ↓
Face Model
    ↓
Embedding
    ↓
PostgreSQL / pgvector
```

`pgvector` is a candidate technology for storing and comparing embeddings.

The final decision belongs in `DATABASE.md` after evaluating the selected model.

---

# 21. Face Verification

Face verification is a 1:1 identity verification problem.

The system should answer:

> "Does this live face correspond to the authenticated student's registered face?"

It should not initially attempt unrestricted 1:N identification across every student.

Conceptual flow:

```text
Authenticated Student
       │
       ▼
Registered embedding
       │
       │
Live face
       │
       ▼
Comparison
       │
       ▼
Similarity / distance
       │
       ▼
Threshold evaluation
       │
       ▼
Verified / rejected
```

The verification threshold must be based on the selected model and testing rather than an arbitrary value.

---

# 22. Geolocation Architecture

The browser uses the Web Geolocation API.

The frontend collects:

```text
latitude
longitude
accuracy
```

The backend receives these values.

FastAPI then:

1. Loads the attendance session.
2. Loads the session's coordinates.
3. Calculates distance.
4. Evaluates allowed radius.
5. Evaluates location accuracy.
6. Produces the authoritative location result.

Conceptually:

```text
Browser GPS
     ↓
latitude / longitude / accuracy
     ↓
FastAPI
     ↓
Distance calculation
     ↓
Radius validation
     ↓
Location result
```

The frontend may show a preliminary result for UX, but the backend remains authoritative.

---

# 23. Attendance Verification Architecture

Attendance verification combines multiple independent checks.

```text
                    Attendance Request
                           │
                           ▼
                  Authentication
                           │
                           ▼
                    Session Valid?
                           │
                           ▼
                    Class Member?
                           │
                           ▼
                    Location Valid?
                           │
                           ▼
                    Face Valid?
                           │
                           ▼
                    Duplicate?
                           │
                           ▼
                  Create Attendance
```

All required checks must succeed.

---

# 24. Transaction Boundary

Attendance creation should be treated as a controlled database operation.

Conceptually:

```text
BEGIN TRANSACTION

Validate attendance conditions

Check duplicate

Create attendance

COMMIT
```

If a required operation fails:

```text
ROLLBACK
```

Database constraints must provide a final defense against duplicate attendance.

---

# 25. Duplicate Protection

The database must enforce uniqueness:

```text
UNIQUE(session_id, student_id)
```

The service layer should also check for existing attendance before attempting insertion.

This gives us two layers:

```text
Service-level prevention
        +
Database-level guarantee
```

---

# 26. Arcjet Security Layer

Arcjet is used for rate limiting and relevant application security controls.

Conceptually:

```text
Request
   ↓
Arcjet security checks
   ↓
FastAPI endpoint
```

High-cost and abuse-sensitive endpoints receive particular attention:

```text
Authentication
Face registration
Face verification
Attendance verification
Attendance marking
```

The exact Arcjet integration will follow the current official SDK/API documentation during implementation.

---

# 27. Attendance Request Security

Attendance endpoints should not rely solely on a session cookie or token.

The backend should independently validate:

* User identity
* Session
* Student enrollment
* Session state
* Time
* Location
* Face verification
* Duplicate state

This prevents a valid authenticated user from simply calling an attendance endpoint with manipulated parameters.

---

# 28. Auditability

Attendance is a security-sensitive operation.

The system should retain enough information to answer:

> "Why was this attendance accepted or rejected?"

Potential audit information:

```text
student
session
timestamp

reported latitude
reported longitude
GPS accuracy
calculated distance

face verification result
face similarity/confidence

verification status
```

The exact audit schema will be defined in `DATABASE.md`.

---

# 29. Privacy Architecture

The system should follow data minimization.

### Location

Collect primarily when required for attendance verification.

Do not continuously track students by default.

### Face data

Prefer embeddings/representations over unnecessary raw image storage.

### Access

Role-based access must restrict sensitive data.

### Logs

Logs must not unnecessarily expose:

* Face images
* Authentication secrets
* OAuth tokens
* Database credentials
* Sensitive personal information

---

# 30. Error Handling

The backend should return consistent API errors.

Conceptual response:

```json
{
  "error": {
    "code": "SESSION_EXPIRED",
    "message": "This attendance session has ended."
  }
}
```

Error codes should be stable enough for the frontend to handle them.

The frontend should convert technical errors into useful user-facing messages.

Example:

```text
Backend:
LOCATION_OUTSIDE_RADIUS

Frontend:
"You're outside the attendance area.
Move closer to the classroom and try again."
```

---

# 31. Observability

The application should eventually include:

* Structured backend logging
* Request IDs
* Error tracking
* Health checks
* Database connectivity checks

Health endpoints may include:

```text
GET /health
GET /health/db
```

Sensitive data must not be written to logs.

---

# 32. Testing Architecture

Testing should exist at multiple levels.

### Backend unit tests

Test:

* Distance calculations
* Session validation
* Attendance eligibility
* Authorization
* Business rules

### Backend integration tests

Test:

* API + database
* Authentication flow
* Attendance creation
* Duplicate protection

### Frontend tests

Test:

* Critical components
* Attendance workflow
* Error states
* Role-specific rendering

### End-to-end tests

Eventually test:

```text
Login
→ Session
→ Location
→ Verification
→ Attendance
```

---

# 33. Development Environments

The project should support at least:

```text
Development
Production
```

Potential future environment:

```text
Staging
```

Development services:

```text
Next.js
FastAPI
PostgreSQL
```

Production architecture will be finalized after deployment requirements are known.

---

# 34. Deployment Boundary

The system is intentionally split into independently deployable components:

```text
Frontend
    ↓
Next.js deployment

Backend
    ↓
FastAPI deployment

Database
    ↓
Managed PostgreSQL
```

The face-processing workload may remain part of FastAPI initially.

If computational requirements become significant, it can later be separated into an independent service.

---

# 35. Architecture Evolution

The architecture should evolve based on actual requirements and measured bottlenecks.

Do not prematurely introduce:

* Microservices
* Message queues
* Redis
* Kubernetes
* Multiple databases
* Dedicated face-processing clusters

unless the project actually requires them.

The initial architecture should remain a modular monolith:

```text
Next.js
   +
FastAPI
   +
PostgreSQL
```

This gives us clear boundaries without unnecessary infrastructure complexity.

---

# 36. Initial Architecture Decision

The initial system is therefore:

```text
┌──────────────────────────────────────────────┐
│                  FRONTEND                    │
│                                              │
│ Next.js + TypeScript + Tailwind              │
│ TanStack Query + Zustand                     │
│                                              │
└──────────────────────┬───────────────────────┘
                       │
                       │ HTTPS / REST
                       ▼
┌──────────────────────────────────────────────┐
│                  BACKEND                     │
│                                              │
│ FastAPI                                      │
│ ├── Auth                                     │
│ ├── Authorization                             │
│ ├── Academic management                       │
│ ├── Sessions                                  │
│ ├── Attendance                                │
│ ├── Location verification                     │
│ └── Face verification                         │
│                                              │
└───────────────┬─────────────────┬────────────┘
                │                 │
                ▼                 ▼
       ┌────────────────┐  ┌──────────────────┐
       │  PostgreSQL    │  │ Face Processing  │
       │                │  │                  │
       │ SQLAlchemy 2   │  │ Model            │
       │ asyncpg        │  │ Embeddings       │
       │ Alembic        │  │ Verification     │
       └────────────────┘  └──────────────────┘

                ▲
                │
          ┌────────────┐
          │  Arcjet    │
          │  Security  │
          └────────────┘
```

---

# 37. Architectural Rules for Contributors

Any developer or coding agent working on GeoAttend must follow these rules:

1. Do not bypass FastAPI for database access.
2. Do not put authoritative business logic in Next.js.
3. Do not trust frontend verification flags.
4. Do not use Zustand as an API cache.
5. Use TanStack Query for server state.
6. Use SQLAlchemy 2.x patterns.
7. Use Alembic for database schema changes.
8. Keep routers thin.
9. Put business logic in services.
10. Keep database operations in repositories/data-access modules where appropriate.
11. Validate authorization on the backend.
12. Enforce important invariants at the database level.
13. Do not introduce unnecessary infrastructure.
14. Do not add dependencies without justification.
15. Update architecture documentation when significant decisions change.
16. Never commit secrets.
17. Do not store sensitive data in logs.
18. Prefer small, focused modules over large files.
19. Add tests for important business rules.
20. Preserve backward compatibility when modifying established API contracts unless a breaking change is intentional and documented.

---

# 38. Current Implementation Status

The project is currently in the architecture/design phase.

Completed:

* Repository created
* Next.js project initialized
* FastAPI project initialized
* Product requirements documented

Not yet finalized:

* Database schema
* Exact API contracts
* OAuth implementation
* Face recognition model
* Face embedding storage
* UI design system
* Deployment provider
* Production infrastructure

These decisions should be finalized in the appropriate documentation before their implementation.

---

# 39. Related Documentation

This document should be read together with:

* `PRODUCT.md` — Product requirements
* `DATABASE.md` — Database schema and persistence
* `UI.md` — UI/UX system and research
* `SECURITY.md` — Detailed security model
* `API.md` — API contracts
* `AGENTS.md` — Coding-agent instructions

Not all supporting documents need to exist immediately. They should be created as the corresponding architecture is finalized.
