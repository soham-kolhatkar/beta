# GeoAttend — Product Specification

> A secure, location-aware attendance platform using facial recognition for fast, reliable classroom attendance.

---

## 1. Product Overview

GeoAttend is a web-based attendance management system designed for educational institutions.

The system combines:

* Google OAuth authentication
* Academic/class management
* Geolocation verification
* Facial recognition
* Attendance sessions
* Real-time attendance monitoring
* Attendance history and analytics
* Role-based access control
* Rate limiting and security controls

The primary objective is to make attendance:

1. **Fast** for students
2. **Simple** for faculty
3. **Difficult to falsify**
4. **Easy to monitor**
5. **Auditable**
6. **Mobile-friendly**

The system should feel like a modern productivity application rather than a traditional college administration portal.

---

# 2. Product Goals

## 2.1 Primary Goals

### G1 — Fast attendance

A student should be able to go from opening the application to successfully marking attendance with minimal interaction.

Target experience:

```text
Open application
      ↓
See active class
      ↓
Verify location
      ↓
Verify face
      ↓
Attendance marked
```

The student should not have to navigate through multiple administrative pages to perform the primary attendance action.

---

### G2 — Prevent proxy attendance

Attendance should require multiple independent validations:

```text
Authenticated user
        +
Active session
        +
Class membership
        +
Valid location
        +
Face verification
        ↓
Attendance
```

No single client-side signal should be sufficient to mark attendance.

---

### G3 — Make faculty attendance management simple

Faculty should be able to:

* Create an attendance session
* Define the attendance location
* Define an allowed radius
* Set the session duration
* Monitor attendance in real time
* Inspect verification results
* End a session
* View historical attendance
* Generate reports

---

### G4 — Provide useful attendance insights

Students should easily understand:

* Overall attendance percentage
* Subject-wise attendance
* Recent attendance
* Missed classes
* Attendance risk

Faculty should be able to understand:

* Session attendance
* Student attendance
* Subject/class attendance
* Attendance trends
* Verification failures

---

# 3. User Roles

The system has three primary roles.

## 3.1 Student

Students use GeoAttend primarily to:

* Authenticate with Google
* Complete their profile
* Register their face
* View their classes
* View active attendance sessions
* Mark attendance
* View attendance history
* View attendance percentage

Students should have a **mobile-first experience**.

---

## 3.2 Faculty

Faculty use GeoAttend primarily to:

* Authenticate with Google
* Manage assigned classes
* Create attendance sessions
* Set attendance location
* Set attendance radius
* Monitor live attendance
* View verification details
* View attendance history
* Generate attendance reports

Faculty experience should be optimized for desktop/tablet while remaining responsive.

---

## 3.3 Admin

Administrators manage institutional data.

Admin capabilities include:

* Manage students
* Manage faculty
* Manage subjects
* Manage classes
* Manage branches
* Manage divisions
* Manage academic years
* Assign faculty to classes
* Assign students to classes
* View institution-wide attendance
* Manage system-level configuration

Admin functionality may initially be limited while the MVP focuses on Student and Faculty workflows.

---

# 4. Authentication

Google OAuth is the primary authentication mechanism.

Users authenticate through Google rather than creating a separate application password.

Authentication establishes the user's identity.

Authorization is determined by GeoAttend's own database.

Conceptually:

```text
Google
  ↓
Authenticated identity
  ↓
GeoAttend user
  ↓
Role
  ├── STUDENT
  ├── FACULTY
  └── ADMIN
```

The system must not assume that a Google account automatically has a particular application role.

---

# 5. Academic Structure

GeoAttend models the academic structure of an institution.

The expected hierarchy is:

```text
Institution
    │
    └── Academic Year
          │
          └── Branch
                │
                └── Division
                      │
                      └── Students
                            │
                            └── Classes / Subjects
                                  │
                                  └── Faculty
```

The exact database representation will be defined in `DATABASE.md`.

Students should be associated with their academic context so that faculty can create attendance sessions for the correct class.

---

# 6. Attendance Session

An attendance session represents one specific opportunity to mark attendance.

A faculty member creates a session containing at minimum:

* Class
* Subject
* Faculty
* Start time
* End time
* Latitude
* Longitude
* Allowed radius
* Session status

Example:

```text
Subject: Database Management Systems
Class: CSAI - Division A

Start: 10:00 AM
End:   11:00 AM

Location:
Latitude: 18.xxxxx
Longitude: 73.xxxxx

Radius:
100 meters

Status:
ACTIVE
```

---

# 7. Session Lifecycle

A session follows a controlled lifecycle.

```text
CREATED
   ↓
ACTIVE
   ↓
ENDED
```

A session may also expire automatically:

```text
ACTIVE
   ↓
TIME EXPIRED
   ↓
ENDED
```

