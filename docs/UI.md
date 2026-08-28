# GeoAttend — UI/UX Specification

## 1. Purpose

This document defines the UI/UX direction for GeoAttend.

The objective is not to reproduce a traditional college administration portal.

GeoAttend should feel like a modern, focused productivity application where:

* Students can understand their attendance immediately.
* Students can mark attendance with minimal interaction.
* Faculty can start and monitor sessions quickly.
* Administrators can understand institutional attendance at a glance.
* Verification states are transparent and understandable.
* Mobile interaction is treated as a first-class experience.

Tailwind CSS is the primary styling system.

---

# 2. UX Research Summary

Research into current attendance products and student experiences reveals several recurring patterns.

### Existing systems commonly provide

* Attendance dashboards
* Subject/class-wise attendance
* Live attendance
* Geofencing
* Face recognition
* Reports
* Role-specific interfaces
* Attendance analytics

Current products such as Presence 360, AttendTrack, Accura, Face Attendance and Presentify demonstrate variations of these patterns.

### Important UX observation

Students generally care about:

```text
How much attendance do I have?
What is my next class?
Am I present today?
Can I mark attendance right now?
```

They generally do not want to navigate through several administrative screens to answer these questions.

Recent student feedback around attendance applications specifically highlights the value of showing current/next class, timetable and attendance status immediately.

Therefore, GeoAttend will use an **attendance-first information hierarchy**.

---

# 3. Core UX Philosophy

GeoAttend follows five principles.

## 3.1 Show, don't make users search

Important information should be visible without unnecessary navigation.

Student opening the app:

```text
Today's classes
        ↓
Current / next class
        ↓
Attendance status
        ↓
Primary action
```

---

## 3.2 One primary action per screen

Every important screen should have one visually dominant action.

Examples:

```text
Student dashboard
→ Mark Attendance

Faculty dashboard
→ Start Session

Active session
→ View Live Attendance
```

Secondary actions should visually recede.

---

## 3.3 Verification should feel like a guided process

Do not expose technical details such as:

```text
POST /attendance/verify
embedding distance = 0.31
```

Instead communicate meaningful states:

```text
Checking your location...

✓ You're within the classroom area.

Preparing camera...

✓ Face detected.

Verifying identity...

✓ Identity verified.

Attendance marked.
```

---

## 3.4 Errors should tell users what to do

Avoid:

```text
Error: LOCATION_VALIDATION_FAILED
```

Prefer:

```text
You're outside the attendance area.

Move closer to the classroom and try again.
```

For poor GPS accuracy:

```text
Your location isn't accurate enough.

Move near a window or outdoors for a moment,
then try again.
```

For face problems:

```text
We can't get a clear view of your face.

Try:
• Moving into better lighting
• Holding your phone at eye level
• Moving slightly farther from the camera
```

---

## 3.5 Don't make security invisible

Users should understand that verification is happening.

For example:

```text
LOCATION
✓ Verified

IDENTITY
✓ Verified
```

This increases confidence in the system.

---

# 4. Role-Specific UX

GeoAttend has three distinct experiences.

```text
                 GeoAttend
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
       Student    Faculty     Admin
          │          │          │
      Mobile      Desktop     Desktop
       first       first       first
```

---

# 5. Student Experience

## 5.1 Design Priority

The student experience is:

**Mobile-first.**

Students will primarily use their phones to:

* Check attendance
* View today's classes
* Mark attendance
* View attendance history

The interface should remain highly usable on desktop, but mobile interaction takes priority.

---

# 6. Student Navigation

Mobile navigation should remain minimal.

Recommended:

```text
┌─────────────────────────────────┐
│                                 │
│         Page content            │
│                                 │
│                                 │
├────────┬────────┬────────┬──────┤
│ Home   │ Attend │History │ More │
└────────┴────────┴────────┴──────┘
```

Potential primary navigation:

```text
Home
Attendance
History
Profile
```

Do not introduce a large sidebar on mobile.

