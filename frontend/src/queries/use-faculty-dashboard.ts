import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { FacultyDashboard } from "@/lib/types";

export const facultyDashboardQueryKey = ["faculty-dashboard"];

export function useFacultyDashboard() {
  return useQuery<FacultyDashboard>({
    queryKey: facultyDashboardQueryKey,
    queryFn: async () => {
      const { data } = await apiClient.get<FacultyDashboard>("/faculty/me/dashboard");
      return data;
    },
  });
}
