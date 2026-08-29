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