---

# 7. Student Dashboard

The dashboard should answer the student's most important questions immediately.

Recommended hierarchy:

```text
┌──────────────────────────────────────┐
│ Good morning, Soham                  │
│ CSAI • Third Year • Division A       │
└──────────────────────────────────────┘

TODAY
────────────────────────────────────────

┌──────────────────────────────────────┐
│ CURRENT CLASS                        │
│                                      │
│ Database Management Systems          │
│ 10:00 AM • Room 304                  │
│                                      │
│ ● Attendance is open                 │
│                                      │
│        [ Mark Attendance ]            │
└──────────────────────────────────────┘


ATTENDANCE
────────────────────────────────────────

Overall
     82%

┌────────────┬────────────┬────────────┐
│ DBMS       │ OS         │ AI         │
│ 82%        │ 76%        │ 91%        │
│            │            │            │
└────────────┴────────────┴────────────┘


TODAY'S CLASSES
────────────────────────────────────────

09:00  Operating Systems       ✓ Present
10:00  DBMS                    ● Open
12:00  Computer Networks       ○ Upcoming
14:00  AI                      ○ Upcoming
```

The exact visual treatment will be established in the design system.

---

# 8. Attendance Percentage

Attendance percentage should not be presented only as a number.

It should have context.

Example:

```text
DBMS

82%

42 / 51 classes

Healthy
```

For a lower percentage:

```text
Operating Systems

68%

34 / 50 classes

Needs attention
```

The system should avoid relying solely on red/green color.

Use:

* percentage
* label
* icon/state
* optional trend

This improves accessibility.

---

# 9. Attendance Risk

Students should understand when attendance requires attention.

Example:

```text
⚠ Attendance needs attention

Operating Systems — 68%

You may need to attend the next
3 classes to return above 75%.
```

This is more useful than simply coloring `68%` red.

Attendance prediction/calculation can be implemented later.

---

# 10. Active Attendance Card

When a session is active, it should become the dominant dashboard element.

Example:

```text
┌──────────────────────────────────────┐
│ ● ATTENDANCE OPEN                    │
│                                      │
│ Database Management Systems          │
│ Division A                           │
│ Prof. XYZ                            │
│                                      │
│ Closes in 08:32                      │
│                                      │
│          [ Mark Attendance ]         │
└──────────────────────────────────────┘
```

The action should be impossible to miss without becoming visually aggressive.

---

# 11. Student Attendance Flow

The attendance flow should use a focused full-screen or near-full-screen experience.

Recommended sequence:

```text
Session
  ↓
Location
  ↓
Face
  ↓
Verification
  ↓
Success
```

The student should not be navigating the normal application during this process.

---

# 12. Attendance Step 1 — Session

Show:

```text
Database Management Systems

Prof. XYZ
Division A

Attendance closes in 08:32

[ Continue ]
```

If the session is invalid:

```text
This attendance session is no longer active.

[ Back to Dashboard ]
```

---

# 13. Attendance Step 2 — Location

The interface should make the location check understandable.

Example:

```text
┌──────────────────────────────────────┐
│                                      │
│              LOCATION                │
│                                      │
│                 ◉                    │
│              You are                 │
│               34 m                   │
│            from the class            │
│                                      │
│       ✓ Location verified            │
│                                      │
│              [ Continue ]            │
└──────────────────────────────────────┘
```

The UI should not require users to understand latitude/longitude.

---

# 14. Location Loading State

Example:

```text
Finding your location...

This may take a few seconds.
```

A progress indicator should communicate that the system is actively working.

Avoid indefinite spinners with no explanation.

---

# 15. Location Failure State

Example:

```text
We couldn't verify your location.

You're currently outside the
attendance area.

Move closer to the classroom
and try again.

[ Try Again ]
```

For accuracy:

```text
Your location signal is too weak.

Move to an area with a clearer
GPS signal and try again.

[ Try Again ]
```

---

