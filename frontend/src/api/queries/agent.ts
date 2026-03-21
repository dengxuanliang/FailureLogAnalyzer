import { useMutation } from "@tanstack/react-query";
import apiClient from "../client";
import type { AgentChatRequest, AgentChatResponse } from "../../types/agent";

export function useAgentChatMutation() {
  return useMutation<AgentChatResponse, Error, AgentChatRequest>({
    mutationFn: async (payload) => {
      const response = await apiClient.post<AgentChatResponse>("/agent/chat", payload);
      return response.data;
    },
  });
}
