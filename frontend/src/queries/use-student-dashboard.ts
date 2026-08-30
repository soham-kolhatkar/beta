import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { StudentDashboard } from "@/lib/types";

export const studentDashboardQueryKey = ["student-dashboard"];

export function useStudentDashboard() {
  return useQuery<StudentDashboard>({
    queryKey: studentDashboardQueryKey,
    queryFn: async () => {
      const { data } = await apiClient.get<StudentDashboard>("/students/me/dashboard");
      return data;
    },
  });
}
