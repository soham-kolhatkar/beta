import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { AttendanceHistory } from "@/lib/types";

export function attendanceHistoryQueryKey(page: number) {
  return ["attendance-history", page];
}

export function useAttendanceHistory(page: number, pageSize = 10) {
  return useQuery<AttendanceHistory>({
    queryKey: attendanceHistoryQueryKey(page),
    queryFn: async () => {
      const { data } = await apiClient.get<AttendanceHistory>("/students/me/attendance", {
        params: { page, page_size: pageSize },
      });
      return data;
    },
  });
}
