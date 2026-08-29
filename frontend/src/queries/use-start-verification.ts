import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { StartVerificationResult } from "@/lib/types";

export function useStartVerification() {
  return useMutation({
    mutationFn: async (sessionId: string) => {
      const { data } = await apiClient.post<StartVerificationResult>(
        `/attendance/sessions/${sessionId}/verification`,
      );
      return data;
    },
  });
}
