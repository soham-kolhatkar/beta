import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";

interface HealthResponse {
  status: string;
}

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const { data } = await apiClient.get<HealthResponse>("/health");
      return data;
    },
  });
}
