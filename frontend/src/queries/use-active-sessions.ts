import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { ActiveSession } from "@/lib/types";

export const activeSessionsQueryKey = ["sessions", "active"];

export function useActiveSessions() {
  return useQuery<ActiveSession[]>({
    queryKey: activeSessionsQueryKey,
    queryFn: async () => {
      const { data } = await apiClient.get<{ items: ActiveSession[] }>(
        "/attendance/sessions/active",
      );
      return data.items;
    },
  });
}
