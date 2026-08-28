# GeoAttend — API Specification

## 1. Purpose

This document defines the API contract between the GeoAttend frontend and backend.

The backend is implemented using FastAPI.

The frontend is implemented using Next.js with TypeScript.

The API follows REST principles and is versioned under:

```text
/api/v1
```

The API is authoritative for:

* Authentication state
* Authorization
* Academic relationships
* Attendance sessions
* Geolocation verification
* Face verification
* Attendance creation
* Attendance history

---

# 2. Base URL

Development:

```text
http://localhost:8000/api/v1
```

Production:

```text
https://<api-domain>/api/v1
```

The frontend should access the backend through a configurable environment variable.

Example:

```text
NEXT_PUBLIC_API_URL
```

The actual environment variable name can be finalized during implementation.

---

# 3. API Principles

## 3.1 Backend is authoritative

The frontend provides input/evidence.

FastAPI makes the final decision.

For example:

```text
Frontend
  ↓
latitude
longitude
accuracy
face image
session ID
  ↓
FastAPI
  ↓
validate
  ↓
decision
```

---

## 3.2 API responses must be predictable

Successful responses should use consistent structures.

Errors should expose stable error codes.

Example:

```json
{
  "error": {
    "code": "SESSION_EXPIRED",
    "message": "This attendance session has ended."
  }
}
```

The frontend should primarily use `error.code` for programmatic handling.

---

# 4. HTTP Status Codes

Use standard HTTP status codes.

```text
200 OK
201 Created
204 No Content
400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
409 Conflict
422 Unprocessable Entity
429 Too Many Requests
500 Internal Server Error
```

General meaning:

### 401

User is not authenticated.

### 403

User is authenticated but does not have permission.

### 404

Requested resource does not exist or is intentionally hidden.

### 409

Request conflicts with current state.

Example:

```text
Attendance already marked.
```

### 422

Request structure/data validation failed.

### 429

Rate limit exceeded.

---

# 5. Authentication Architecture

Google OAuth establishes the user's identity.

The exact OAuth/session implementation may use a secure application-session mechanism.

The frontend should not need to know Google's internal OAuth tokens.

Conceptually:

```text
Browser
   ↓
Google
   ↓
GeoAttend Auth
   ↓
Application Session
   ↓
FastAPI
```

---

# 6. Authentication Endpoints

## GET `/auth/me`

Returns the currently authenticated GeoAttend user.

### Response

```json
{
  "id": "uuid",
  "email": "student@example.com",
  "name": "Soham Kolhatkar",
  "role": "STUDENT",
  "profile_image_url": "https://..."
}
```

If unauthenticated:

```text
401 Unauthorized
```

---

# 7. GET `/auth/status`

Optional lightweight authentication-status endpoint.

### Response

```json
{
  "authenticated": true
}
```

This may be unnecessary if `/auth/me` is already cached by TanStack Query.

Do not implement duplicate endpoints without a concrete frontend requirement.

---

# 8. POST `/auth/logout`

Ends the current application session.

### Response

```text
204 No Content
```

The exact session invalidation mechanism depends on the authentication implementation.

---

# 9. User Endpoints

## GET `/users/me`

Returns the authenticated user's basic profile.

Potential response:

```json
{
  "id": "uuid",
  "name": "Soham Kolhatkar",
  "email": "student@example.com",
  "role": "STUDENT",
  "profile_image_url": "https://..."
}
```

This endpoint may overlap with `/auth/me`.

Prefer `/auth/me` if it already provides all required information.

Avoid maintaining duplicate endpoints unnecessarily.

---

# 10. Student Profile

## GET `/students/me`

Returns student-specific information.

### Response

```json
{
  "id": "uuid",
  "user": {
    "id": "uuid",
    "name": "Soham Kolhatkar",
    "email": "student@example.com"
  },
  "prn": "123456",
  "roll_number": "42",
  "branch": {
    "id": "uuid",
    "name": "Computer Science",
    "code": "CSAI"
  },
  "division": {
    "id": "uuid",
    "name": "A"
  },
  "academic_year": {
    "id": "uuid",
    "name": "2026-27"
  },
  "face_registered": true
}
```

---

# 11. Student Dashboard

## GET `/students/me/dashboard`

Returns the data required for the student dashboard.

