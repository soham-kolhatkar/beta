# GeoAttend — Security Specification

## 1. Purpose

This document defines the security architecture and security requirements for GeoAttend.

GeoAttend handles several sensitive operations:

* User identity
* Password-based authentication
* Student academic information
* Faculty information
* Attendance records
* Location information
* Facial biometric representations
* Attendance verification attempts

The security model is designed around one principle:

> **The client provides evidence; the backend makes the decision.**

---

# 2. Security Objectives

GeoAttend must protect against:

1. Unauthorized access
2. Role escalation
3. Proxy attendance
4. Location manipulation
5. Face verification bypass
6. Duplicate attendance
7. Replay attacks
8. API abuse
9. Credential/token theft
10. Sensitive data exposure
11. Unauthorized attendance modification
12. Excessive biometric/location collection

---

# 3. Trust Boundaries

The system has several trust boundaries.

```text id="3p0kqz"
                    UNTRUSTED
                       │
              ┌────────▼────────┐
              │ Student Browser │
              │ Faculty Browser │
              └────────┬────────┘
                       │
                       │ HTTPS
                       ▼
               ┌───────────────┐
               │   FastAPI     │
               │ TRUST BOUNDARY│
               └───────┬───────┘
                       │
              ┌────────┴────────┐
              ▼                 ▼
       ┌─────────────┐   ┌──────────────┐
       │ PostgreSQL  │   │ Face Service │
       │   TRUSTED   │   │   TRUSTED    │
       └─────────────┘   └──────────────┘
```

Everything originating from the browser must be treated as potentially manipulated.

---

# 4. Fundamental Security Rule

Never trust security-sensitive values supplied by the frontend.

Do not trust:

```json id="x8s7za"
{
  "role": "FACULTY",
  "locationVerified": true,
  "faceVerified": true,
  "attendanceMarked": true
}
```

The backend must independently determine these values.

---

# 5. Authentication

GeoAttend implements email/password authentication directly rather than delegating identity to a third-party provider.

Authentication answers:

> Who is this user?

Authorization answers:

> What can this user do?

These must remain separate.

---

# 6. Login Flow

Conceptual flow:

```text id="m1m0d9"
Browser
   │
   ▼
POST /auth/login (email + password)
   │
   ▼
GeoAttend authentication layer
   │
   ▼
Look up user by (normalized) email
   │
   ▼
Verify password against stored Argon2id hash
   │
   ▼
Application session
   │
   ▼
FastAPI
```

If the email doesn't exist or the password is wrong, the backend must return the same generic `INVALID_CREDENTIALS` error either way — never reveal whether a given email is registered (account-enumeration protection).

Valid credentials must not be treated as the application's authorization model — role and permissions are always read from GeoAttend's own database, never inferred from the fact that login succeeded.

---

# 7. Application Identity

The application maintains its own user record.

Example:

```text id="2g8c9e"
Email + password credentials
       ↓
users
       ↓
role
       ↓
Student / Faculty / Admin
```

Presenting valid credentials does not automatically determine role — role is a property of the stored `users` record, not something derived from the login mechanism.

---

# 8. Session Security

The final session mechanism must:

* Use HTTPS in production
* Prevent token leakage
* Prevent session fixation
* Support expiration
* Support logout/revocation
* Avoid exposing sensitive credentials to client-side JavaScript unnecessarily

Implementation: a server-side, DB-backed session (not a JWT) — see `docs/DATABASE.md` §8 "Sessions". Only a SHA-256 hash of the session token is stored, giving trivial logout/revocation.

---

# 9. Token Handling

Never log:

* Passwords or password hashes
* Application session tokens
* Authorization headers

Tokens must never be placed in:

* URLs
* query parameters
* error messages
* analytics events
* client-visible logs

---

# 10. Authorization Model

GeoAttend uses role-based authorization.

Initial roles:

```text id="b50p1k"
STUDENT
FACULTY
ADMIN
```

However, role checking alone is not sufficient.

Resource-level authorization is also required.

---

# 11. Role Authorization

Example:

```text id="ql2vkj"
POST /sessions
```

requires:

```text id="6i1u4v"
Authenticated
AND
FACULTY role
```

But also:

```text id="2f0j34"
Faculty owns / is assigned to the class
```

Similarly:

```text id="l8h7ue"
POST /attendance/mark
```

requires:

