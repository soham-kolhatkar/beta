export type UserRole = "STUDENT" | "FACULTY" | "ADMIN";

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  profile_image_url: string | null;
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