The endpoint should avoid requiring the frontend to make many sequential requests.

Potential response:

```json
{
  "student": {
    "name": "Soham Kolhatkar"
  },
  "attendance": {
    "percentage": 82.4,
    "present": 42,
    "total": 51
  },
  "active_session": {
    "id": "uuid",
    "subject": "Database Management Systems",
    "class_name": "CSAI-A",
    "faculty_name": "Professor XYZ",
    "ends_at": "2026-08-08T10:45:00Z"
  },
  "today_classes": []
}
```

This endpoint is optimized for the dashboard experience.

---

# 12. Student Classes

## GET `/students/me/classes`

Returns classes the student is enrolled in.

### Response

```json
{
  "items": [
    {
      "id": "uuid",
      "subject": {
        "id": "uuid",
        "name": "Database Management Systems",
        "code": "DBMS"
      },
      "faculty": {
        "id": "uuid",
        "name": "Professor XYZ"
      },
      "division": "A"
    }
  ]
}
```

---

# 13. Student Attendance Summary

## GET `/students/me/attendance/summary`

Returns overall and subject-level attendance.

### Response

```json
{
  "overall": {
    "percentage": 82.4,
    "present": 42,
    "total": 51
  },
  "subjects": [
    {
      "class_id": "uuid",
      "subject": "Database Management Systems",
      "percentage": 82.4,
      "present": 42,
      "total": 51
    }
  ]
}
```

---

# 14. Student Attendance History

## GET `/students/me/attendance`

Returns attendance history.

Query parameters:

```text
subject_id
status
from
to
page
page_size
```

Example:

```text
GET /students/me/attendance?subject_id=UUID&page=1&page_size=20
```

### Response

```json
{
  "items": [
    {
      "id": "uuid",
      "session_id": "uuid",
      "subject": "Database Management Systems",
      "marked_at": "2026-08-08T10:32:00Z",
      "status": "PRESENT"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 42,
    "total_pages": 3
  }
}
```

---

# 15. Student Subject Attendance

## GET `/students/me/classes/{class_id}/attendance`

Returns attendance information for one class.

### Authorization

The authenticated student must be enrolled in the class.

Otherwise:

```text
403 Forbidden
```

### Response

```json
{
  "class": {
    "id": "uuid",
    "subject": "Database Management Systems"
  },
  "summary": {
    "percentage": 82.4,
    "present": 42,
    "total": 51
  },
  "records": []
}
```

---

# 16. Face Registration

## POST `/students/me/face`

Registers or updates the student's face profile.

The request may use `multipart/form-data` if the browser uploads an image.

Conceptual request:

```text
multipart/form-data

image: <face image>
```

### Required validation

Backend must verify:

* Authenticated student
* Valid image
* Supported MIME type
* File size
* Image decodes successfully
* Exactly one face
* Face quality acceptable
* Face processing succeeds

### Response

```json
{
  "face_registered": true,
  "model": {
    "name": "model-name",
    "version": "1.0"
  }
}
```

Do not return the stored embedding.

---

# 17. Face Profile Status

## GET `/students/me/face`

Returns face-registration status.

### Response

```json
{
  "registered": true,
  "model": {
    "name": "model-name",
    "version": "1.0"
  },
  "updated_at": "2026-08-08T08:00:00Z"
}
```

No embedding is returned.

---

# 18. Active Attendance Sessions

## GET `/attendance/sessions/active`

Returns attendance sessions the authenticated student is eligible to attend.

The backend must filter based on:

* Student identity
* Enrollment
* Session state
* Time

The frontend must not receive unrelated active sessions.

### Response

```json
{
  "items": [
    {
      "id": "uuid",
      "subject": {
        "id": "uuid",
        "name": "Database Management Systems",
        "code": "DBMS"
      },
      "class": {
        "id": "uuid",
        "name": "CSAI-A"
      },
      "faculty": {
        "name": "Professor XYZ"
      },
      "starts_at": "2026-08-08T10:00:00Z",
      "ends_at": "2026-08-08T11:00:00Z"
    }
  ]
}
```

---

# 19. Session Details

## GET `/attendance/sessions/{session_id}`

Returns information about a session.

### Authorization

Students may access the session only if they are eligible to attend it.

Faculty may access the session only if authorized to manage it.

