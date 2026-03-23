import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/api/client";
import type {
  EvalSession,
  SessionActionResponse,
  SessionDeleteResponse,
  SessionDetail,
} from "@/types/api";

const SESSIONS_KEY = ["sessions"] as const;

export function useSessions() {
  return useQuery({
    queryKey: SESSIONS_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<EvalSession[]>("/sessions");
      return data;
    },
  });
}

export function useSessionDetail(sessionId: string | null) {
  return useQuery({
    queryKey: [...SESSIONS_KEY, sessionId],
    queryFn: async () => {
      const { data } = await apiClient.get<SessionDetail>(`/sessions/${sessionId}`);
      return data;
    },
    enabled: Boolean(sessionId),
  });
}

export function useDeleteSession() {
  const queryClient = useQueryClient();
  return useMutation<SessionDeleteResponse, Error, string>({
    mutationFn: async (sessionId) => {
      const { data } = await apiClient.delete<SessionDeleteResponse>(`/sessions/${sessionId}`);
      return data;
    },
    onSuccess: (_data, sessionId) => {
      queryClient.invalidateQueries({ queryKey: SESSIONS_KEY });
      queryClient.invalidateQueries({ queryKey: [...SESSIONS_KEY, sessionId] });
    },
  });
}

export function useRerunSessionRules() {
  return useMutation<SessionActionResponse, Error, { sessionId: string; ruleIds?: string[] | null }>(
    {
      mutationFn: async ({ sessionId, ruleIds }) => {
        const { data } = await apiClient.post<SessionActionResponse>(
          `/sessions/${sessionId}/actions/rerun-rules`,
          { rule_ids: ruleIds ?? null },
        );
        return data;
      },
    },
  );
}
