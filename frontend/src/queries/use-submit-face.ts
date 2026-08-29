import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { FaceVerifyResult } from "@/lib/types";

export function useSubmitFace() {
  return useMutation({
    mutationFn: async ({
      verificationId,
      image,
    }: {
      verificationId: string;
      image: Blob;
    }) => {
      const formData = new FormData();
      formData.append("image", image, "face.jpg");
      const { data } = await apiClient.post<FaceVerifyResult>(
        `/attendance/verifications/${verificationId}/face`,
        formData,
      );
      return data;
    },
  });
}