### Response

```json
{
  "id": "uuid",
  "class": {
    "id": "uuid",
    "name": "CSAI-A"
  },
  "subject": {
    "id": "uuid",
    "name": "Database Management Systems",
    "code": "DBMS"
  },
  "faculty": {
    "id": "uuid",
    "name": "Professor XYZ"
  },
  "starts_at": "2026-08-08T10:00:00Z",
  "ends_at": "2026-08-08T11:00:00Z",
  "status": "ACTIVE"
}
```

Do not expose unnecessary session security information.

---

# 20. Faculty Classes

## GET `/faculty/me/classes`

Returns classes assigned to the authenticated faculty member.

### Response

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "CSAI-A",
      "subject": {
        "id": "uuid",
        "name": "Database Management Systems",
        "code": "DBMS"
      },
      "student_count": 48
    }
  ]
}
```

---

# 21. Create Attendance Session

## POST `/attendance/sessions`

Creates an attendance session.

### Authorization

Requires:

```text
FACULTY
```

and faculty must be authorized for the specified class.

### Request

```json
{
  "class_id": "uuid",
  "starts_at": "2026-08-08T10:00:00Z",
  "ends_at": "2026-08-08T11:00:00Z",
  "latitude": 18.5204,
  "longitude": 73.8567,
  "radius_meters": 100
}
```

### Validation

Backend validates:

* Faculty authorization
* Class existence
* Time validity
* Coordinates
* Radius
* Existing conflicting session if applicable

### Response

```text
201 Created
```

```json
{
  "id": "uuid",
  "class_id": "uuid",
  "status": "ACTIVE",
  "starts_at": "2026-08-08T10:00:00Z",
  "ends_at": "2026-08-08T11:00:00Z"
}
```

---

# 22. End Attendance Session

## POST `/attendance/sessions/{session_id}/end`

Ends an active attendance session.

### Authorization

Faculty must own/be assigned to the session.

### Response

```json
{
  "id": "uuid",
  "status": "ENDED",
  "ended_at": "2026-08-08T10:45:00Z"
}
```

This endpoint is preferable to a generic:

```text
PATCH /sessions/{id}
```

because ending a session is a domain action.

---

# 23. Faculty Session List

## GET `/faculty/me/sessions`

Returns sessions belonging to the authenticated faculty member.

Query parameters:

```text
class_id
status
from
to
page
page_size
```

---

# 24. Live Session Attendance

## GET `/attendance/sessions/{session_id}/attendance`

Returns attendance for an active/historical session.

### Authorization

Faculty must be authorized for the session.

### Response

```json
{
  "session": {
    "id": "uuid",
    "class_name": "CSAI-A",
    "subject": "Database Management Systems"
  },
  "summary": {
    "total_students": 48,
    "present": 42,
    "not_marked": 4,
    "verification_issues": 2
  },
  "students": [
    {
      "student_id": "uuid",
      "name": "Aarav Sharma",
      "prn": "123456",
      "status": "PRESENT",
      "marked_at": "2026-08-08T10:31:42Z"
    }
  ]
}
```

---

# 25. Live Updates

The initial implementation can use TanStack Query polling/refetching.

Example:

```text
GET /attendance/sessions/{session_id}/attendance
```

with periodic refetching while the session is active.

WebSockets or Server-Sent Events should not be introduced until real-time requirements justify them.

Potential future architecture:

```text
Faculty
   ↓
WebSocket / SSE
   ↓
FastAPI
   ↓