```text id="o5b5yo"
Authenticated
AND
STUDENT role
AND
Student enrolled in class
```

---

# 12. Backend Authorization

Authorization must be enforced in FastAPI.

Frontend checks are for UX only.

Incorrect:

```text id="k9p6f3"
if (user.role === "FACULTY") {
    showFacultyDashboard();
}
```

This is acceptable for UI rendering but is not security.

The backend must independently enforce:

```text id="9jkh8w"
Authenticated user
      ↓
Load role from trusted source
      ↓
Check permission
      ↓
Check resource ownership
      ↓
Allow / reject
```

---

# 13. Privilege Escalation Prevention

Users must never be able to change their own role through client input.

For example, this must never be accepted:

```json id="7v8g50"
{
  "role": "ADMIN"
}
```

unless the request comes from an authorized administrative operation.

Role changes must be performed by authorized backend logic.

---

# 14. Student Authorization

A student can:

* View their own profile
* View their own attendance
* Register/update their face
* View eligible attendance sessions
* Attempt attendance

A student cannot:

* View another student's private attendance
* Create attendance sessions
* Modify attendance records
* Change their role
* Access faculty reports
* Access admin functionality

---

# 15. Faculty Authorization

Faculty can:

* View their profile
* View assigned classes
* Create sessions for authorized classes
* End their sessions
* Monitor their sessions
* View attendance for authorized classes
* Generate authorized reports

Faculty cannot:

* Modify another faculty member's sessions
* Access unrelated classes
* Modify student identity information without permission
* Change roles

---

# 16. Admin Authorization

Admins can manage institutional data according to their permissions.

Potential operations:

* Students
* Faculty
* Subjects
* Classes
* Academic structure
* Attendance administration
* Reports
* System configuration

Admin actions should be audited.

---

# 17. Object-Level Authorization

Every resource access must be checked against the authenticated user.

Example:

```text id="2o5m6f"
Faculty A
     ↓
GET /sessions/UUID_B
```

If `UUID_B` belongs to Faculty B:

```text id="aztq3n"
403 Forbidden
```

Resource IDs alone must never grant access.

---

# 18. Attendance Security Model

Attendance requires multiple independent conditions.

```text id="2hj8tb"
Authentication
       +
Authorization
       +
Active Session
       +
Class Enrollment
       +
Valid Location
       +
Acceptable GPS Accuracy
       +
Face Verification
       +
No Duplicate
       ↓
Attendance
```

All required conditions must pass.

---

# 19. Attendance Is a Security-Sensitive Operation

Attendance should not be treated as a normal CRUD operation.

For example:

```text id="ztf5kq"
POST /attendance
```

should not simply insert a row.

It should trigger a verification workflow.

Conceptually:

```text id="o2njdx"
Request
 ↓
Authenticate
 ↓
Authorize
 ↓
Validate session
 ↓
Validate enrollment
 ↓
Validate time
 ↓
Validate location
 ↓
Validate face
 ↓
Check duplicate
 ↓
Create attendance
```

---

# 20. Geolocation Security

Browser GPS is useful evidence but is not a cryptographically trusted location source.

The backend must:

1. Receive coordinates.
2. Validate their format/range.
3. Validate timestamp/context where appropriate.
4. Load the authoritative session location.
5. Calculate distance server-side.
6. Compare against configured radius.
7. Consider reported GPS accuracy.

The frontend must not submit:

```text id="q9xj4h"
distance = 20
isWithinRadius = true
```

and expect the backend to trust it.

---

# 21. GPS Accuracy

A coordinate should not automatically be accepted solely because its mathematical distance is within the radius.

Example:

```text id="5kcr7n"
Distance = 30 m
GPS accuracy = ±500 m
```

This is unreliable.

The application should have configurable rules around acceptable accuracy.

The exact threshold should be determined through testing rather than arbitrarily hardcoded.

---

# 22. Location Spoofing

Web applications cannot guarantee that browser GPS data is impossible to spoof.

Therefore GeoAttend should treat location as one component of a multi-factor verification system:

```text id="3u9i9f"
Location
+
Authentication
+
Class membership
+
Face
+
Session timing
```

Additional anti-abuse signals may be introduced later.

---

# 23. Continuous Tracking

Continuous student location tracking is explicitly out of scope.

Location should generally be collected:

```text id="s9y80p"
When required for attendance verification
```

not:

