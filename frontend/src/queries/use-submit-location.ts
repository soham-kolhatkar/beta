import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { LocationVerifyResult } from "@/lib/types";

interface SubmitLocationInput {
  verificationId: string;
  latitude: number;
  longitude: number;
  accuracyMeters: number;
}

export function useSubmitLocation() {
  return useMutation({
    mutationFn: async ({
      verificationId,
      latitude,
      longitude,
      accuracyMeters,
    }: SubmitLocationInput) => {
      const { data } = await apiClient.post<LocationVerifyResult>(
        `/attendance/verifications/${verificationId}/location`,
        { latitude, longitude, accuracy_meters: accuracyMeters },
      );
      return data;
    },
  });
}
