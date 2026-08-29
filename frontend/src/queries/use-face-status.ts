import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { FaceStatus } from "@/lib/types";

export const faceStatusQueryKey = ["face-status"];

export function useFaceStatus() {
  return useQuery<FaceStatus>({
    queryKey: faceStatusQueryKey,
    queryFn: async () => {
      const { data } = await apiClient.get<FaceStatus>("/students/me/face");
      return data;
    },
  });
}
