import { useQuery } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { apiClient } from "@/lib/api";
import type { User } from "@/lib/types";

export const currentUserQueryKey = ["current-user"];

export function useCurrentUser() {
  return useQuery<User | null>({
    queryKey: currentUserQueryKey,
    queryFn: async () => {
      try {
        const { data } = await apiClient.get<User>("/auth/me");
        return data;
      } catch (error) {
        if (isAxiosError(error) && error.response?.status === 401) {
          return null;
        }
        throw error;
      }
    },
    retry: false,
  });
}
