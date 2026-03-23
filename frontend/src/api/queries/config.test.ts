import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { jest } from "@jest/globals";
import React, { type ReactNode } from "react";

const apiClientMock = {
  get: jest.fn() as jest.Mock,
  post: jest.fn() as jest.Mock,
  put: jest.fn() as jest.Mock,
  patch: jest.fn() as jest.Mock,
  delete: jest.fn() as jest.Mock,
};

await jest.unstable_mockModule("../client", () => ({
  __esModule: true,
  default: apiClientMock,
}));

const {
  useAdapters,
  useCreateRule,
  useCreateStrategy,
  useCreateTemplate,
  useCreateUser,
  useCreateProviderSecret,
  useDeleteRule,
  useDeleteProviderSecret,
  useDeleteStrategy,
  useDeleteTemplate,
  useProviderSecrets,
  useRules,
  useStrategies,
  useTemplates,
  useUpdateProviderSecret,
  useUpdateRule,
  useUpdateStrategy,
  useUpdateTemplate,
  useUpdateUser,
  useUsers,
} = await import("./config");

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

describe("config query hooks", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("fetches rules", async () => {
    apiClientMock.get.mockImplementationOnce(async () => ({
      data: [{ id: "r1", name: "Rule One" }],
    }));

    const { result } = renderHook(() => useRules(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual([{ id: "r1", name: "Rule One" }]);
    expect(apiClientMock.get).toHaveBeenCalledWith("/rules");
  });

  it("creates, updates, and deletes rules", async () => {
    apiClientMock.post.mockImplementationOnce(async () => ({ data: { id: "r1" } }));
    apiClientMock.patch.mockImplementationOnce(async () => ({ data: { id: "r1", is_active: false } }));
    apiClientMock.delete.mockImplementation(async () => ({ data: null }));

    const createHook = renderHook(() => useCreateRule(), { wrapper: createWrapper() });
    const updateHook = renderHook(() => useUpdateRule(), { wrapper: createWrapper() });
    const deleteHook = renderHook(() => useDeleteRule(), { wrapper: createWrapper() });

    await act(async () => {
      await createHook.result.current.mutateAsync({
        name: "Rule One",
        description: "",
        field: "model_answer",
        condition: { type: "field_missing" },
        tags: ["格式与规范错误.空回答"],
        confidence: 1,
        priority: 1,
        is_active: true,
      });
      await updateHook.result.current.mutateAsync({
        id: "r1",
        data: { is_active: false },
      });
      await deleteHook.result.current.mutateAsync("r1");
    });

    expect(apiClientMock.post).toHaveBeenCalledWith("/rules", expect.objectContaining({ name: "Rule One" }));
    expect(apiClientMock.patch).toHaveBeenCalledWith("/rules/r1", { is_active: false });
    expect(apiClientMock.delete).toHaveBeenCalledWith("/rules/r1");
  });

  it("fetches and mutates strategies", async () => {
    apiClientMock.get.mockImplementationOnce(async () => ({ data: [{ id: "s1", name: "Fallback" }] }));
    apiClientMock.post.mockImplementationOnce(async () => ({ data: { id: "s1" } }));
    apiClientMock.patch.mockImplementationOnce(async () => ({ data: { id: "s1", is_active: false } }));
    apiClientMock.delete.mockImplementationOnce(async () => ({ data: null }));

    const strategiesHook = renderHook(() => useStrategies(), { wrapper: createWrapper() });
    await waitFor(() => expect(strategiesHook.result.current.isSuccess).toBe(true));
    expect(apiClientMock.get).toHaveBeenCalledWith("/llm/strategies");

    const createHook = renderHook(() => useCreateStrategy(), { wrapper: createWrapper() });
    const updateHook = renderHook(() => useUpdateStrategy(), { wrapper: createWrapper() });
    const deleteHook = renderHook(() => useDeleteStrategy(), { wrapper: createWrapper() });

    await act(async () => {
      await createHook.result.current.mutateAsync({
        name: "Fallback",
        strategy_type: "fallback",
        config: {},
        llm_provider: "openai",
        llm_model: "gpt-4o",
        prompt_template_id: null,
        max_concurrent: 5,
        daily_budget: 10,
        is_active: true,
      });
      await updateHook.result.current.mutateAsync({
        id: "s1",
        data: { is_active: false },
      });
      await deleteHook.result.current.mutateAsync("s1");
    });

    expect(apiClientMock.post).toHaveBeenCalledWith(
      "/llm/strategies",
      expect.objectContaining({ name: "Fallback" }),
    );
    expect(apiClientMock.patch).toHaveBeenCalledWith("/llm/strategies/s1", { is_active: false });
    expect(apiClientMock.delete).toHaveBeenCalledWith("/llm/strategies/s1");
  });

  it("fetches and mutates templates", async () => {
    apiClientMock.get.mockImplementationOnce(async () => ({ data: [{ id: "t1", name: "Generic Template" }] }));
    apiClientMock.post.mockImplementationOnce(async () => ({ data: { id: "t1" } }));
    apiClientMock.patch.mockImplementationOnce(async () => ({ data: { id: "t1", is_active: false } }));
    apiClientMock.delete.mockImplementationOnce(async () => ({ data: null }));

    const templatesHook = renderHook(() => useTemplates(), { wrapper: createWrapper() });
    await waitFor(() => expect(templatesHook.result.current.isSuccess).toBe(true));
    expect(apiClientMock.get).toHaveBeenCalledWith("/llm/prompt-templates");

    const createHook = renderHook(() => useCreateTemplate(), { wrapper: createWrapper() });
    const updateHook = renderHook(() => useUpdateTemplate(), { wrapper: createWrapper() });
    const deleteHook = renderHook(() => useDeleteTemplate(), { wrapper: createWrapper() });

    await act(async () => {
      await createHook.result.current.mutateAsync({
        name: "Generic Template",
        benchmark: null,
        template: "Analyze: {question}",
        is_active: true,
      });
      await updateHook.result.current.mutateAsync({
        id: "t1",
        data: { is_active: false },
      });
      await deleteHook.result.current.mutateAsync("t1");
    });

    expect(apiClientMock.post).toHaveBeenCalledWith(
      "/llm/prompt-templates",
      expect.objectContaining({ name: "Generic Template" }),
    );
    expect(apiClientMock.patch).toHaveBeenCalledWith("/llm/prompt-templates/t1", { is_active: false });
    expect(apiClientMock.delete).toHaveBeenCalledWith("/llm/prompt-templates/t1");
  });

  it("fetches adapters", async () => {
    apiClientMock.get.mockImplementationOnce(async () => ({
      data: [{ name: "mmlu", description: "MMLU", detected_fields: ["subject"], is_builtin: true }],
    }));

    const { result } = renderHook(() => useAdapters(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual([
      { name: "mmlu", description: "MMLU", detected_fields: ["subject"], is_builtin: true },
    ]);
    expect(apiClientMock.get).toHaveBeenCalledWith("/ingest/adapters");
  });

  it("fetches and mutates users", async () => {
    apiClientMock.get.mockImplementationOnce(async () => ({
      data: [{ id: "u1", username: "admin", email: "a@example.com", role: "admin", is_active: true }],
    }));
    apiClientMock.post.mockImplementationOnce(async () => ({ data: { id: "u2" } }));
    apiClientMock.patch.mockImplementationOnce(async () => ({ data: { id: "u2", role: "viewer" } }));

    const usersHook = renderHook(() => useUsers(), { wrapper: createWrapper() });
    await waitFor(() => expect(usersHook.result.current.isSuccess).toBe(true));
    expect(apiClientMock.get).toHaveBeenCalledWith("/users");

    const createHook = renderHook(() => useCreateUser(), { wrapper: createWrapper() });
    const updateHook = renderHook(() => useUpdateUser(), { wrapper: createWrapper() });

    await act(async () => {
      await createHook.result.current.mutateAsync({
        username: "new-user",
        email: "new@example.com",
        password: "password123",
        role: "analyst",
      });
      await updateHook.result.current.mutateAsync({
        id: "u2",
        role: "viewer",
      });
    });

    expect(apiClientMock.post).toHaveBeenCalledWith(
      "/users",
      expect.objectContaining({ username: "new-user" }),
    );
    expect(apiClientMock.patch).toHaveBeenCalledWith("/users/u2", { role: "viewer" });
  });

  it("fetches and mutates provider secrets", async () => {
    apiClientMock.get.mockImplementationOnce(async () => ({
      data: [{ id: "ps1", provider: "openai", name: "primary", secret_mask: "sk-t...3456" }],
    }));
    apiClientMock.post.mockImplementationOnce(async () => ({ data: { id: "ps2" } }));
    apiClientMock.patch.mockImplementationOnce(async () => ({ data: { id: "ps2", is_active: false } }));
    apiClientMock.delete.mockImplementationOnce(async () => ({ data: null }));

    const listHook = renderHook(() => useProviderSecrets(), { wrapper: createWrapper() });
    await waitFor(() => expect(listHook.result.current.isSuccess).toBe(true));
    expect(apiClientMock.get).toHaveBeenCalledWith("/llm/provider-secrets");

    const createHook = renderHook(() => useCreateProviderSecret(), { wrapper: createWrapper() });
    const updateHook = renderHook(() => useUpdateProviderSecret(), { wrapper: createWrapper() });
    const deleteHook = renderHook(() => useDeleteProviderSecret(), { wrapper: createWrapper() });

    await act(async () => {
      await createHook.result.current.mutateAsync({
        provider: "openai",
        name: "primary",
        secret: "sk-test-123456",
        is_active: true,
        is_default: true,
      });
      await updateHook.result.current.mutateAsync({
        id: "ps2",
        data: { is_active: false },
      });
      await deleteHook.result.current.mutateAsync("ps2");
    });

    expect(apiClientMock.post).toHaveBeenCalledWith(
      "/llm/provider-secrets",
      expect.objectContaining({ provider: "openai", name: "primary" }),
    );
    expect(apiClientMock.patch).toHaveBeenCalledWith("/llm/provider-secrets/ps2", { is_active: false });
    expect(apiClientMock.delete).toHaveBeenCalledWith("/llm/provider-secrets/ps2");
  });
});