Attendance event
```

---

# 26. Student Attendance Verification

The attendance workflow should not be represented by a single insecure request.

The backend should maintain a verification context.

Conceptually:

```text
1. Create verification attempt
2. Validate location
3. Validate face
4. Commit attendance
```

---

# 27. Start Verification

## POST `/attendance/sessions/{session_id}/verification`

Creates a verification context for the authenticated student.

### Authorization

Student must:

* Be authenticated
* Be enrolled in the session's class
* Have a registered face
* Be eligible for the session

### Response

```json
{
  "verification_id": "uuid",
  "session_id": "uuid",
  "expires_at": "2026-08-08T10:35:00Z",
  "steps": [
    "LOCATION",
    "FACE"
  ]
}
```

The verification ID should be short-lived.

---

# 28. Location Verification

## POST `/attendance/verifications/{verification_id}/location`

Submits the student's current location.

### Request

```json
{
  "latitude": 18.5205,
  "longitude": 73.8568,
  "accuracy_meters": 12
}
```

### Backend processing

The backend:

1. Loads verification context.
2. Validates expiration.
3. Loads session location.
4. Calculates distance.
5. Evaluates radius.
6. Evaluates accuracy.
7. Stores the verification result.

### Successful response

```json
{
  "verified": true,
  "distance_meters": 34.2,
  "accuracy_meters": 12.0,
  "next_step": "FACE"
}
```

---

# 29. Location Failure Response

Example:

```json
{
  "verified": false,
  "code": "LOCATION_OUTSIDE_RADIUS",
  "message": "You are outside the attendance area.",
  "distance_meters": 183.4,
  "allowed_radius_meters": 100
}
```

The frontend can translate this into the appropriate UX.

---

# 30. Face Verification

## POST `/attendance/verifications/{verification_id}/face`

Uploads the student's face image for verification.

Request:

```text
multipart/form-data

image: <face image>
```

Backend validates:

* Verification context
* Expiration
* Student identity
* Image validity
* Face count
* Face quality
* Liveness if enabled
* Face similarity

### Successful response

```json
{
  "verified": true,
  "next_step": "COMPLETE"
}
```

Do not expose the student's stored embedding.

Do not expose internal model thresholds.

---

# 31. Face Failure Response

Example:

```json
{
  "verified": false,
  "code": "FACE_NOT_VERIFIED",
  "message": "We couldn't verify your identity."
}
```

The response may optionally include:

```json
{
  "retryable": true
}
```

The frontend should determine the appropriate retry UX.

---

# 32. Complete Attendance

## POST `/attendance/verifications/{verification_id}/complete`

Attempts to convert a successful verification context into an attendance record.

### Backend must revalidate

Even if previous steps succeeded, the backend should verify:

* Verification context is valid
* Context belongs to authenticated user
* Session is still active
* Student is still eligible
* Location verification succeeded
* Face verification succeeded
* Attendance does not already exist

### Response

```json
{
  "attendance_id": "uuid",
  "status": "PRESENT",
  "marked_at": "2026-08-08T10:32:00Z"
}
```

---

# 33. Why Use a Verification Context?

Avoid:

```text id="uk8p7a"
POST /attendance/mark
{
    student_id,
    session_id,
    location,
    face
}
```

as a single uncontrolled operation.

Instead:

```text id="6p0qzq"
Create verification
       ↓
Location
       ↓
Face
       ↓
Complete
```

This gives the backend a short-lived state machine.

It also helps prevent replay and cross-session verification reuse.

---

# 34. Verification State

Conceptual states:

```text
CREATED
LOCATION_VERIFIED
FACE_VERIFIED
COMPLETED
FAILED
EXPIRED
```

The backend controls transitions.

The frontend should not be able to arbitrarily set the state.

---

# 35. Verification Expiration

Verification contexts must expire quickly.

Example:

```text id="f9x9v4"
Created
   ↓
Short validity period
   ↓
Expired
```

The exact duration should be configured rather than scattered across the codebase.

---

# 36. Attendance Already Marked

If the student already has attendance:

```text
409 Conflict
```

Example:

```json
{
  "error": {
    "code": "ATTENDANCE_ALREADY_MARKED",
    "message": "Attendance has already been marked for this session."
  }
}
```

---

# 37. Session Expired

If a student attempts verification after session expiry:

```text
409 Conflict
```

```json
{
  "error": {
    "code": "SESSION_EXPIRED",
    "message": "This attendance session has ended."
  }
}
```

---

# 38. Student Not Enrolled

If the student is not enrolled in the class:

```text
403 Forbidden
```

```json
{
  "error": {
    "code": "NOT_ENROLLED",
    "message": "You are not enrolled in this class."
  }
}
```

---

# 39. Face Not Registered

If the student has no registered face:

```text
409 Conflict
```

```json
{
  "error": {
    "code": "FACE_NOT_REGISTERED",
    "message": "Please register your face before marking attendance."
  }
}
```

The frontend can provide a direct route to face registration.

---

# 40. Unauthorized Session Access

If a student tries to access an unrelated session:

```text
403 Forbidden
```

The backend should avoid exposing unnecessary information about the existence of unauthorized resources.

---

# 41. Faculty Session Validation

Before creating a session:

```text
Faculty authenticated
        ↓