```text id="7udx1n"
24/7
Background
Continuous
```

This reduces:

* Privacy risk
* Battery consumption
* Data storage
* Regulatory exposure

---

# 24. Face Data Security

Facial biometric information must be treated as highly sensitive.

The preferred architecture is:

```text id="h6o3f9"
Camera image
      ↓
Face processing
      ↓
Embedding
      ↓
Secure storage
```

rather than unnecessarily retaining raw photographs.

---

# 25. Face Embedding Protection

Face embeddings must not be treated as ordinary public profile information.

Access should be restricted to:

* Face verification service
* Authorized backend processes
* Explicitly authorized administrative operations

Students should not be able to request another student's embedding.

Faculty should not receive raw embeddings.

---

# 26. Face Verification

Face verification is a 1:1 verification process.

The system should verify:

```text id="v0m2c4"
Authenticated Student
        ↕
Registered Face
```

rather than performing unrestricted face identification across the entire database.

This reduces both complexity and privacy exposure.

---

# 27. Face Verification Threshold

The face model will produce some confidence/similarity measure.

The threshold must not be arbitrarily chosen.

It should be determined using:

* Validation data
* False acceptance rate
* False rejection rate
* Real-world classroom conditions
* Lighting variation
* Camera variation

The threshold should be configurable rather than hardcoded in multiple files.

---

# 28. Face Spoofing

A photograph or replayed video may potentially bypass basic face matching.

Therefore:

### MVP

Basic face verification may be used to validate the complete product workflow.

### Security phase

Add liveness/anti-spoofing.

Potential flow:

```text id="k4kgr0"
Face detected
    ↓
Liveness check
    ↓
Face verification
    ↓
Attendance
```

---

# 29. Camera Privacy

Camera access should only be requested when required.

The application should explain why camera access is needed.

Example:

> Camera access is required to verify your identity before marking attendance.

The camera should not remain active after verification is complete.

---

# 30. Face Image Handling

If raw images are temporarily uploaded for verification:

* Process them as quickly as practical.
* Do not persist them unless explicitly required.
* Do not write them to application logs.
* Do not include them in error reports.
* Do not store them in public object storage.

If image retention is introduced later, it requires an explicit privacy decision.

---

# 31. Attendance Replay Protection

A valid attendance request should not be reusable.

Potential protections include:

* Session validity
* Short-lived verification context
* Server-generated challenge/request IDs
* Timestamp validation
* One-time verification state
* Database uniqueness

The exact mechanism will be finalized during API design.

---

# 32. Duplicate Attendance Protection

Duplicate attendance must be prevented at two levels.

### Application

```text id="9wm1qn"
Check existing attendance
```

### Database

```text id="6w0r2a"
UNIQUE(session_id, student_id)
```

The database constraint is the final guarantee.

---

# 33. Race Conditions

Two simultaneous attendance requests must not create two attendance records.

Example:

```text id="4z1g7v"
Request A ──┐
            ├── Database
Request B ──┘
```

Both requests might pass an application-level existence check.

The unique constraint must ensure only one succeeds.

The service must gracefully handle the uniqueness violation.

---

# 34. Session Security

Attendance sessions must validate:

* Session exists
* Session belongs to the appropriate class
* Session is active
* Current time is within session limits
* Faculty is authorized
* Student is enrolled

Expired sessions must not accept attendance.

---

# 35. Session Time Manipulation

The server's time must be authoritative.

Do not trust:

```text id="1v0p83"
clientTime
```

for determining whether a session is active.

Use backend/server time.

All database timestamps should be stored in UTC.

---

# 36. API Rate Limiting

Arcjet will provide rate limiting/security controls.

High-risk endpoints:

```text id="r6kw3v"
/auth/*
/face/register
/face/verify
/attendance/verify
/attendance/mark
```

Face-related endpoints require particular protection because they can be computationally expensive.

---

# 37. Rate Limit Strategy

Rate limits should distinguish between:

* Authentication attempts
* Face registration
* Face verification
* Attendance attempts
* Normal reads

For example, a face verification endpoint should have stricter limits than:

```text id="e4g1o6"
GET /student/profile
```

Exact values should be established after testing and expected usage analysis.

---

# 38. Abuse Detection

The system should eventually detect suspicious patterns such as:

```text id="l8m2jg"
Many verification attempts
Repeated failures
Unusual request frequency
Repeated attempts across sessions
Suspicious device/browser behavior
```

