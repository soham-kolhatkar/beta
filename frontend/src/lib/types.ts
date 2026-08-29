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
