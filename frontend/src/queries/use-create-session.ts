import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { CreateSessionInput, SessionCreateResult } from "@/lib/types";
import { facultyDashboardQueryKey } from "@/queries/use-faculty-dashboard";

export function useCreateSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: CreateSessionInput) => {
      const { data } = await apiClient.post<SessionCreateResult>("/attendance/sessions", input);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: facultyDashboardQueryKey });
    },
  });
}
