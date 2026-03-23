import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "../client";

export type RuleConditionType =
  | "regex"
  | "contains"
  | "not_contains"
  | "length_gt"
  | "length_lt"
  | "field_equals"
  | "field_missing"
  | "python_expr";

export interface RuleCondition {
  type: RuleConditionType;
  pattern?: string;
  value?: string | number;
  threshold?: number;
}

export interface AnalysisRule {
  id: string;
  name: string;
  description: string;
  field: string;
  condition: RuleCondition;
  tags: string[];
  confidence: number;
  priority: number;
  is_active: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export type AnalysisRuleCreate = Omit<
  AnalysisRule,
  "id" | "created_by" | "created_at" | "updated_at"
>;
export type AnalysisRuleUpdate = Partial<AnalysisRuleCreate>;

export type LLMStrategyType = "full" | "fallback" | "sample" | "manual";

export interface AnalysisStrategy {
  id: string;
  name: string;
  strategy_type: LLMStrategyType;
  config: Record<string, unknown>;
  llm_provider: string;
  llm_model: string;
  prompt_template_id: string | null;
  max_concurrent: number;
  daily_budget: number;
  is_active: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export type AnalysisStrategyCreate = Omit<
  AnalysisStrategy,
  "id" | "created_by" | "created_at" | "updated_at"
>;
export type AnalysisStrategyUpdate = Partial<AnalysisStrategyCreate>;

export interface PromptTemplate {
  id: string;
  name: string;
  benchmark: string | null;
  template: string;
  version: number;
  is_active: boolean;
  created_by: string;
  created_at: string;
}

export type PromptTemplateCreate = Omit<
  PromptTemplate,
  "id" | "version" | "created_by" | "created_at"
>;
export type PromptTemplateUpdate = Partial<PromptTemplateCreate>;

export interface BenchmarkAdapter {
  name: string;
  description: string;
  detected_fields: string[];
  is_builtin: boolean;
}

export type UserRole = "admin" | "analyst" | "viewer";

export interface UserInfo {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface UserCreate {
  username: string;
  email: string;
  password: string;
  role: UserRole;
}

export type UserUpdate = Partial<Omit<UserCreate, "username">> & {
  is_active?: boolean;
};

export interface ProviderSecret {
  id: string;
  provider: string;
  name: string;
  secret_mask: string;
  is_active: boolean;
  is_default: boolean;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface ProviderSecretCreate {
  provider: string;
  name: string;
  secret: string;
  is_active: boolean;
  is_default: boolean;
}

export type ProviderSecretUpdate = Partial<ProviderSecretCreate>;

const RULES_KEY = ["rules"] as const;
const STRATEGIES_KEY = ["strategies"] as const;
const TEMPLATES_KEY = ["promptTemplates"] as const;
const ADAPTERS_KEY = ["adapters"] as const;
const USERS_KEY = ["users"] as const;
const PROVIDER_SECRETS_KEY = ["provider-secrets"] as const;

export function useRules() {
  return useQuery<AnalysisRule[]>({
    queryKey: RULES_KEY,
    queryFn: () => apiClient.get<AnalysisRule[]>("/rules").then((response) => response.data),
  });
}

export function useCreateRule() {
  const queryClient = useQueryClient();
  return useMutation<AnalysisRule, Error, AnalysisRuleCreate>({
    mutationFn: (data) => apiClient.post<AnalysisRule>("/rules", data).then((response) => response.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: RULES_KEY }),
  });
}

export function useUpdateRule() {
  const queryClient = useQueryClient();
  return useMutation<AnalysisRule, Error, { id: string; data: AnalysisRuleUpdate }>({
    mutationFn: ({ id, data }) =>
      apiClient.patch<AnalysisRule>(`/rules/${id}`, data).then((response) => response.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: RULES_KEY }),
  });
}

export function useDeleteRule() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      await apiClient.delete(`/rules/${id}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: RULES_KEY }),
  });
}

export function useStrategies() {
  return useQuery<AnalysisStrategy[]>({
    queryKey: STRATEGIES_KEY,
    queryFn: () =>
      apiClient.get<AnalysisStrategy[]>("/llm/strategies").then((response) => response.data),
  });
}

export function useCreateStrategy() {
  const queryClient = useQueryClient();
  return useMutation<AnalysisStrategy, Error, AnalysisStrategyCreate>({
    mutationFn: (data) =>
      apiClient.post<AnalysisStrategy>("/llm/strategies", data).then((response) => response.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: STRATEGIES_KEY }),
  });
}

export function useUpdateStrategy() {
  const queryClient = useQueryClient();
  return useMutation<AnalysisStrategy, Error, { id: string; data: AnalysisStrategyUpdate }>({
    mutationFn: ({ id, data }) =>
      apiClient.patch<AnalysisStrategy>(`/llm/strategies/${id}`, data).then((response) => response.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: STRATEGIES_KEY }),
  });
}

export function useDeleteStrategy() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      await apiClient.delete(`/llm/strategies/${id}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: STRATEGIES_KEY }),
  });
}