# 16. Attendance Step 3 — Face Verification

The face capture interface should actively guide the student.

Example:

```text
┌──────────────────────────────────────┐
│                                      │
│            Verify Identity           │
│                                      │
│        ┌──────────────────┐          │
│        │                  │          │
│        │     CAMERA       │          │
│        │                  │          │
│        │        ◯         │          │
│        │                  │          │
│        └──────────────────┘          │
│                                      │
│        Keep your face centered       │
│                                      │
└──────────────────────────────────────┘
```

---

# 17. Face Guidance

The UI should guide the user before submitting an image.

Possible states:

```text
No face detected
```

```text
Face detected
```

```text
Move slightly closer
```

```text
Move slightly farther away
```

```text
Improve lighting
```

```text
Hold still
```

This is important because real-world face recognition can be affected by lighting, distance and capture quality. User reports from recent face-attendance implementations specifically describe these problems.

---

# 18. Face Capture

Avoid making the student press:

```text
[ Take Photo ]
```

if automatic capture can reliably be used.

Preferred experience:

```text
Face detected
      ↓
Face aligned
      ↓
Conditions acceptable
      ↓
Capture automatically
```

The implementation should still provide a manual fallback if automatic capture fails.

---

# 19. Verification State

After capture:

```text
Verifying your identity...

Please hold still.
```

Do not show technical similarity scores to students.

---

# 20. Attendance Success

Success should feel definitive.

```text
┌──────────────────────────────────────┐
│                                      │
│                  ✓                   │
│                                      │
│        Attendance marked             │
│                                      │
│        Database Management           │
│        Systems                       │
│                                      │
│        Today • 10:32 AM              │
│                                      │
│        Location ✓                    │
│        Identity ✓                    │
│                                      │
│           [ Done ]                   │
│                                      │
└──────────────────────────────────────┘
```

The success screen should not expose unnecessary technical information.

---

# 21. Attendance Failure

If face verification fails:

```text
We couldn't verify your identity.

Make sure your face is clearly visible
and try again.

Attempts remaining: 2

[ Try Again ]
```

If repeated failures occur, the system may require faculty assistance.

The UI should never reveal sensitive matching thresholds.

---

# 22. Student History

Attendance history should prioritize usability.

Recommended filters:

```text
All
Present
Absent
```

and:

```text
Subject
Date range
```

Example:

```text
AUGUST 2026

08 Aug
DBMS
✓ Present
10:32 AM

08 Aug
OS
✓ Present
09:02 AM

07 Aug
AI
✕ Absent
```

Avoid unnecessarily complex calendar interfaces initially.

---

# 23. Student Subject Detail

Selecting a subject:

```text
DBMS

82%

42 / 51 classes

────────────────────

Recent attendance

08 Aug     ✓
06 Aug     ✓
04 Aug     ✕
01 Aug     ✓
```

Optional later:

```text
Attendance trend
```

---

# 24. Faculty Experience

Faculty needs a different information density.

Faculty should primarily answer:

```text
What classes do I have today?

Is a session active?

How many students are present?

Who has not attended?

Did verification fail for anyone?

```

---

# 25. Faculty Navigation

Desktop:

```text
┌──────────────┬─────────────────────────────────────┐
│              │                                     │
│ GeoAttend    │                                     │
│              │                                     │
│ Dashboard    │            Page content              │
│ Classes      │                                     │
│ Sessions     │                                     │
│ Attendance   │                                     │
│ Reports      │                                     │
│              │                                     │
│ Settings     │                                     │
│              │                                     │
└──────────────┴─────────────────────────────────────┘
```

The sidebar should remain compact.

Avoid filling it with every conceivable feature.

---

# 26. Faculty Dashboard

Recommended structure:

