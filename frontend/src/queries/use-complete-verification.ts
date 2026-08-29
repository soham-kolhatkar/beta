import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { CompleteAttendanceResult } from "@/lib/types";

export function useCompleteVerification() {
  return useMutation({
    mutationFn: async (verificationId: string) => {
      const { data } = await apiClient.post<CompleteAttendanceResult>(
        `/attendance/verifications/${verificationId}/complete`,
      );
      return data;
    },
  });
}
