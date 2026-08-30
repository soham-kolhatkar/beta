# GeoAttend — Database Design

## 1. Purpose

This document defines the PostgreSQL database architecture for GeoAttend.

It specifies:

* Entities
* Relationships
* Primary keys
* Foreign keys
* Constraints
* Indexes
* Enums
* Face embedding storage
* Attendance data
* Audit data
* Data integrity rules
* Migration principles

The database is accessed only through the FastAPI backend.

---

# 2. Database Technology

GeoAttend uses:

* PostgreSQL
* SQLAlchemy 2.x
* asyncpg
* Alembic

Architecture:

```text
FastAPI
   ↓
SQLAlchemy 2.x
   ↓
asyncpg
   ↓
PostgreSQL
```

Database schema changes must be managed through Alembic migrations.

---

# 3. Database Design Principles

The database should prioritize:

1. Data integrity
2. Referential integrity
3. Clear relationships
4. Appropriate normalization
5. Useful indexes
6. Database-level enforcement of critical invariants
7. Minimal duplication
8. Privacy-conscious storage
9. Query performance
10. Easy future migration

Business logic should remain primarily in the application layer, while critical invariants should also be enforced at the database level.

---

# 4. High-Level Entity Relationship

The initial conceptual model is:

```text
Institution
    │
    ├── Academic Years
    │
    ├── Branches
    │
    ├── Subjects
    │
    ├── Users
    │     ├── Students
    │     └── Faculty
    │
    └── Classes
          │
          ├── Faculty
          ├── Students
          └── Subject
                 │
                 └── Attendance Sessions
                         │
                         └── Attendance
```

A more detailed relationship:

```text
                         ┌──────────────┐
                         │ Institution  │
                         └──────┬───────┘
                                │
             ┌──────────────────┼───────────────────┐
             │                  │                   │
             ▼                  ▼                   ▼
      Academic Year          Branch             Subject
             │                  │
             │                  ▼
             │               Division
             │                  │
             │                  ▼
             │              Students
             │                  │
             │                  │
             │            Enrollment
             │                  │
             └──────────┐       │
                        ▼       ▼
                         Class
                           │
                   ┌───────┴────────┐
                   │                │
                Faculty          Subject
                   │
                   ▼
            Attendance Session
                   │
                   ▼
              Attendance
                   │
                   ▼
                Student
```

The final physical schema may normalize some of these relationships further.

---

# 5. UUID Strategy

Application entities should use UUIDs as primary keys.

Recommended:

```text
UUID
```

instead of sequential integer IDs for externally exposed entities.

Reasons:

* Avoid predictable resource IDs
* Easier distributed generation
* Safer public API identifiers
* Better separation between internal ordering and identity

Example:

```text
user.id
student.id
faculty.id
class.id
session.id
attendance.id
```

should use UUIDs.

Database-generated UUIDs or application-generated UUIDs may be used consistently.

---

# 6. User Entity

The `users` table represents application identities.

Conceptual schema:

```text
users
────────────────────────────
id                  UUID PK
email               VARCHAR UNIQUE
password_hash       VARCHAR
name                VARCHAR
profile_image_url   TEXT NULL
role                USER_ROLE
is_active           BOOLEAN
created_at          TIMESTAMP
updated_at          TIMESTAMP
```

`profile_image_url` is optional and not automatically populated (there is no OAuth provider supplying an avatar); it remains `NULL` unless a profile-photo feature is added later.

---

# 7. User Role

Initial roles:

```text
STUDENT
FACULTY
ADMIN
```

A PostgreSQL enum or equivalent constrained representation may be used.

The role determines the user's broad application permissions.

Fine-grained resource authorization must still be performed by FastAPI.

---

# 8. Password Storage & Sessions

`email` is the primary identity key used to look up a user at login (there is no external identity provider to supply a separate stable ID).

Recommended constraint:

```text
UNIQUE(email)
```

The application should normalize emails (e.g. lowercase) before enforcing uniqueness and before lookup at login.

