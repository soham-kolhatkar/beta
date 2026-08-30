import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { ClassAttendance } from "@/lib/types";

export function classAttendanceQueryKey(classId: string) {
  return ["class-attendance", classId];
}

export function useClassAttendance(classId: string) {
  return useQuery<ClassAttendance>({
    queryKey: classAttendanceQueryKey(classId),
    queryFn: async () => {
      const { data } = await apiClient.get<ClassAttendance>(
        `/students/me/classes/${classId}/attendance`,
      );
      return data;
    },
  });
}
