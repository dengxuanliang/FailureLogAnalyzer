export type ChatRole = "user" | "assistant" | "system";

export type AgentPage =
  | "overview"
  | "analysis"
  | "compare"
  | "cross-benchmark"
  | "config"
  | "error-analysis"
  | "version-compare";

export type AgentFilterKey =
  | "benchmark"
  | "model_version"
  | "time_range_start"
  | "time_range_end";

export type ActionPayload =
  | { type: "navigate"; page: AgentPage }
  | { type: "set_filter"; key: AgentFilterKey; value: string }
  | { type: "highlight_record"; record_id: string }
  | { type: "open_session"; session_id: string };

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  timestamp: string;
  isStreaming?: boolean;
  action?: ActionPayload;
}

export interface WsClientMessage {
  message: string;
  conversation_id: string | null;
  filters?: Partial<Record<AgentFilterKey, string>>;
}

export interface WsServerMessage {
  type: "token" | "message" | "action" | "error" | "done";
  token?: string;
  message?: ChatMessage;
  action?: ActionPayload;
  error?: string;
  conversation_id?: string;
}

export type ConnectionStatus = "connecting" | "connected" | "disconnected" | "error";

export interface AgentChatRequest extends WsClientMessage {}

export interface AgentChatResponse {
  conversation_id: string;
  reply: string;
  messages: ChatMessage[];
  action?: ActionPayload;
}