```text
Good morning, Professor

TODAY
────────────────────────────────────────

3 Classes
1 Active
2 Upcoming


ACTIVE SESSION

┌─────────────────────────────────────────┐
│ DBMS • Division A                       │
│                                         │
│ 42 / 48 Present                         │
│                                         │
│ ███████████████████░░░                  │
│                                         │
│ Started 10:00 AM                        │
│                                         │
│ [ View Live Attendance ]                │
└─────────────────────────────────────────┘


TODAY'S CLASSES

09:00  Operating Systems      Completed
10:00  DBMS                   Active
14:00  AI                     Upcoming
```

---

# 27. Create Session

Creating a session should be short.

Step 1:

```text
Create Attendance Session

Class
[ DBMS • Division A ]

Duration
[ 10:00 ] — [ 11:00 ]

Location
[ Use Current Location ]

Radius
[ 100 m ]

[ Start Session ]
```

Do not expose unnecessary technical configuration.

Advanced options can be hidden.

---

# 28. Location Selection for Faculty

Faculty should see their current location before creating the session.

Example:

```text
Class location

       ● You are here

Accuracy: ±12 m

[ Use this location ]
```

The faculty should be able to adjust the radius.

Suggested defaults can be configured institution-wide later.

---

# 29. Active Faculty Session

This is one of the most important screens in the application.

Recommended layout:

```text
DBMS • Division A

● LIVE

42 / 48 Present

██████████████████░░


PRESENT
────────────────────────

✓ Aarav Sharma
✓ Aditya Patil
✓ Ananya Joshi
...


PENDING / NOT VERIFIED
────────────────────────

○ Rohit Kulkarni
○ Sneha Patil


FAILED
────────────────────────

⚠ Rahul Shah
   Face verification failed
```

---

# 30. Live Attendance Statistics

At the top:

```text
48 Students

42 Present
4 Not Marked
2 Verification Issues
```

Use compact summary cards.

Do not create a dashboard with ten unrelated charts.

---

# 31. Live Attendance Search

Faculty should be able to search:

```text
[ Search name / PRN ]
```

The list should update immediately.

Filters:

```text
All
Present
Not Marked
Failed
```

This is more useful during a live session than a complicated analytics chart.

---

# 32. Student Verification Detail

Faculty selecting a student should see:

```text
Aarav Sharma
PRN: 123456

Attendance
✓ Present

Location
✓ Verified
34 m from session

GPS Accuracy
12 m

Identity
✓ Verified

Marked
10:31:42 AM
```

Technical face similarity values should be optional/role-restricted rather than displayed prominently.

---

# 33. Verification Failure Detail

Example:

```text
Rohit Kulkarni

Status
⚠ Verification failed

Location
✓ Verified — 28 m

Identity
✕ Could not verify

Last attempt
10:32:18 AM

[ Allow Retry ]
```

Faculty should be able to understand the failure without needing technical knowledge.

---

# 34. Faculty Attendance History

Faculty should be able to navigate:

```text
Class
 ↓
Date
 ↓
Session
 ↓
Attendance
```

Example:

```text
DBMS • Division A

08 Aug 2026
48 students
42 present

06 Aug 2026
48 students
45 present

04 Aug 2026
48 students
47 present
```

---

# 35. Reports

Reports should be action-oriented.

Useful initial reports:

```text
Class attendance
Student attendance
Subject attendance
Date-range attendance
```

Later:

```text
Low-attendance students
Attendance trends
Faculty statistics
Verification failure rate
```

---

# 36. Admin Experience

Admin UI is information-dense but should remain clean.

Primary navigation:

```text
Dashboard
Students
Faculty
Classes
Subjects
Academic Structure
Attendance
Reports
Settings
```

---

# 37. Admin Dashboard

The admin dashboard should answer:

```text
How is attendance doing across the institution?

Are there problematic classes?

Are students falling below attendance requirements?

Are there unusual verification failures?
```

Example:

```text
Institution Overview

Students          2,480
Faculty             126
Classes              84
Today's Sessions     63


Attendance Today

92% Present


At Risk

124 students


Verification Issues

18 attempts
```

---

# 38. Dashboard Design Rule