These signals should support security decisions without automatically punishing legitimate users without review.

---

# 39. Input Validation

All API input must be validated using Pydantic schemas and appropriate backend validation.

Validate:

* UUIDs
* Strings
* Dates
* Coordinates
* Radius
* Accuracy
* Pagination
* Filters
* File/image constraints

Coordinates should satisfy valid ranges:

```text id="zw8c4b"
Latitude:
-90 to 90

Longitude:
-180 to 180
```

---

# 40. File/Image Validation

If face images are transmitted to FastAPI, validate:

* MIME type
* File size
* Image dimensions
* Decode success
* Number of faces
* Content validity

Do not trust the client-provided file extension.

Example:

```text id="i8w6k1"
avatar.jpg
```

must not automatically be assumed to be a valid JPEG.

---

# 41. HTTP Security

Production API communication must use HTTPS.

Security headers should be considered for both frontend and backend.

Potential headers:

* Strict-Transport-Security
* Content-Security-Policy
* X-Content-Type-Options
* Referrer-Policy
* Permissions-Policy

Exact configuration depends on the final deployment platform.

---

# 42. CORS

FastAPI should allow only known frontend origins.

Development:

```text id="m7gd5f"
http://localhost:3000
```

Production:

```text id="2h7l3f"
https://<production-frontend>
```

Avoid:

```text id="4aj5y9"
allow_origins=["*"]
```

for authenticated production APIs.

---

# 43. CSRF

The final CSRF strategy depends on the authentication/session mechanism.

If authentication uses secure HTTP-only cookies, CSRF protections must be considered.

If bearer tokens are used through a different architecture, the threat model changes.

This will be finalized with the authentication implementation.

---

# 44. Cookie Security

If cookies are used for authentication, production cookies should use appropriate flags such as:

```text id="n1r1ra"
HttpOnly
Secure
SameSite
```

Exact `SameSite` configuration depends on the deployment architecture.

Authentication cookies must not be readable by arbitrary frontend JavaScript.

---

# 45. Secrets Management

Secrets must never be committed to Git.

Sensitive values include:

```text id="2l5v0q"
Database credentials
JWT/session secrets
Password-hashing configuration (if any application-level pepper is used)
Arcjet credentials
Deployment credentials
```

Use environment variables or a managed secrets system.

---

# 46. Environment Files

Development secrets may be stored locally in:

```text id="5r4jq7"
.env
.env.local
```

These files must be ignored by Git.

Example:

```text id="w2w2ij"
.env
.env.*
!.env.example
```

The repository should contain:

```text id="0lq9r8"
.env.example
```

with placeholders only.

---

# 47. Logging Security

Logs must not contain:

* Session tokens
* Face images
* Face embeddings
* Passwords or password hashes
* Authorization headers
* Full sensitive request payloads

Prefer structured logs containing:

```text id="xq5h17"
request_id
user_id
route
status_code
duration
error_code
```

where appropriate.

---

# 48. Error Security

Do not expose internal exceptions to users.

Bad:

```text id="z85pgi"
sqlalchemy.exc.IntegrityError:
duplicate key value violates unique constraint ...
```

Good:

```text id="8v0lka"
Attendance has already been marked for this session.
```

Detailed errors should be logged internally without exposing sensitive implementation information.

---

# 49. Database Security

PostgreSQL credentials must be protected.

The application database user should have only the permissions it requires.

Production database access should not be publicly exposed unnecessarily.

Database backups should be protected with the same sensitivity as the database itself.

---

# 50. SQL Injection

SQLAlchemy parameterized queries should be used.

Do not construct SQL using string concatenation with user input.

Bad:

```python
query = f"SELECT * FROM users WHERE email = '{email}'"
```

Use SQLAlchemy expressions.

---

# 51. ORM Security

SQLAlchemy models and queries should use explicit relationships and validated inputs.

Avoid accepting arbitrary field names/order expressions from users without a controlled allowlist.

For example:

```text id="2bx8gm"
sort_by=name
sort_by=created_at
```

should use an explicit mapping rather than directly interpolating the value into SQL.

---

# 52. Data Access Security

Repositories/services should enforce ownership boundaries.

Example:

```text id="x2h8qm"
Faculty A
   ↓
get_session(session_id)
   ↓
Verify session.faculty_id == current_faculty.id
```

