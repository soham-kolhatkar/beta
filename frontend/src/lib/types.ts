export type UserRole = "STUDENT" | "FACULTY" | "ADMIN";

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  profile_image_url: string | null;
}

export interface FaceModelInfo {
  name: string;
  version: string;
}

export interface FaceStatus {
  registered: boolean;
  model: FaceModelInfo | null;
  updated_at: string | null;
}

export type SessionStatus = "CREATED" | "ACTIVE" | "ENDED";

export interface SubjectBrief {
  id: string;
  name: string;
  code: string;
}

export interface FacultyClass {
  id: string;
  name: string;
  subject: SubjectBrief;
  student_count: number;
}

export interface SessionDetail {
  id: string;
  class: { id: string; name: string };
  subject: SubjectBrief;
  faculty: { id: string; name: string };
  starts_at: string;
  ends_at: string;
  status: SessionStatus;
}

export interface CreateSessionInput {
  class_id: string;
  starts_at: string;
  ends_at: string;
  latitude: number;
  longitude: number;
  radius_meters: number;
}

export interface SessionCreateResult {
  id: string;
  class_id: string;
  status: SessionStatus;
  starts_at: string;
  ends_at: string;
}

export interface ActiveSession {
  id: string;
  class: { id: string; name: string };
  subject: SubjectBrief;
  faculty: { name: string };
  starts_at: string;
  ends_at: string;
}

export interface StartVerificationResult {
  verification_id: string;
  session_id: string;
  expires_at: string;
  steps: string[];
}

export interface LocationVerifyResult {
  verified: boolean;
  distance_meters: number;
  accuracy_meters: number;
  next_step?: string;
  code?: string;
  message?: string;
  allowed_radius_meters?: number;
}

export interface FaceVerifyResult {
  verified: boolean;
  next_step?: string;
  code?: string;
  message?: string;
  retryable?: boolean;
}

export interface CompleteAttendanceResult {
  attendance_id: string;
  status: "PRESENT";
  marked_at: string;
}

export interface AttendanceOverview {
  percentage: number;
  present: number;
  total: number;
}

export interface StudentDashboard {
  student: { name: string };
  attendance: AttendanceOverview;
  active_session: ActiveSession | null;
  today_classes: ActiveSession[];
}

export interface TodaySummary {
  classes: number;
  active_sessions: number;
  upcoming_sessions: number;
}

export interface FacultyDashboard {
  today: TodaySummary;
  active_session: SessionDetail | null;
  upcoming_classes: SessionDetail[];
}

export type RosterStatus = "PRESENT" | "NOT_MARKED" | "VERIFICATION_ISSUE";

export interface RosterStudent {
  student_id: string;
  name: string;
  prn: string;
  status: RosterStatus;
  marked_at: string | null;
}

export interface SessionRoster {
  session: { id: string; class_name: string; subject: string };
  summary: {
    total_students: number;
    present: number;
    not_marked: number;
    verification_issues: number;
  };
  students: RosterStudent[];
}

export function dashboardPathForRole(role: UserRole): string {
  switch (role) {
    case "STUDENT":
      return "/student/dashboard";
    case "FACULTY":
      return "/faculty/dashboard";
    case "ADMIN":
      return "/admin/dashboard";
  }
}
