import { useMutation, useQueries, useQuery } from "@tanstack/react-query";
import apiClient from "@/api/client";
import type {
  AnalysisStrategy,
  IngestJobListResponse,
  IngestJobStatus,
  IngestUploadPayload,
  IngestUploadResponse,
  LlmJobStatus,
  LlmJobTriggerPayload,
  LlmJobTriggerResponse,
} from "@/types/api";

export function useIngestUpload() {
  return useMutation<IngestUploadResponse, Error, IngestUploadPayload>({
    mutationFn: async (payload) => {
      const formData = new globalThis.FormData();
      formData.append("file", payload.file);
      formData.append("benchmark", payload.benchmark);
      formData.append("model", payload.model);
      formData.append("model_version", payload.model_version);
      if (payload.adapter_name) {
        formData.append("adapter_name", payload.adapter_name);
      }
      if (payload.session_id) {
        formData.append("session_id", payload.session_id);
      }

      const token = localStorage.getItem("token");
      const response = await globalThis.fetch("/api/v1/ingest/upload", {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed with status ${response.status}`);
      }

      return (await response.json()) as IngestUploadResponse;
    },
  });
}

export function useIngestJobStatusQueries(jobIds: string[]) {
  return useQueries({
    queries: jobIds.map((jobId) => ({
      queryKey: ["ingestJobStatus", jobId],
      queryFn: async () => {
        const { data } = await apiClient.get<IngestJobStatus>(`/ingest/${jobId}/status`);
        return data;
      },
      enabled: Boolean(jobId),
      refetchInterval: 3_000,
    })),
  });
}

export function useIngestJobs() {
  return useQuery<IngestJobListResponse>({
    queryKey: ["ingestJobs"],
    queryFn: async () => {
      const { data } = await apiClient.get<IngestJobListResponse>("/ingest/jobs");
      return data;
    },
    refetchInterval: 5_000,
  });
}

export function useLlmJobStatusQueries(jobIds: string[]) {
  return useQueries({
    queries: jobIds.map((jobId) => ({
      queryKey: ["llmJobStatus", jobId],
      queryFn: async () => {
        const { data } = await apiClient.get<LlmJobStatus>(`/llm/jobs/${jobId}/status`);
        return data;
      },
      enabled: Boolean(jobId),
      refetchInterval: 3_000,
    })),
  });
}

export function useLlmJobs() {
  return useQuery<LlmJobStatus[]>({
    queryKey: ["llmJobs"],
    queryFn: async () => {
      const { data } = await apiClient.get<LlmJobStatus[]>("/llm/jobs");
      return data;
    },
    refetchInterval: 5_000,
  });
}

export function useLlmStrategies() {
  return useQuery<AnalysisStrategy[]>({
    queryKey: ["strategies"],
    queryFn: async () => {
      const { data } = await apiClient.get<AnalysisStrategy[]>("/llm/strategies");
      return data;
    },
  });
}

export function useTriggerLlmJob() {
  return useMutation<LlmJobTriggerResponse, Error, LlmJobTriggerPayload>({
    mutationFn: async (payload) => {
      const { data } = await apiClient.post<LlmJobTriggerResponse>("/llm/jobs/trigger", {
        session_id: payload.session_id,
        strategy_id: payload.strategy_id,
        manual_record_ids: payload.manual_record_ids ?? [],
        expect_manual_records: payload.expect_manual_records ?? false,
      });
      return data;
    },
  });
}
