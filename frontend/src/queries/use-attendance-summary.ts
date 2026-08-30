import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { AttendanceSummary } from "@/lib/types";

export const attendanceSummaryQueryKey = ["attendance-summary"];

export function useAttendanceSummary() {
  return useQuery<AttendanceSummary>({
    queryKey: attendanceSummaryQueryKey,
    queryFn: async () => {
      const { data } = await apiClient.get<AttendanceSummary>("/students/me/attendance/summary");
      return data;
    },
  });
}
