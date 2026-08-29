import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { FacultyClass } from "@/lib/types";

export const facultyClassesQueryKey = ["faculty-classes"];

export function useFacultyClasses() {
  return useQuery<FacultyClass[]>({
    queryKey: facultyClassesQueryKey,
    queryFn: async () => {
      const { data } = await apiClient.get<{ items: FacultyClass[] }>("/faculty/me/classes");
      return data.items;
    },
  });
}