Students cannot mark attendance for:

* Future sessions
* Ended sessions
* Expired sessions
* Sessions they are not enrolled in

---

# 8. Student Attendance Flow

The intended student flow is:

```text
Login
  ↓
Student Dashboard
  ↓
View active/upcoming class
  ↓
Select attendance session
  ↓
Check session eligibility
  ↓
Request device location
  ↓
Validate location
  ↓
Capture face
  ↓
Perform face verification
  ↓
Validate attendance request
  ↓
Create attendance record
  ↓
Show success
```

The student should receive clear feedback at every stage.

Example states:

```text
Checking location...
Location verified ✓

Preparing camera...
Face detected ✓

Verifying identity...
Identity verified ✓

Attendance marked ✓
```

Failure states must also explain what happened without exposing sensitive implementation details.

---

# 9. Location Verification

The browser provides the student's current location.

The client should provide:

* Latitude
* Longitude
* Location accuracy

The backend is responsible for determining whether the student is inside the attendance area.

The frontend must never be treated as authoritative for location validation.

Example:

```text
Student location
      ↓
FastAPI
      ↓
Calculate distance from session location
      ↓
Compare with allowed radius
      ↓
Valid / Invalid
```

Location accuracy should also be considered.

A location report with extremely poor accuracy should not automatically be accepted simply because the reported coordinates fall within the radius.

---

# 10. Face Registration

A student must register their face before using face-based attendance.

Expected flow:

```text
Student
   ↓
Face Registration
   ↓
Camera permission
   ↓
Face detection
   ↓
Capture suitable face
   ↓
Generate face representation
   ↓
Store representation securely
```

The exact face recognition model and storage mechanism are technical decisions and will be documented separately.

Raw photographs should not be retained unnecessarily.

---

# 11. Face Verification

During attendance:

```text
Live camera input
       ↓
Face detection
       ↓
Face representation
       ↓
Compare with registered identity
       ↓
Verification result
```

The backend is responsible for the authoritative verification result.

The frontend must not be able to submit:

```text
faceVerified: true
```

and have that accepted as proof of identity.

---

# 12. Liveness Detection

Basic face matching is not considered sufficient long-term because a user could potentially present a photograph or replayed image.

Therefore:

### MVP

Face verification may initially be implemented without advanced liveness detection to simplify development and validate the overall product.

### Future security phase

Add liveness / anti-spoofing protection.

Potential flow:

```text
Camera
  ↓
Face detected
  ↓
Liveness verification
  ↓
Face identity verification
  ↓
Attendance
```

Liveness implementation will be evaluated separately based on accuracy, performance, privacy, licensing and deployment requirements.

---

# 13. Attendance Creation Rules

Attendance can only be created when all required conditions pass.

```text
Authenticated
    AND
Active session
    AND
Student belongs to class
    AND
Within allowed location
    AND
Acceptable location accuracy
    AND
Face verified
    AND
No previous attendance
```

If any required condition fails, attendance must not be created.

---

# 14. Duplicate Attendance

A student must not be able to mark attendance more than once for the same session.

The system must enforce this at the database level.

Logical rule:

```text
(session_id, student_id)
```

must be unique.

Frontend prevention is useful for UX but is not sufficient for security.

---

# 15. Attendance Record

An attendance record should contain enough information to audit how attendance was created.

Potential information:

```text
Student
Session
Timestamp

Location
Distance from session location
GPS accuracy

Face verification result
Face similarity/confidence

Verification status
```

The exact schema will be defined in `DATABASE.md`.

---

# 16. Faculty Live Attendance

While a session is active, faculty should be able to monitor attendance.

Example:

```text
DBMS — Division A

48 Students

42 Present
4 Absent
2 Pending

██████████████████░░
```

Faculty should be able to search students by:

* Name
* PRN
* Roll number

Selecting a student's attendance should expose relevant verification information.

Example:

```text
Student: Aarav Sharma

Attendance:
Present

Location:
Verified — 34m

GPS Accuracy:
12m

Face:
Verified

Marked:
10:31:42 AM
```

---

# 17. Attendance Statuses

The system should distinguish between different states.

Possible attendance states:

```text
PRESENT
ABSENT
PENDING
FAILED
```

However, the final status model should be kept as simple as possible.

A verification failure should not necessarily become a permanent attendance status unless there is a business reason to retain it.

Detailed verification events may instead be stored separately for auditing.

---

# 18. Student Dashboard

The student dashboard should prioritize information students need most frequently.

Primary information:

```text
Student identity

Today's classes
Upcoming class

Overall attendance

Subject-wise attendance

Recent attendance

Attendance warnings
```

The primary action should be immediately visible when an attendance session is active.

The experience should be mobile-first.

---

# 19. Faculty Dashboard

The faculty dashboard should prioritize:

