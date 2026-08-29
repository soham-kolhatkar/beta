import { RequireRole } from "@/components/require-role";

export default function FacultyLayout({ children }: { children: React.ReactNode }) {
  return <RequireRole role="FACULTY">{children}</RequireRole>;
}
