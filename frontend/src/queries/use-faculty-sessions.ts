import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { SessionDetail, SessionStatus } from "@/lib/types";

export function facultySessionsQueryKey(status?: SessionStatus) {
  return ["faculty-sessions", status ?? "ALL"];
}

export function useFacultySessions(status?: SessionStatus) {
  return useQuery<SessionDetail[]>({
    queryKey: facultySessionsQueryKey(status),
    queryFn: async () => {
      const { data } = await apiClient.get<{ items: SessionDetail[] }>("/faculty/me/sessions", {
        params: status ? { status } : undefined,
      });
      return data.items;
    },
  });
}