```text
Today's classes

Upcoming sessions

Active session

Live attendance

Recent attendance

Attendance statistics
```

The most important action should be:

```text
Create / Start Attendance Session
```

when an appropriate class is scheduled.

---

# 20. Admin Dashboard

The admin dashboard should prioritize institution-level management:

```text
Students
Faculty
Classes
Subjects
Academic structure
Attendance
Reports
Analytics
```

Admin interfaces can be more information-dense than the student experience.

---

# 21. UI/UX Principles

GeoAttend should not look like a traditional college administration portal.

The design should be:

* Modern
* Clean
* Minimal
* Responsive
* Accessible
* Mobile-first for students
* Information-dense for faculty/admin
* Fast to navigate
* Clear about system state

Tailwind CSS will be used for styling.

Reusable UI primitives may be used, but the final design language should be specific to GeoAttend.

---

# 22. Core UX Principle

The system should minimize unnecessary interaction.

### Student

```text
Open
  ↓
See class
  ↓
Verify
  ↓
Done
```

### Faculty

```text
Open
  ↓
See today's classes
  ↓
Start session
  ↓
Monitor
  ↓
Finish
```

### Admin

```text
Open
  ↓
Understand institution
  ↓
Manage
  ↓
Investigate
  ↓
Report
```

---

# 23. Security Principles

The backend must be authoritative.

The client must never be trusted for:

* User role
* Attendance validity
* Location validity
* Face verification result
* Session validity
* Duplicate prevention

Security mechanisms include:

* Google OAuth
* Backend authorization
* Server-side location validation
* Face verification
* Database constraints
* Rate limiting
* Audit information
* Input validation
* Secure environment variables

Arcjet will be used for rate limiting and relevant security controls.

---

# 24. Privacy Principles

GeoAttend handles sensitive information such as:

* Identity information
* Location information
* Face representations
* Attendance records

Therefore:

1. Collect only information necessary for the application.
2. Avoid storing raw facial photographs unnecessarily.
3. Do not continuously track students by default.
4. Location should primarily be collected during attendance verification.
5. Access to attendance and identity information must be role-restricted.
6. Sensitive credentials and secrets must never be committed to the repository.
7. Retention policies should be defined before production deployment.

---

# 25. MVP Scope

The first production-oriented MVP will include:

### Authentication

* Google OAuth
* User creation
* Role-based access

### Academic structure

* Students
* Faculty
* Subjects
* Classes
* Divisions
* Academic year

### Student

* Dashboard
* Profile
* Face registration
* Active attendance
* Location verification
* Face verification
* Attendance history
* Attendance percentage

### Faculty

* Dashboard
* Classes
* Create attendance session
* Start/end session
* Live attendance
* Attendance history
* Basic reports

### Security

* Backend authorization
* Duplicate attendance protection
* Location validation
* Face verification
* Arcjet rate limiting
* Audit information

---

# 26. Post-MVP Features

The following should not block MVP development.

### Phase 2

* Liveness detection
* Advanced attendance analytics
* CSV/Excel export
* Attendance trends
* Low-attendance warnings
* Notifications
* Better session scheduling
* Faculty attendance corrections with audit trail

### Phase 3

* Institution-wide administration
* Multiple institutions
* Advanced reporting
* Automated timetable integration
* Email/push notifications
* Advanced anti-proxy detection
* Attendance anomaly detection

---

# 27. Explicitly Out of Scope for Initial MVP

The following should not be implemented unless explicitly approved:

* Continuous student location tracking
* Background GPS tracking
* Complex AI attendance prediction
* Automatic attendance correction
* Facial identification across the entire student population
* Native Android/iOS applications
* Chat functionality
* Payment functionality
* Unnecessary social features

The MVP should remain focused on:

```text
Identity
+
Location
+
Face
+
Attendance
```

---

# 28. Product Success Criteria

The MVP should satisfy the following:

### Student

A student can:

```text
Login
→ identify today's class
→ verify location
→ verify face
→ mark attendance
→ view attendance history
```

without unnecessary navigation.

### Faculty

A faculty member can:

```text
Login
→ select class
→ create session
→ monitor attendance
→ inspect verification
→ finish session
```

without manual attendance entry for normal attendance.

### Security

The system must reject:

```text
Unauthenticated requests
Expired sessions
Students outside the allowed location
Students not belonging to the class
Unverified faces
Duplicate attendance
Rate-limit abuse
```

### Reliability

The system should maintain a clear audit trail for attendance creation and verification.

---

# 29. Product Philosophy

GeoAttend is not intended to be merely a digital replacement for a paper attendance register.

The goal is to create a **fast verification system** where attendance becomes a natural part of the classroom workflow.

The product should always optimize for:

> **Less effort for legitimate users, more confidence for faculty, and stronger resistance to fraudulent attendance.**