`password_hash` must never store a plaintext password. Store only the output of a strong, salted password-hashing algorithm — **Argon2id** is the recommended default (OWASP's current first choice); bcrypt is an acceptable fallback if Argon2id is unavailable in a given environment. Verification must use the hashing library's own constant-time comparison, never a manual string comparison. See `docs/SECURITY.md` for the full authentication threat model.

## Sessions

The session mechanism (previously left open as "not yet finalized") is a server-side, DB-backed session, not a JWT:

```text
sessions
────────────────────────────
id                  UUID PK
user_id             UUID FK → users.id
token_hash          VARCHAR UNIQUE
expires_at          TIMESTAMP
created_at          TIMESTAMP
```

The raw session token is a high-entropy random value (32 bytes, URL-safe) set as an `HttpOnly` cookie. Only its SHA-256 hash (`token_hash`) is stored — never the raw token — so a database leak doesn't hand out directly usable sessions, the same principle as password hashing. Logout deletes the row by `token_hash`; expiration is checked (and the row lazily deleted) on read. This gives trivial, immediate revocation without needing a JWT blocklist or an additional infrastructure dependency like Redis, consistent with the "modular monolith" principle in `docs/ARCHITECTURE.md` §35.

---

# 9. Student Entity

The `students` table contains student-specific information.

Conceptual schema:

```text
students
────────────────────────────
id                  UUID PK
user_id             UUID FK → users.id UNIQUE
prn                 VARCHAR UNIQUE
roll_number         VARCHAR
branch_id           UUID FK
division_id         UUID FK
academic_year_id    UUID FK
face_registered     BOOLEAN
created_at          TIMESTAMP
updated_at          TIMESTAMP
```

`face_embedding_id` from earlier drafts of this schema is intentionally omitted: it would only duplicate the relationship `face_profiles.student_id` already provides (§28), one-directionally, with no query this table needs that the reverse lookup doesn't already serve. `face_registered` is populated starting in Phase 3.

The student profile is separate from the generic user profile.

Relationship:

```text
users
  │
  │ 1:1
  ▼
students
```

---

# 10. Faculty Entity

The `faculty` table contains faculty-specific information.

Conceptual schema:

```text
faculty
────────────────────────────
id                  UUID PK
user_id             UUID FK → users.id UNIQUE
employee_id         VARCHAR UNIQUE
department          VARCHAR
created_at          TIMESTAMP
updated_at          TIMESTAMP
```

Relationship:

```text
users
  │
  │ 1:1
  ▼
faculty
```

---

# 11. Institution

The initial application is designed around educational institutions.

Conceptual schema:

```text
institutions
────────────────────────────
id                  UUID PK
name                VARCHAR
code                VARCHAR UNIQUE
created_at          TIMESTAMP
updated_at          TIMESTAMP
```

All academic entities should be associated with an institution where appropriate.

This makes future multi-institution support possible without redesigning the entire schema.

---

# 12. Academic Year

Academic years represent institutional academic periods.

Example:

```text
2026-27
```

Schema:

```text
academic_years
────────────────────────────
id                  UUID PK
institution_id      UUID FK
name                VARCHAR
start_date          DATE
end_date            DATE
is_active           BOOLEAN
created_at          TIMESTAMP
```

Constraint:

```text
UNIQUE(institution_id, name)
```

---

# 13. Branch

Examples:

```text
Computer Science
Information Technology
Artificial Intelligence
Electronics
Mechanical
```

Schema:

```text
branches
────────────────────────────
id                  UUID PK
institution_id      UUID FK
name                VARCHAR
code                VARCHAR
created_at          TIMESTAMP
```

Constraint:

```text
UNIQUE(institution_id, code)
```

---

# 14. Division

Divisions belong to an academic context.

Example:

```text
CSAI
 ├── A
 ├── B
 └── C
```

Schema:

```text
divisions
────────────────────────────
id                  UUID PK
institution_id      UUID FK
branch_id           UUID FK
academic_year_id    UUID FK
name                VARCHAR
created_at          TIMESTAMP
```

Recommended constraint:

```text
UNIQUE(
    branch_id,
    academic_year_id,
    name
)
```

This prevents duplicate divisions within the same academic context.

---

# 15. Subject

Subjects are institution-level academic subjects.

Schema:

```text
subjects
────────────────────────────
id                  UUID PK
institution_id      UUID FK
name                VARCHAR
code                VARCHAR
created_at          TIMESTAMP
updated_at          TIMESTAMP
```

Constraint:

```text
UNIQUE(institution_id, code)
```

---

# 16. Class

A `class` represents a specific teaching relationship between:

* Academic context
* Subject
* Faculty

For example:

```text
CSAI
Division A
Third Year
DBMS
Prof. XYZ
```

Conceptual schema:

```text
classes
────────────────────────────
id                  UUID PK
institution_id      UUID FK
subject_id          UUID FK
faculty_id          UUID FK
division_id         UUID FK
academic_year_id    UUID FK
name                VARCHAR
created_at          TIMESTAMP
updated_at          TIMESTAMP
```

The exact naming of this entity may later be changed to `course_offering` or `class_offering` if that better reflects the domain.

---

# 17. Why Class Is Separate From Subject

A subject is not the same thing as a class.

For example:

```text
Subject:
Database Management Systems
```

may have:

```text
CSAI-A → Prof. A
CSAI-B → Prof. B
CSAI-C → Prof. C
```

Therefore:

```text
Subject
   │
   ├── Class Offering A
   ├── Class Offering B
   └── Class Offering C
```

This distinction is important for attendance.

---

# 18. Student Enrollment

Students should not be directly attached to a class using a single `student.class_id`.

A student may attend multiple subjects.

Therefore use an enrollment/registration table.

```text
class_enrollments
────────────────────────────
id                  UUID PK
class_id            UUID FK
student_id          UUID FK
created_at          TIMESTAMP
```

Constraint:

```text
UNIQUE(class_id, student_id)
```

This gives:

```text
Student
   │
   ├── DBMS
   ├── Operating Systems
   ├── AI
   └── Computer Networks
```

without duplicating student records.

---

# 19. Faculty Assignment

Initially, a class has one responsible faculty member.

Therefore:

```text
classes.faculty_id
```

can reference:

```text
faculty.id
```

If future requirements support:

* Co-teaching
* Multiple faculty
* Teaching assistants

then this can be changed to:

```text
class_faculty
```

without changing attendance fundamentally.

---

# 20. Attendance Session

An attendance session represents a specific attendance opportunity.

Schema:

```text
attendance_sessions
────────────────────────────
id                  UUID PK
class_id            UUID FK
faculty_id          UUID FK

latitude            NUMERIC
longitude           NUMERIC
radius_meters       NUMERIC

starts_at           TIMESTAMP
ends_at             TIMESTAMP

status              SESSION_STATUS
ended_at            TIMESTAMP (nullable)

created_at          TIMESTAMP
updated_at          TIMESTAMP
```

`ended_at` is a Phase 4 implementation addition, not in the original spec: `POST /attendance/sessions/{id}/end`'s response (§22) returns it, so it needs to be a real column rather than derived. There is no background job transitioning an expired-but-not-explicitly-ended `ACTIVE` session to `ENDED`; code that needs to know whether a session can currently accept attendance checks `status == ACTIVE` *and* that `now` falls within `[starts_at, ends_at)`, not `status` alone.

---

# 21. Session Status

Initial statuses:

```text
CREATED
ACTIVE
ENDED
```

An `ACTIVE` session can accept attendance.

A `CREATED` session is not yet accepting attendance.

An `ENDED` session cannot accept attendance.

Expired sessions should transition logically to an inactive/ended state.

---

# 22. Session Location

Each attendance session stores the location where attendance is expected.

Required values:

```text
latitude
longitude
radius_meters
```

The location represents the faculty's selected classroom/attendance location.

The student location is not stored as the permanent session location.

---

# 23. Student Location

When attendance is attempted, the student sends:

```text
latitude
longitude
accuracy
```

The system may retain the submitted location and derived values in attendance/audit data where justified.

This allows the system to answer:

> "Where was the student when attendance was marked?"

However, continuous location tracking is explicitly out of scope.

---

# 24. Attendance Entity

Attendance represents a successful or recorded attendance attempt.

Conceptual schema:

```text
attendance
────────────────────────────
id                  UUID PK

session_id          UUID FK
student_id          UUID FK

marked_at           TIMESTAMP

latitude            NUMERIC
longitude           NUMERIC
location_accuracy   NUMERIC
distance_meters     NUMERIC

face_verified       BOOLEAN
face_score          NUMERIC NULL

status              ATTENDANCE_STATUS

created_at          TIMESTAMP
```

---

# 25. Duplicate Attendance Constraint

This is one of the most important database constraints.

```text
UNIQUE(session_id, student_id)
```

A student can therefore have only one attendance record per session.

This must be enforced by PostgreSQL.

Application-level checks alone are insufficient because concurrent requests could bypass them.

---

# 26. Attendance Status

Initial status:

```text
PRESENT
```

Additional statuses may be introduced only when there is a real business requirement.

Possible future statuses:

```text
ABSENT
MANUALLY_ADJUSTED
REVOKED
```

Verification failures should not automatically be stored as attendance records unless the product requires failed-attempt auditing.

---

# 27. Verification Attempts

For stronger auditing and fraud detection, verification attempts may eventually be separated from successful attendance.

Potential table:

```text
attendance_verification_attempts
────────────────────────────────────
id
session_id
student_id

attempted_at

latitude
longitude
location_accuracy
distance_meters

location_result
face_result
face_score

failure_reason

created_at
```

This allows us to distinguish:

```text
Attempt
    ≠
Attendance
```

This table is optional for the initial MVP but strongly recommended if anti-fraud requirements become significant. It remains unbuilt — not needed to implement the verification flow below, and still deferred to whenever anti-fraud auditing becomes a real requirement.

---

# 27a. Verification Context (Phase 5a)

`docs/API.md` §26-35 defines a verification-context state machine
(`CREATED → LOCATION_VERIFIED → FACE_VERIFIED → COMPLETED/FAILED/EXPIRED`,
with its own `expires_at`) that the table above doesn't model — that one is
an audit log of *completed* attempts, not a mutable in-flight context. This
is the table that backs `POST /attendance/sessions/{id}/verification` and
the `/attendance/verifications/{id}/*` step endpoints:

```text
attendance_verifications
────────────────────────────────────
id                          UUID PK
session_id                  UUID FK -> attendance_sessions.id
student_id                  UUID FK -> students.id

status                      VERIFICATION_STATUS
expires_at                  TIMESTAMP

location_latitude           NUMERIC (nullable)
location_longitude          NUMERIC (nullable)
location_accuracy_meters    NUMERIC (nullable)
location_distance_meters    NUMERIC (nullable)

failure_reason               VARCHAR (nullable)

created_at                  TIMESTAMP
updated_at                  TIMESTAMP
```

Face-step columns (result, similarity score, etc.) are deliberately not
included yet — Phase 5b adds them when it builds that step, rather than
adding unused columns now. A row is created once per `POST .../verification`
call and updated in place as steps complete; resubmitting the location step
(e.g. after `LOCATION_ACCURACY_TOO_LOW`) overwrites the same row rather than
creating a new one — `attendance_verification_attempts` above is the
separate, still-unbuilt place a per-attempt audit trail would eventually
live.

---

# 28. Face Data Architecture

Face data should be separated from the main student record.

Rather than storing:

```text
students.face_embedding
```

directly, prefer a dedicated entity:

```text
face_profiles
────────────────────────────
id                  UUID PK
student_id          UUID FK UNIQUE
embedding           VECTOR(...)
model_name          VARCHAR
model_version       VARCHAR
created_at          TIMESTAMP
updated_at          TIMESTAMP
```

This gives us the ability to change models later.

For example:

```text
Student
   │
   ▼
Face Profile
   │
   ├── Model: Model A
   ├── Version: 1
   └── Embedding
```

---

# 29. pgvector

`pgvector` is the preferred candidate for face embeddings if the selected face model produces vector embeddings compatible with it.

Conceptually:

```text
face_profiles
────────────────────────────
id
student_id
embedding VECTOR
model_name
model_version
```

Benefits:

* Native vector storage
* Similarity operations
* PostgreSQL integration
* Avoids introducing another database
* Future support for vector search

However, the exact vector dimension must be determined by the selected face model.

Do not hardcode an embedding dimension until the model is finalized.

---

# 30. Face Embedding Strategy

The system is initially a **1:1 verification system**, not a global face-identification system.

Therefore the expected query is:

```text
Authenticated Student
        ↓
Retrieve student's face profile
        ↓
Compare live face embedding
        ↓
Verification result
```

We do not need to search every student's embedding for every attendance attempt.

This reduces complexity and improves privacy.

---

# 31. Face Model Versioning

The stored face profile should include:

```text
model_name
model_version
```

Reason:

If the system changes from:

```text
Model A v1
```

to:

```text
Model B v2
```

existing embeddings may need to be regenerated.

Model metadata allows the system to identify which embeddings require migration.

---

# 32. Face Profile Constraints

Recommended:

```text
UNIQUE(student_id)
```

A student should have one active face profile in the MVP.

Future versions may support multiple embeddings if required.

---

# 33. Audit Logs

Built in Phase 7 (resolving the MVP-vs-post-MVP inconsistency between this section and `docs/PRODUCT.md` §25 — see `PROGRESS.md`). Security-sensitive administrative actions are auditable.

Table (built as specified below, exactly):

```text
audit_logs
────────────────────────────
id
user_id
action
entity_type
entity_id
metadata
created_at
```

Examples:

```text
FACULTY_CREATED_SESSION
FACULTY_ENDED_SESSION
ADMIN_CHANGED_STUDENT
ADMIN_CHANGED_ENROLLMENT
ATTENDANCE_MANUALLY_ADJUSTED
FACE_PROFILE_UPDATED
```

Audit metadata should not contain raw face images, session tokens, passwords or password hashes, or unnecessary sensitive information.

---

# 34. Timestamps

All persisted timestamps should be stored in UTC.

Examples:

```text
created_at
updated_at
starts_at
ends_at
marked_at
```

The frontend converts timestamps into the user's local timezone for display.

This prevents timezone-related inconsistencies.

---

# 35. Soft Deletion

Do not automatically add `deleted_at` to every table.

Soft deletion should only be used where historical records must remain while the entity becomes inactive.

For example:

```text
users.is_active
```

may be sufficient for user deactivation.

Attendance records should generally not be physically deleted casually because they represent historical records.

---

# 36. Foreign Key Strategy

Foreign keys should be used consistently.

Examples:

```text
students.user_id → users.id
faculty.user_id → users.id

classes.subject_id → subjects.id
classes.faculty_id → faculty.id
classes.division_id → divisions.id

class_enrollments.class_id → classes.id
class_enrollments.student_id → students.id

attendance_sessions.class_id → classes.id
attendance_sessions.faculty_id → faculty.id

attendance.session_id → attendance_sessions.id
attendance.student_id → students.id
```

---

# 37. Delete Behavior

Cascade deletes must be used carefully.

### Attendance

Attendance records should not disappear merely because a student profile is removed.

Historical records may need to remain.

Therefore destructive cascading should generally be avoided for attendance-related entities.

### Enrollment

Removing an enrollment should not remove attendance history.

Therefore:

```text
class_enrollments
```

may be deleted independently while:

```text
attendance
```

remains intact.

---

# 38. Indexing Strategy

Indexes should be created based on actual query patterns.

Likely indexes include:

### Users

```text
email
```

### Students

```text
prn
user_id
branch_id
division_id
academic_year_id
```

### Classes

```text
faculty_id
subject_id
division_id
academic_year_id
```

### Enrollments

```text
student_id
class_id
(class_id, student_id) UNIQUE
```

### Sessions

```text
class_id
faculty_id
status
starts_at
ends_at
```

### Attendance

```text
student_id
session_id
marked_at
(session_id, student_id) UNIQUE
```

Indexes should be reviewed after real query patterns emerge.

---

# 39. Composite Indexes

Potential composite indexes:

```text
attendance_sessions(class_id, status)
```

Useful for finding active sessions for a class.

```text
attendance(student_id, marked_at)
```

Useful for student attendance history.

```text
attendance_sessions(starts_at, ends_at, status)
```

may assist session-related queries depending on the final implementation.

Indexes should not be added indiscriminately.

---

# 40. Academic Integrity Constraints

The database should prevent logically invalid relationships wherever practical.

Examples:

A class must reference:

```text
valid subject
valid faculty
valid division
valid academic year
```

An enrollment must reference:

```text
valid student
valid class
```

An attendance session must reference:

```text
valid class
valid faculty
```

An attendance record must reference:

```text
valid session
valid student
```

Additional cross-entity validation belongs in FastAPI services.

---

# 41. Cross-Entity Validation

Some rules cannot be efficiently enforced using simple foreign keys.

Example:

```text
Attendance session:
class_id = Class A

faculty_id = Faculty B
```

The database may allow this structurally.

FastAPI must verify:

```text
Faculty B is authorized to manage Class A
```

Similarly:

```text
Student X
attendance_session = Class A
```

requires the service layer to verify:

```text
Student X is enrolled in Class A
```

---

# 42. Attendance Integrity

Before creating attendance, FastAPI should validate:

```text
1. User is authenticated
2. User is a student
3. Session exists
4. Session is active
5. Session has not expired
6. Student is enrolled in the class
7. Location is valid
8. Location accuracy is acceptable
9. Face verification succeeds
10. Attendance does not already exist
```

The database then provides final integrity guarantees.

---

# 43. Transaction Strategy

Attendance creation should use a database transaction.

Conceptual flow:

```text
BEGIN

Validate relevant records

Check duplicate

Create attendance

COMMIT
```

If an error occurs:

```text
ROLLBACK
```

The unique database constraint remains the final protection against concurrent duplicate requests.

---

# 44. Data Retention

Retention policies should be defined before production.

Potential categories:

```text
User profile
Long-term

Academic data
Academic-period based

Attendance
Long-term / institution-defined

Face embeddings
Only while required for face verification

Verification attempts
Shorter retention depending on security requirements

Audit logs
Institution-defined
```

Exact retention periods must be decided according to institutional requirements and applicable privacy/legal obligations before production deployment.

---

# 45. Privacy Requirements

The database should avoid storing unnecessary sensitive information.

Do not store:

* Plaintext passwords — store only a salted Argon2id hash (`users.password_hash`)
* Raw camera images unless explicitly required
* Continuous GPS history

Face embeddings must be treated as sensitive biometric information and access must be restricted.

---

# 46. Initial Entity List

The expected initial database entities are:

```text
users
sessions
institutions
academic_years
branches
divisions
subjects
students
faculty
classes
class_enrollments
attendance_sessions
attendance_verifications
attendance
face_profiles
audit_logs
```

Potential post-MVP entities:

```text
attendance_verification_attempts
class_faculty
timetables
notifications
```

---

# 47. Simplified ER Diagram

```text
┌────────────────┐
│  institutions  │
└───────┬────────┘
        │
        ├──────────────┐
        ▼              ▼
┌──────────────┐ ┌──────────────┐
│academic_years│ │   branches   │
└──────┬───────┘ └──────┬───────┘
       │                │
       └───────┬────────┘
               ▼
        ┌─────────────┐
        │  divisions  │
        └──────┬──────┘
               │
               ▼
        ┌─────────────┐
        │  students   │◄──────────────┐
        └──────┬──────┘               │
               │                      │
               │ enrollment           │
               ▼                      │
       ┌──────────────────┐            │
       │class_enrollments │            │
       └────────┬─────────┘            │
                │                      │
                ▼                      │
          ┌───────────┐                │
          │  classes  │                │
          └─────┬─────┘                │
                │                      │
          ┌─────┼───────────┐          │
          ▼     ▼           ▼          │
      subject faculty   sessions       │
                        │              │
                        ▼              │
                  ┌────────────┐       │
                  │ attendance │───────┘
                  └────────────┘

users
 ├── students
 └── faculty

students
 └── face_profiles
```

---

# 48. Final Database Philosophy

The database should model the real academic domain rather than trying to optimize only for the attendance screen.

The most important conceptual separation is:

```text
User
   ↓
Student / Faculty
   ↓
Academic enrollment
   ↓
Class
   ↓
Attendance Session
   ↓
Attendance
```

And separately:

```text
Student
   ↓
Face Profile
```

This keeps authentication, academic relationships, attendance, and biometric information independent.

The database should remain normalized and understandable before introducing optimization.

---

# 49. Current Database Status

The conceptual model is defined.

Not yet finalized:

* Exact SQLAlchemy models
* PostgreSQL enum implementation
* Exact `NUMERIC` precision for coordinates
* `pgvector` extension setup
* Face embedding dimension
* Exact cascade behavior
* Verification-attempt retention
* Production retention policy

These should be finalized after the API, security, and face-recognition design are completed.

---

# 50. Related Documentation

* `PRODUCT.md` — Product requirements
* `ARCHITECTURE.md` — System architecture
* `UI.md` — UI/UX architecture
* `SECURITY.md` — Security requirements
* `API.md` — API contracts
* `AGENTS.md` — Coding-agent instructions