Avoid "dashboard decoration."

Every visualization must answer a question.

Bad:

```text
Random pie chart
Random line chart
Random KPI
```

Good:

```text
What percentage of students are present today?

Which subjects have low attendance?

Which classes have unusual verification failures?
```

---

# 39. Responsive Strategy

Three primary breakpoints:

```text
Mobile
Tablet
Desktop
```

The exact Tailwind breakpoints should use the framework defaults unless a real design requirement justifies customization.

---

# 40. Mobile Rules

On mobile:

* Prioritize one primary action.
* Use bottom navigation for students where appropriate.
* Avoid dense tables.
* Convert tables into cards/lists when necessary.
* Use full-screen camera flows.
* Keep buttons comfortably tappable.
* Avoid horizontal scrolling wherever possible.
* Keep critical information above the fold.

---

# 41. Tablet Rules

Tablet should support:

* Faculty live attendance
* Student dashboards
* Session creation

The layout may transition from mobile cards to denser two-column layouts.

---

# 42. Desktop Rules

Desktop should support:

* Faculty dashboard
* Live attendance
* Admin dashboard
* Reports
* Tables
* Analytics

Use available screen width but preserve readable content widths.

---

# 43. Tailwind Design System

The UI should be built using Tailwind CSS.

The design system should define:

```text
Typography
Spacing
Colors
Border radius
Shadows
Buttons
Inputs
Cards
Badges
Tables
Dialogs
Navigation
Status indicators
```

Avoid arbitrary styling scattered across components.

---

# 44. Color Philosophy

Use a restrained neutral foundation.

Suggested semantic categories:

```text
Neutral
General UI

Primary
Main actions

Success
Verified / Present

Warning
Pending / Attention

Danger
Failed / Invalid

Info
Informational state
```

Do not make every dashboard card a different color.

Color should communicate state, not decoration.

---

# 45. Accessibility

The UI must not depend only on color.

For example:

Bad:

```text
Green = Present
Red = Absent
```

Better:

```text
✓ Present
✕ Absent
```

with color supporting the meaning.

Additional requirements:

* Keyboard navigation
* Visible focus states
* Semantic HTML
* Accessible labels
* Sufficient contrast
* Camera/location permission explanations
* Screen-reader-friendly status messages

---

# 46. Typography

Use a modern sans-serif typeface.

Typography hierarchy should be restrained:

```text
Page title
Section heading
Card title
Body
Secondary information
Caption
```

Avoid excessive font sizes and decorative headings.

The UI should feel professional rather than promotional.

---

# 47. Cards

Cards should be used when grouping meaningful information.

Good uses:

```text
Active attendance
Attendance summary
Upcoming class
Verification status
```

Bad uses:

```text
Every piece of text inside a card
```

Avoid excessive nested cards.

---

# 48. Tables

Tables are appropriate for:

* Faculty attendance
* Admin student lists
* Reports
* Historical sessions

They are not ideal for the primary mobile student experience.

On mobile, tables should become:

```text
List
 ↓
Student card
 ↓
Details
```

---

# 49. Loading States

Every asynchronous operation must have an intentional loading state.

Examples:

```text
Loading today's classes...
Checking your location...
Preparing camera...
Verifying identity...
Loading attendance...
```

Avoid generic:

```text
Loading...
```

whenever a more meaningful message is possible.

---

# 50. Empty States

Empty states should explain why the screen is empty.

Example:

```text
No active attendance sessions

Your faculty hasn't started
attendance yet.

Check back when your class begins.
```

Not:

```text
No data.
```

---

# 51. Error States

Error states should contain:

1. What happened
2. Why it matters
3. What the user can do

Example:

```text
Location couldn't be verified

You're approximately 180 m away
from the attendance area.

Move closer to the classroom
and try again.

[ Try Again ]
```

---

# 52. Permission UX

Browser permissions are critical.

For location:

```text
We need your location to verify
that you're in the classroom.

Your location is checked only
when you mark attendance.

[ Allow Location ]
```