export function useTemplates() {
  return useQuery<PromptTemplate[]>({
    queryKey: TEMPLATES_KEY,
    queryFn: () =>
      apiClient
        .get<PromptTemplate[]>("/llm/prompt-templates")
        .then((response) => response.data),
  });
}

export function useCreateTemplate() {
  const queryClient = useQueryClient();
  return useMutation<PromptTemplate, Error, PromptTemplateCreate>({
    mutationFn: (data) =>
      apiClient
        .post<PromptTemplate>("/llm/prompt-templates", data)
        .then((response) => response.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: TEMPLATES_KEY }),
  });
}

export function useUpdateTemplate() {
  const queryClient = useQueryClient();
  return useMutation<PromptTemplate, Error, { id: string; data: PromptTemplateUpdate }>({
    mutationFn: ({ id, data }) =>
      apiClient
        .patch<PromptTemplate>(`/llm/prompt-templates/${id}`, data)
        .then((response) => response.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: TEMPLATES_KEY }),
  });
}

export function useDeleteTemplate() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      await apiClient.delete(`/llm/prompt-templates/${id}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: TEMPLATES_KEY }),
  });
}

export function useAdapters() {
  return useQuery<BenchmarkAdapter[]>({
    queryKey: ADAPTERS_KEY,
    queryFn: () =>
      apiClient.get<BenchmarkAdapter[]>("/ingest/adapters").then((response) => response.data),
  });
}

export function useUsers() {
  return useQuery<UserInfo[]>({
    queryKey: USERS_KEY,
    queryFn: () => apiClient.get<UserInfo[]>("/users").then((response) => response.data),
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation<UserInfo, Error, UserCreate>({
    mutationFn: (data) => apiClient.post<UserInfo>("/users", data).then((response) => response.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_KEY }),
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();
  return useMutation<UserInfo, Error, UserUpdate & { id: string }>({
    mutationFn: ({ id, ...data }) =>
      apiClient.patch<UserInfo>(`/users/${id}`, data).then((response) => response.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_KEY }),
  });
}

export function useProviderSecrets() {
  return useQuery<ProviderSecret[]>({
    queryKey: PROVIDER_SECRETS_KEY,
    queryFn: () =>
      apiClient.get<ProviderSecret[]>("/llm/provider-secrets").then((response) => response.data),
  });
}

export function useCreateProviderSecret() {
  const queryClient = useQueryClient();
  return useMutation<ProviderSecret, Error, ProviderSecretCreate>({
    mutationFn: (data) =>
      apiClient
        .post<ProviderSecret>("/llm/provider-secrets", data)
        .then((response) => response.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PROVIDER_SECRETS_KEY }),
  });
}

export function useUpdateProviderSecret() {
  const queryClient = useQueryClient();
  return useMutation<ProviderSecret, Error, { id: string; data: ProviderSecretUpdate }>({
    mutationFn: ({ id, data }) =>
      apiClient
        .patch<ProviderSecret>(`/llm/provider-secrets/${id}`, data)
        .then((response) => response.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PROVIDER_SECRETS_KEY }),
  });
}

export function useDeleteProviderSecret() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      await apiClient.delete(`/llm/provider-secrets/${id}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PROVIDER_SECRETS_KEY }),
  });
}
