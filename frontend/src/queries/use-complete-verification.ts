import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { CompleteAttendanceResult } from "@/lib/types";
import { studentDashboardQueryKey } from "@/queries/use-student-dashboard";

export function useCompleteVerification() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (verificationId: string) => {
      const { data } = await apiClient.post<CompleteAttendanceResult>(
        `/attendance/verifications/${verificationId}/complete`,
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: studentDashboardQueryKey });
    },
  });
}