For camera:

```text
We need camera access to verify
your identity.

Your camera is used only during
face verification.

[ Allow Camera ]
```

The system should explain permissions before triggering them where possible.

---

# 53. Camera UX

The camera screen should include:

* Clear face positioning guidance
* Lighting guidance
* Distance guidance
* Permission status
* Processing state
* Retry state

Avoid cluttering the camera view with unnecessary UI.

---

# 54. Verification Progress

Use a clear step indicator.

Example:

```text
● Location ─── ○ Identity ─── ○ Complete
```

During face verification:

```text
✓ Location ─── ● Identity ─── ○ Complete
```

On success:

```text
✓ Location ─── ✓ Identity ─── ✓ Complete
```

This helps users understand where they are in the process.

---

# 55. Notifications and Toasts

Use toast notifications for short-lived events:

```text
Attendance marked
Session created
Profile updated
```

Do not use toasts for important information that must remain visible.

Important errors should appear inline.

---

# 56. Motion

Use subtle transitions.

Appropriate:

* Page transitions
* Card expansion
* Verification progress
* Success confirmation
* Modal transitions

Avoid excessive:

* bouncing
* parallax
* animated backgrounds
* decorative motion

Attendance is a utility workflow; speed and clarity are more important than visual spectacle.

---

# 57. Design Language

GeoAttend should feel:

```text
Modern
        +
Calm
        +
Trustworthy
        +
Fast
        +
Professional
```

It should not feel:

```text
Corporate HR portal
        or
Old college ERP
        or
AI gimmick
```

---

# 58. Visual Differentiation

The product should communicate its core idea visually:

```text
Presence
+
Verification
+
Location
```

But these concepts should appear through subtle status indicators and interaction design rather than giant:

```text
AI FACE RECOGNITION!!!
GPS!!!
```

marketing-style elements inside the application.

---

# 59. Recommended Student Information Hierarchy

When the student opens the app:

```text
1. Identity / greeting
2. Current or next class
3. Attendance action
4. Overall attendance
5. Subject attendance
6. Today's schedule
7. Recent activity
```

---

# 60. Recommended Faculty Information Hierarchy

When faculty opens the app:

```text
1. Today's schedule
2. Active session
3. Present count
4. Session action
5. Student verification status
6. Recent sessions
7. Reports
```

---

# 61. Recommended Admin Information Hierarchy

When admin opens the app:

```text
1. Institution overview
2. Today's attendance
3. At-risk students
4. Active sessions
5. Verification anomalies
6. Academic management
7. Reports
```

---

# 62. MVP UI Pages

## Authentication

```text
/login
```

---

## Student

```text
/student/dashboard
/student/attendance
/student/attendance/[sessionId]
/student/history
/student/profile
/student/face-registration
```

---

## Faculty

```text
/faculty/dashboard
/faculty/classes
/faculty/sessions
/faculty/sessions/[sessionId]
/faculty/attendance
/faculty/reports
```

---

## Admin

```text
/admin/dashboard
/admin/students
/admin/faculty
/admin/classes
/admin/subjects
/admin/academic
/admin/attendance
/admin/reports
```

Exact route structure can change during implementation.

---

# 63. MVP Design Priorities

The first implementation should prioritize:

### Priority 1

Student attendance flow:

```text
Session
→ Location
→ Face
→ Verification
→ Success
```

### Priority 2

Student dashboard:

```text
Current class
Attendance
Today's schedule
```

### Priority 3

Faculty live attendance:

```text
Start session
→ Monitor
→ Verify
```

### Priority 4

History and reports.

### Priority 5

Admin UI.

Do not spend large amounts of development time polishing admin analytics before the core attendance workflow is excellent.

---

# 64. UX Performance Requirements

The application should feel responsive.

Important principles:

* Do not block the entire interface unnecessarily.
* Use skeletons for larger content areas.
* Provide immediate visual feedback for actions.
* Cache appropriate server data with TanStack Query.
* Avoid refetching everything after every action.
* Optimize camera processing.
* Avoid unnecessary page reloads.

---

# 65. Face Verification UX Requirement

Face recognition should be treated as a **pipeline**, not a single button.

The UI should progressively guide:

```text
Camera ready
      ↓
Face detected
      ↓
Face positioned correctly
      ↓
Lighting acceptable
      ↓
Capture
      ↓
Verification
      ↓
Result
```

This is important because real-world recognition reliability depends on capture conditions, not only the recognition model. Recent implementation reports specifically identify lighting, distance and speed as common failure points.

---

# 66. Research-Informed Design Decisions

Based on the research, GeoAttend will intentionally adopt:

### From current attendance platforms

* Real-time attendance
* Geofencing
* Face verification
* Role-specific dashboards
* Attendance analytics
* Search/filtering
* Session-based attendance

### From student UX feedback

* Current class visibility
* Next class visibility
* At-a-glance attendance percentage
* Minimal navigation for checking attendance

### From face-recognition systems

* Clear camera guidance
* Geofence feedback
* Verification states
* Retry flows
* Anti-spoofing/liveness as a future capability

---

# 67. What GeoAttend Should Do Better

GeoAttend should differentiate itself through the **quality of the workflow**, not by accumulating features.

The student experience should feel like:

```text
Open
 ↓
Understand
 ↓
Verify
 ↓
Done
```

rather than:

```text
Open
 ↓
Navigate
 ↓
Find attendance
 ↓
Select subject
 ↓
Select date
 ↓
Find session
 ↓
Upload image
 ↓
Submit
```

Faculty should feel:

```text
Open
 ↓
Start
 ↓
Watch
 ↓
Finish
```

rather than:

```text
Open
 ↓
Navigate
 ↓
Configure
 ↓
Navigate
 ↓
Open register
 ↓
Refresh
 ↓
Export
```

---

# 68. Design System Implementation

The Tailwind implementation should eventually centralize:

* Colors
* Typography
* Radius
* Shadows
* Spacing
* Breakpoints
* Component variants

The implementation should avoid excessive arbitrary values such as:

```text
mt-[17px]
rounded-[13px]
text-[#...] 
```

unless they are intentional design tokens.

Prefer reusable design tokens and component variants.

---

# 69. Component Design Philosophy

Components should represent meaningful concepts.

Good:

```text
AttendanceCard
SessionStatus
VerificationStep
LocationStatus
FaceCapture
AttendanceSummary
StudentAttendanceList
```

Less desirable:

```text
BlueBox
BigCard
GreenContainer
```

Component names should communicate domain meaning.

---

# 70. UI Architecture Rule

The UI should be built from three layers:

```text
Design primitives
        ↓
Reusable components
        ↓
Domain screens
```

Example:

```text
Button
  ↓
VerificationButton
  ↓
AttendanceVerificationScreen
```

This keeps Tailwind usage maintainable.

---

# 71. Final UX Principle

The most important UI rule for GeoAttend is:

> **The interface should make the correct action obvious and the system state understandable.**

For students:

> "Am I allowed to mark attendance right now?"

For faculty:

> "Who is present right now?"

For administrators:

> "Is attendance working correctly across the institution?"

If the interface answers these questions quickly, the product is succeeding.

---

# 72. Current UI Status

Research completed.

Initial UX architecture defined.

Not yet finalized:

* Exact color palette
* Exact typography
* Component visual styles
* Logo/branding
* Icon set
* Detailed wireframes
* Animation rules
* Dark mode decision

These should be finalized before extensive UI implementation.

---

# 73. Related Documentation

* `PRODUCT.md` — Product requirements
* `ARCHITECTURE.md` — System architecture
* `DATABASE.md` — Database schema
* `SECURITY.md` — Security architecture
* `API.md` — API contracts
* `AGENTS.md` — Coding-agent instructions