Faculty role
        ↓
Class exists
        ↓
Faculty assigned to class
        ↓
Time valid
        ↓
Location valid
        ↓
Create session
```

---

# 42. Session Conflicts

The backend should define whether multiple overlapping sessions for the same class are allowed.

Initial recommendation:

```text
Do not allow overlapping active sessions
for the same class.
```

If a conflict occurs:

```text
409 Conflict
```

Example:

```json
{
  "error": {
    "code": "SESSION_CONFLICT",
    "message": "An active session already exists for this class."
  }
}
```

---

# 43. Faculty Dashboard Endpoint

## GET `/faculty/me/dashboard`

Returns information required for the faculty dashboard.

Potential response:

```json
{
  "today": {
    "classes": 3,
    "active_sessions": 1,
    "upcoming_sessions": 2
  },
  "active_session": {},
  "upcoming_classes": []
}
```

The endpoint should be optimized for dashboard rendering.

---

# 44. Reports

Reports should initially use standard REST queries rather than a separate reporting service.

Example:

## GET `/faculty/me/reports/attendance`

Query parameters:

```text
class_id
from
to
student_id
page
page_size
```

Response:

```json
{
  "items": [],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total": 200,
    "total_pages": 4
  }
}
```

---

# 45. Export

Export should be treated as a separate operation.

Potential future endpoint:

```text
GET /faculty/me/reports/attendance/export
```

Supported formats may include:

```text
CSV
XLSX
```

Do not implement exports until the basic reporting API is stable.

---

# 46. Admin API

Admin APIs will manage:

```text
students
faculty
subjects
branches
divisions
academic years
classes
enrollments
attendance
```

Example:

```text
GET    /admin/students
POST   /admin/students
PATCH  /admin/students/{id}

GET    /admin/faculty
POST   /admin/faculty
PATCH  /admin/faculty/{id}
```

All admin endpoints require:

```text
ADMIN
```

and appropriate resource authorization.

---

# 47. Pagination

Collection endpoints should support pagination.

Standard parameters:

```text
page
page_size
```

Example:

```text
?page=1&page_size=20
```

Recommended maximum:

```text
page_size <= 100
```

The exact maximum can be configured.

---

# 48. Pagination Response

Use:

```json
{
  "items": [],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5
  }
}
```

The frontend should not have to calculate pagination totals.

---

# 49. Filtering

Filters should use explicit query parameters.

Example:

```text
GET /faculty/me/sessions
    ?status=ACTIVE
    &class_id=UUID
```

Avoid generic JSON filter objects in query parameters unless the API genuinely requires them.

---

# 50. Sorting

Sorting should use an allowlisted field.

Example:

```text
?sort_by=marked_at&order=desc
```

The backend must map allowed values to known database columns.

Never directly interpolate arbitrary client-provided sort values into SQL.

---

# 51. Search

Search endpoints should support controlled search fields.

Example:

```text
GET /admin/students?search=soham
```

The backend determines which fields are searched.

For example:

```text
name
email
PRN
roll number
```

depending on the endpoint.

---

# 52. API Error Schema

All expected API errors should follow:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message."
  }
}
```

Optional:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "details": {}
  }
}
```

Do not expose internal stack traces.

---

# 53. Common Error Codes

Initial error codes:

```text
AUTH_REQUIRED
FORBIDDEN
RESOURCE_NOT_FOUND

INVALID_REQUEST
VALIDATION_ERROR

SESSION_NOT_FOUND
SESSION_NOT_ACTIVE
SESSION_EXPIRED
SESSION_CONFLICT

NOT_ENROLLED

LOCATION_UNAVAILABLE
LOCATION_OUTSIDE_RADIUS
LOCATION_ACCURACY_TOO_LOW

FACE_NOT_REGISTERED
FACE_NOT_DETECTED
FACE_NOT_VERIFIED
FACE_PROCESSING_FAILED

VERIFICATION_EXPIRED
VERIFICATION_INVALID
VERIFICATION_STEP_INVALID

ATTENDANCE_ALREADY_MARKED