Do not rely on the frontend to request only authorized resources.

---

# 53. Academic Data Security

Students should only access:

* Their own profile
* Their own attendance
* Their own enrolled classes

Faculty should only access:

* Their assigned classes
* Their sessions
* Attendance belonging to authorized classes

Admins may have broader access according to institutional permissions.

---

# 54. Attendance Modification

Attendance should not normally be directly editable.

If manual correction is required:

```text id="4a9s7z"
Original attendance
       ↓
Correction request
       ↓
Authorized faculty/admin
       ↓
Audit log
       ↓
Updated attendance
```

Never silently overwrite attendance without an audit trail.

---

# 55. Audit Logging

Audit important administrative/security events.

Examples:

```text id="u1v9yq"
User role changed
Faculty created session
Faculty ended session
Attendance manually changed
Face profile updated
Student enrollment changed
```

Audit logs should contain enough context to investigate an event.

---

# 56. Privacy by Design

The system should follow data minimization.

### Collect

Only what is necessary.

### Process

Only when required.

### Store

Only for as long as necessary.

### Expose

Only to authorized users.

---

# 57. Location Data Retention

Location data collected during attendance should have an explicit retention policy.

The system should not silently become a student location-tracking system.

Potential approach:

```text id="5aqmbm"
Attendance verification
        ↓
Location captured
        ↓
Distance calculated
        ↓
Required audit information retained
```

Exact retention requirements should be finalized before production.

---

# 58. Biometric Data Retention

Face embeddings should have a defined lifecycle.

Potential states:

```text id="u6v8lf"
Not registered
     ↓
Registered
     ↓
Updated
     ↓
Revoked/deleted
```

Deleting a student should trigger an explicit decision about the associated biometric profile.

---

# 59. Account Deactivation

A user should be deactivatable without necessarily destroying historical attendance.

Example:

```text id="6x3p7n"
users.is_active = false
```

The user cannot authenticate/use the system.

Historical attendance remains available where institutionally required.

---

# 60. Face Registration Security

Face registration is highly sensitive.

The system should require:

* Authenticated student
* Appropriate role
* Face capture validation
* Exactly one suitable face
* Model processing
* Secure storage
* Rate limiting

A student should not be able to register a face for another student.

---

# 61. Face Profile Replacement

Replacing an existing face profile should require explicit verification.

Potential flow:

```text id="p1j7hk"
Authenticated student
       ↓
Re-authentication / security check
       ↓
New face capture
       ↓
Verification
       ↓
Replace existing profile
       ↓
Audit event
```

The exact workflow will be determined during implementation.

---

# 62. Account Sharing

Because GeoAttend now owns authentication directly, email/password credentials are inherently easier to share, guess, or hand off than a third-party OAuth identity would have been — there is no external account with its own independent protections (device trust, provider-side anomaly detection, etc.) backing them. This means GeoAttend's actual anti-proxy guarantee rests more heavily on face verification than on the login mechanism itself.

The expected model is:

```text id="q9e8y7"
Email/password identity
        +
Face identity
        ↓
Student identity
```

A student sharing their password should still fail face verification when another person attempts attendance. Password hashing (Argon2id) and login rate limiting reduce the risk of credential *compromise*, but they do not prevent deliberate credential *sharing* — that risk is mitigated by face verification, not by the authentication mechanism.

---

# 63. Device Fingerprinting

Device/browser fingerprinting is not a primary attendance factor.

It may be introduced later as an additional fraud signal.

It must never replace:

```text id="7j3q9x"
Authentication
Location
Face
```

Reasons:

* Fingerprints can change
* Browser updates can alter fingerprints
* Privacy concerns
* False positives
* Not a reliable identity mechanism

---

# 64. Replay and Request Binding

Attendance verification requests should be associated with:

```text id="x4qk5n"
Authenticated user
Session
Verification attempt
Timestamp/context
```

This prevents a verification result from being blindly reused for another session or user.

---

# 65. Brute Force Protection

Protect authentication and verification endpoints from repeated attempts.

Examples:

```text id="e6i7f8"
Login brute-force / credential stuffing
Face verification abuse
Attendance verification abuse
```

`/auth/login` needs particular attention now that GeoAttend owns authentication directly: rate limit by both IP and target email, return identical generic errors for "no such user" and "wrong password," and consider a short backoff after repeated failures on the same account. Arcjet should provide the primary rate-limiting layer where applicable.

