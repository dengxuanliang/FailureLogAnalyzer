import { useQuery } from "@tanstack/react-query";
import apiClient from "@/api/client";
import type { EvalSession } from "@/types/api";

export function useSessions() {
  return useQuery({
    queryKey: ["sessions"],
    queryFn: async () => {
      const { data } = await apiClient.get<EvalSession[]>("/sessions");
      return data;
    },
  });
}