RATE_LIMITED
```

New error codes should be documented before being introduced.

---

# 54. API Security Requirements

Every protected endpoint must establish:

```text
Authentication
      ↓
Authorization
      ↓
Resource authorization
      ↓
Validation
      ↓
Business logic
```

Sensitive endpoints additionally require:

```text
Rate limiting
```

---

# 55. TanStack Query Mapping

The frontend should map API resources to TanStack Query.

Example:

```text
GET /auth/me
        ↓
useCurrentUser()

GET /students/me/dashboard
        ↓
useStudentDashboard()

GET /attendance/sessions/active
        ↓
useActiveSessions()

GET /students/me/attendance
        ↓
useAttendanceHistory()

GET /attendance/sessions/{id}/attendance
        ↓
useSessionAttendance()
```

---

# 56. TanStack Mutation Mapping

Example:

```text
POST /students/me/face
        ↓
useRegisterFace()

POST /attendance/sessions
        ↓
useCreateAttendanceSession()

POST /attendance/sessions/{id}/end
        ↓
useEndAttendanceSession()

POST /attendance/verifications
        ↓
useStartVerification()

POST /attendance/verifications/{id}/location
        ↓
useVerifyLocation()

POST /attendance/verifications/{id}/face
        ↓
useVerifyFace()

POST /attendance/verifications/{id}/complete
        ↓
useCompleteAttendance()
```

---

# 57. Query Invalidation

After creating attendance:

```text id="0zv6b8"
Complete attendance
       ↓
Invalidate:
  active sessions
  student dashboard
  attendance summary
  attendance history
```

After ending a faculty session:

```text id="6g7i3b"
End session
       ↓
Invalidate:
  faculty dashboard
  session details
  session attendance
  session list
```

Avoid invalidating the entire query cache unnecessarily.

---

# 58. Optimistic Updates

Do not optimistically mark attendance as successful.

Attendance is security-sensitive and backend-authoritative.

Correct:

```text id="7f4n4x"
Submit
 ↓
Backend verifies
 ↓
Success
 ↓
Update UI
```

Incorrect:

```text id="j4r2v1"
Click
 ↓
Immediately show Present
 ↓
Backend may later fail
```

---

# 59. API Time Handling

All API timestamps should use ISO 8601 format.

Example:

```text
2026-08-08T10:32:00Z
```

The backend stores UTC.

The frontend formats dates/times for the user's local timezone.

---

# 60. Coordinate Representation

API coordinates should be numeric.

Example:

```json
{
  "latitude": 18.5204,
  "longitude": 73.8567,
  "accuracy_meters": 12.5
}
```

The backend validates ranges.

---

# 61. Face Upload Constraints

The face endpoint should define explicit limits.

Potential constraints:

```text
Maximum file size
Supported MIME types
Maximum dimensions
Minimum dimensions
Maximum processing time
```

Exact limits should be configured based on the selected face-processing implementation.

---

# 62. API Versioning

All public API routes use:

```text
/api/v1
```

If a breaking change becomes necessary:

```text
/api/v2
```

Do not silently introduce breaking changes into `/api/v1`.

---

# 63. Backward Compatibility

When changing an established API:

1. Determine whether the change is breaking.
2. Update `API.md`.
3. Update backend schemas.
4. Update frontend API types.
5. Update tests.
6. Update affected documentation.
7. Communicate the change to contributors/Codex.

---

# 64. API Documentation

FastAPI's OpenAPI documentation should remain enabled in development.

Useful development URLs:

```text
/docs
/redoc
/openapi.json
```

Production exposure should be evaluated based on the deployment/security model.

---

# 65. API Testing

Each endpoint should eventually have tests covering:

### Happy path

```text
Valid request → expected response
```

### Authentication

```text
Unauthenticated → 401
```

### Authorization

```text
Wrong role → 403
```

### Resource ownership

```text
Unauthorized resource → 403/404
```

### Validation

```text
Invalid input → 422
```

### Business rules

```text
Expired session → rejection
Duplicate attendance → 409
```

---

# 66. Attendance API Integration Test

The most important integration test should simulate:

```text
Student authentication
      ↓
Active session
      ↓
Student enrollment
      ↓
Start verification
      ↓
Location verification
      ↓
Face verification
      ↓
Complete verification
      ↓
