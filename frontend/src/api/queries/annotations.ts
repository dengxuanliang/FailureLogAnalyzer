import { useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/api/client";

export interface AnnotatePayload {
  record_id: string;
  tags: string[];
  note?: string;
}

export interface AnnotateResponse {
  record_id: string;
  saved_tags: string[];
}

export function useAnnotateRecord() {
  const queryClient = useQueryClient();

  return useMutation<AnnotateResponse, Error, AnnotatePayload>({
    mutationFn: async ({ record_id, tags, note }) => {
      const response = await apiClient.patch<AnnotateResponse>(
        `/analysis/records/${record_id}/tags`,
        { tags, note },
      );
      return response.data;
    },
    onSuccess: async (_response, variables) => {
      await queryClient.invalidateQueries({
        queryKey: ["recordDetail", variables.record_id],
      });
    },
  });
}
