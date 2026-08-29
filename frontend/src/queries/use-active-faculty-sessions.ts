import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { SessionDetail } from "@/lib/types";

export const activeFacultySessionsQueryKey = ["faculty-sessions", "active"];

export function useActiveFacultySessions() {
  return useQuery<SessionDetail[]>({
    queryKey: activeFacultySessionsQueryKey,
    queryFn: async () => {
      const { data } = await apiClient.get<{ items: SessionDetail[] }>("/faculty/me/sessions", {
        params: { status: "ACTIVE" },
      });
      return data.items;
    },
  });
}