Attendance created
```

Then attempt the same attendance again:

```text
Second attempt
      ↓
409 ATTENDANCE_ALREADY_MARKED
```

---

# 67. API Design Philosophy

The API should model **domain actions**, not simply database CRUD.

Good:

```text
POST /attendance/sessions/{id}/end
POST /attendance/verifications/{id}/location
POST /attendance/verifications/{id}/face
POST /attendance/verifications/{id}/complete
```

Less desirable:

```text
PATCH /sessions/{id}
PATCH /attendance/{id}
```

for security-sensitive workflow transitions.

---

# 68. Initial Endpoint Map

```text
AUTH
────────────────────────────────
GET    /auth/me
POST   /auth/logout


STUDENT
────────────────────────────────
GET    /students/me
GET    /students/me/dashboard
GET    /students/me/classes
GET    /students/me/attendance
GET    /students/me/attendance/summary
GET    /students/me/classes/{class_id}/attendance

GET    /students/me/face
POST   /students/me/face


SESSIONS
────────────────────────────────
GET    /attendance/sessions/active
GET    /attendance/sessions/{session_id}

POST   /attendance/sessions
POST   /attendance/sessions/{session_id}/end


VERIFICATION
────────────────────────────────
POST   /attendance/sessions/{session_id}/verification
POST   /attendance/verifications/{verification_id}/location
POST   /attendance/verifications/{verification_id}/face
POST   /attendance/verifications/{verification_id}/complete


FACULTY
────────────────────────────────
GET    /faculty/me
GET    /faculty/me/dashboard
GET    /faculty/me/classes
GET    /faculty/me/sessions
GET    /faculty/me/reports/attendance


LIVE ATTENDANCE
────────────────────────────────
GET    /attendance/sessions/{session_id}/attendance


ADMIN
────────────────────────────────
GET    /admin/students
POST   /admin/students
PATCH  /admin/students/{id}

GET    /admin/faculty
POST   /admin/faculty
PATCH  /admin/faculty/{id}

GET    /admin/classes
GET    /admin/subjects
GET    /admin/academic
```

This is the initial contract, not a demand to implement every endpoint immediately.

---

# 69. MVP Implementation Order

Implement APIs in this order:

## Phase 1 — Authentication

```text
/auth/me
/auth/logout
```

## Phase 2 — Student/Faculty identity

```text
/students/me
/faculty/me
```

## Phase 3 — Academic data

```text
/classes
/students/me/classes
/faculty/me/classes
```

## Phase 4 — Face registration

```text
/students/me/face
```

## Phase 5 — Attendance sessions

```text
POST /attendance/sessions
GET /attendance/sessions/active
GET /attendance/sessions/{id}
POST /attendance/sessions/{id}/end
```

## Phase 6 — Verification

```text
POST /attendance/sessions/{id}/verification
POST /attendance/verifications/{id}/location
POST /attendance/verifications/{id}/face
POST /attendance/verifications/{id}/complete
```

## Phase 7 — Attendance/history

```text
/students/me/attendance
/attendance/sessions/{id}/attendance
```

## Phase 8 — Reports/admin

Implement after the core workflow is stable.

---

# 70. API Contract Rule for Codex

Before implementing or changing an endpoint, Codex should:

1. Read `PRODUCT.md`.
2. Read `ARCHITECTURE.md`.
3. Read `DATABASE.md`.
4. Read `SECURITY.md`.
5. Read this `API.md`.
6. Determine whether the endpoint already exists.
7. Reuse existing conventions.
8. Update this document if the contract changes.
9. Add/update tests.
10. Avoid introducing duplicate endpoints.

---

# 71. Current API Status

The conceptual API contract is defined.

Not yet finalized:

* Exact OAuth callback routes
* Exact session mechanism
* Exact face upload format
* Exact face model
* Exact verification challenge implementation
* Exact Arcjet configuration
* Admin API depth
* WebSocket/SSE decision
* Export endpoints

These should be finalized during implementation based on actual requirements.

---

# 72. Related Documentation

* `PRODUCT.md` — Product requirements
* `ARCHITECTURE.md` — Technical architecture
* `DATABASE.md` — Database design
* `UI.md` — UI/UX specification
* `SECURITY.md` — Security requirements
* `AGENTS.md` — Coding-agent instructions
