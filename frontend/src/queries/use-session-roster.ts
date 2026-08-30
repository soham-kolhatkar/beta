import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { SessionRoster } from "@/lib/types";

export function sessionRosterQueryKey(sessionId: string) {
  return ["session-roster", sessionId];
}

// docs/API.md §25: polling refetch, not WebSockets/SSE, until real-time
// requirements justify the added complexity.
const POLL_INTERVAL_MS = 5_000;

export function useSessionRoster(sessionId: string) {
  return useQuery<SessionRoster>({
    queryKey: sessionRosterQueryKey(sessionId),
    queryFn: async () => {
      const { data } = await apiClient.get<SessionRoster>(
        `/attendance/sessions/${sessionId}/attendance`,
      );
      return data;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
}