---

# 66. Denial of Service Considerations

Face processing can be computationally expensive.

Therefore:

* Rate limit face endpoints.
* Limit upload sizes.
* Reject malformed images early.
* Avoid unnecessary model initialization per request.
* Reuse loaded model instances where safe.
* Monitor processing latency.
* Consider asynchronous processing only if actually necessary.

---

# 67. Face Model Resource Management

The face model should be initialized efficiently.

Avoid:

```text id="n6m1xs"
Every request
    ↓
Load model
    ↓
Process
    ↓
Destroy model
```

Prefer:

```text id="fl4y4s"
Application startup
       ↓
Load model
       ↓
Reuse model
```

provided the selected model/library is thread-safe and deployment resources allow it.

---

# 68. Security Testing

Security testing should include:

### Authentication

* Invalid/incorrect credentials (must not reveal whether the email exists)
* Brute-force / credential-stuffing attempts against `/auth/login`
* Expired sessions
* Session manipulation
* Unauthorized access

### Authorization

* Student → faculty endpoints
* Faculty → another faculty's data
* Student → another student's data
* Role manipulation

### Attendance

* Duplicate requests
* Expired sessions
* Wrong class
* Wrong student
* Outside radius
* Poor GPS accuracy
* Face mismatch
* Replay attempts

### API

* Rate-limit testing
* Invalid UUIDs
* Oversized uploads
* Malformed JSON
* Injection attempts

---

# 69. Security Testing Priority

The highest-priority tests are:

```text id="ljt2i3"
1. Cannot mark attendance for another student
2. Cannot mark attendance outside the allowed location
3. Cannot mark attendance after session expiry
4. Cannot mark attendance without face verification
5. Cannot mark attendance twice
6. Cannot access another user's attendance
7. Cannot escalate role
8. Cannot bypass API rate limits
```

---

# 70. Security Incident Handling

The application should eventually support investigation of suspicious activity.

Useful information:

```text id="e2p7qa"
User
Session
Timestamp
Endpoint
Verification result
Failure reason
Request ID
```

Do not log raw biometric data merely for debugging.

---

# 71. Security Headers and Permissions

Browser capabilities should be explicitly restricted where possible.

Potential `Permissions-Policy` controls include:

```text id="q3zqk8"
camera
geolocation
```

The final policy should allow only the capabilities required by the application.

---

# 72. Production Checklist

Before production:

```text id="r4m6kz"
[ ] HTTPS enabled
[ ] Secure authentication cookies/tokens
[ ] Password hashing configured correctly (Argon2id, adequate cost parameters)
[ ] Login endpoint rate-limited and account-enumeration-safe
[ ] Database credentials protected
[ ] CORS restricted
[ ] Rate limiting enabled
[ ] Face endpoints protected
[ ] Upload limits configured
[ ] Security headers configured
[ ] Backend authorization tested
[ ] Database constraints verified
[ ] Audit logging enabled
[ ] Sensitive logs removed
[ ] Backups configured
[ ] Data retention policy defined
[ ] Biometric retention policy defined
[ ] Error handling reviewed
[ ] Monitoring configured
```

---

# 73. Security Philosophy

GeoAttend should not rely on one security mechanism.

The system should use defense in depth:

```text id="1l44cm"
Password Authentication
      +
Application Authorization
      +
Class Membership
      +
Session Validation
      +
Geolocation
      +
GPS Accuracy
      +
Face Verification
      +
Database Constraints
      +
Rate Limiting
      +
Auditability
```

No single layer is assumed to be perfect.

---

# 74. Current Security Status

The security model is conceptually defined.

Still to finalize:

* Exact Argon2id parameters (cost/memory/parallelism — currently library defaults)
* Exact Arcjet integration (currently skipped entirely — `/auth/*` has no rate limiting yet)
* Face model
* Liveness mechanism
* Verification challenge mechanism
* Location accuracy thresholds
* Biometric retention policy
* Audit log schema
* Production security headers
* Deployment-specific security configuration

These decisions must be finalized before production deployment.

---

# 75. Related Documentation

* `PRODUCT.md` — Product requirements
* `ARCHITECTURE.md` — System architecture
* `DATABASE.md` — Database design
* `UI.md` — UI/UX specification
* `API.md` — API contracts
* `AGENTS.md` — Coding-agent instructions
