import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { FaceModelInfo } from "@/lib/types";
import { faceStatusQueryKey } from "@/queries/use-face-status";

interface RegisterFaceResponse {
  face_registered: boolean;
  model: FaceModelInfo;
}

export function useRegisterFace() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (image: Blob) => {
      const formData = new FormData();
      formData.append("image", image, "face.jpg");
      const { data } = await apiClient.post<RegisterFaceResponse>(
        "/students/me/face",
        formData,
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: faceStatusQueryKey });
    },
  });
}
