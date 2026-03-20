# Analysis Config Page — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Analysis Config page (`/config`), replacing its `PlaceholderPage` route from Plan 07. The page contains five tabbed panels: Rule Management, LLM Strategy Management, Prompt Template Management, Benchmark Adapter Management, and User Management (Admin only).

**Architecture:** Each panel is a self-contained component that owns its own TanStack Query hooks for CRUD operations. All mutations (`create`, `update`, `delete`, `toggle`) use `useMutation` + `queryClient.invalidateQueries` for optimistic list refresh. Forms live in Ant Design `Modal` / `Drawer` overlays. The Benchmark Adapter panel is read-only (adapters are registered server-side). The User Management panel is only visible to Admin role users (design doc §11). Role guards from `AuthContext` disable write actions for `viewer` role users.

**Tech Stack:** React 18, TypeScript 5, Ant Design 5, TanStack Query v5, React Router v6

---

## Prerequisites

This plan depends on Plan 07 (Frontend Foundation) being complete. The following are already available:

- **Types** (`frontend/src/types/api.ts`): base types; this plan adds rule/strategy/template/adapter types
- **Hooks**: `useGlobalFilters()`, `AuthContext` (for role checks)
- **Layout**: `AppLayout` with sidebar nav and FilterBar
- **Router**: route for `/config` (currently `PlaceholderPage`)

## File Structure

```
frontend/src/
  api/queries/
    config.ts               # CREATE — all CRUD hooks for rules, strategies, templates, adapters
    config.test.ts          # CREATE
  pages/
    Config/
      index.tsx             # CREATE — page with Tabs wrapper
      Config.test.tsx       # CREATE
      Config.integration.test.tsx  # CREATE
      components/
        RulesPanel.tsx          # CREATE — rule list + create/edit/delete/toggle
        RulesPanel.test.tsx
        RuleFormModal.tsx        # CREATE — create/edit rule modal with condition builder
        RuleFormModal.test.tsx
        StrategiesPanel.tsx      # CREATE — LLM strategy list + CRUD
        StrategiesPanel.test.tsx
        StrategyFormModal.tsx    # CREATE — create/edit strategy modal
        StrategyFormModal.test.tsx
        TemplatesPanel.tsx       # CREATE — prompt template list + CRUD
        TemplatesPanel.test.tsx
        TemplateFormModal.tsx    # CREATE — create/edit template modal (textarea)
        TemplateFormModal.test.tsx
        AdaptersPanel.tsx        # CREATE — read-only adapter list
        AdaptersPanel.test.tsx
        UsersPanel.tsx          # CREATE — user CRUD table (Admin only)
        UsersPanel.test.tsx
        UserFormModal.tsx        # CREATE — create/edit user modal
        UserFormModal.test.tsx
  types/
    api.ts                  # MODIFY — add AnalysisRule, AnalysisStrategy, PromptTemplate,
                            #          BenchmarkAdapter types
  locales/
    zh.json                 # MODIFY — add config.* keys
    en.json                 # MODIFY — add config.* keys
  router.tsx                # MODIFY — replace PlaceholderPage for /config
```

---

### Task 1: Add TypeScript Types

**Files:**
- Modify: `frontend/src/types/api.ts`

- [ ] **Step 1: Append the following interfaces to `frontend/src/types/api.ts`**

```typescript
// ─── Analysis Config ──────────────────────────────────────────────────────

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
  config: Record<string, unknown>;  // sample_rate, categories, budget_limit, etc.
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
  benchmark: string | null;   // null = generic
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
  name: string;           // e.g. "mmlu"
  description: string;
  detected_fields: string[];
  is_builtin: boolean;
}

// ─── User Management (Admin only, design doc §11) ────────────────────────────

export type UserRole = "admin" | "analyst" | "viewer";

export interface UserInfo {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/api.ts
git commit -m "feat: add config page types (rules, strategies, templates, adapters, users)"
```

---

### Task 2: Add i18n Translation Keys

**Files:**
- Modify: `frontend/src/locales/zh.json`
- Modify: `frontend/src/locales/en.json`

- [ ] **Step 1: Add Chinese translation keys**

Add to `frontend/src/locales/zh.json`:

```json
{
  "config.title": "分析配置",
  "config.tabs.rules": "规则管理",
  "config.tabs.strategies": "LLM 策略",
  "config.tabs.templates": "Prompt 模板",
  "config.tabs.adapters": "Benchmark Adapter",

  "config.rules.title": "分析规则",
  "config.rules.create": "新建规则",
  "config.rules.edit": "编辑规则",
  "config.rules.delete": "删除规则",
  "config.rules.deleteConfirm": "确认删除规则「{name}」？",
  "config.rules.columns.name": "规则名称",
  "config.rules.columns.field": "目标字段",
  "config.rules.columns.conditionType": "条件类型",
  "config.rules.columns.tags": "产出标签",
  "config.rules.columns.confidence": "置信度",
  "config.rules.columns.priority": "优先级",
  "config.rules.columns.status": "状态",
  "config.rules.columns.actions": "操作",
  "config.rules.enabled": "启用",
  "config.rules.disabled": "停用",
  "config.rules.form.name": "规则名称",
  "config.rules.form.description": "描述",
  "config.rules.form.field": "目标字段",
  "config.rules.form.fieldHelp": "如 model_answer, extracted_code",
  "config.rules.form.conditionType": "条件类型",
  "config.rules.form.pattern": "匹配模式/值",
  "config.rules.form.tags": "产出标签",
  "config.rules.form.tagsHelp": "标签路径，如 格式与规范错误.空回答",
  "config.rules.form.confidence": "置信度",
  "config.rules.form.priority": "优先级（越小越先执行）",
  "config.rules.form.isActive": "启用",

  "config.strategies.title": "LLM 触发策略",
  "config.strategies.create": "新建策略",
  "config.strategies.edit": "编辑策略",
  "config.strategies.delete": "删除策略",
  "config.strategies.deleteConfirm": "确认删除策略「{name}」？",
  "config.strategies.columns.name": "策略名称",
  "config.strategies.columns.type": "类型",
  "config.strategies.columns.provider": "LLM 提供商",
  "config.strategies.columns.model": "模型",
  "config.strategies.columns.maxConcurrent": "最大并发",
  "config.strategies.columns.dailyBudget": "每日预算",
  "config.strategies.columns.status": "状态",
  "config.strategies.columns.actions": "操作",
  "config.strategies.form.name": "策略名称",
  "config.strategies.form.type": "策略类型",
  "config.strategies.form.provider": "LLM 提供商",
  "config.strategies.form.model": "模型名称",
  "config.strategies.form.maxConcurrent": "最大并发数",
  "config.strategies.form.dailyBudget": "每日预算上限（美元）",
  "config.strategies.form.isActive": "启用",
  "config.strategies.type.full": "全量",
  "config.strategies.type.fallback": "规则兜底",
  "config.strategies.type.sample": "采样",
  "config.strategies.type.manual": "手动触发",

  "config.templates.title": "Prompt 模板",
  "config.templates.create": "新建模板",
  "config.templates.edit": "编辑模板",
  "config.templates.delete": "删除模板",
  "config.templates.deleteConfirm": "确认删除模板「{name}」？",
  "config.templates.columns.name": "模板名称",
  "config.templates.columns.benchmark": "绑定 Benchmark",
  "config.templates.columns.version": "版本",
  "config.templates.columns.status": "状态",
  "config.templates.columns.actions": "操作",
  "config.templates.generic": "通用",
  "config.templates.form.name": "模板名称",
  "config.templates.form.benchmark": "绑定 Benchmark（空=通用）",
  "config.templates.form.template": "模板内容",
  "config.templates.form.templateHelp": "支持变量：{question} {expected} {model_answer} {rule_tags} {task_category}",
  "config.templates.form.isActive": "启用",

  "config.adapters.title": "Benchmark Adapter",
  "config.adapters.description": "Adapter 由后端代码注册，此处仅查看。",
  "config.adapters.columns.name": "名称",
  "config.adapters.columns.description": "描述",
  "config.adapters.columns.fields": "检测字段",
  "config.adapters.columns.builtin": "类型",
  "config.adapters.builtin": "内置",
  "config.adapters.custom": "自定义",

  "config.tabs.users": "用户管理",
  "config.users.title": "用户管理",
  "config.users.create": "新建用户",
  "config.users.edit": "编辑用户",
  "config.users.deactivate": "停用",
  "config.users.activate": "启用",
  "config.users.deactivateConfirm": "确认停用用户「{name}」？停用后该用户将无法登录。",
  "config.users.columns.username": "用户名",
  "config.users.columns.email": "邮箱",
  "config.users.columns.role": "角色",
  "config.users.columns.status": "状态",
  "config.users.columns.createdAt": "创建时间",
  "config.users.columns.actions": "操作",
  "config.users.active": "正常",
  "config.users.inactive": "已停用",
  "config.users.form.username": "用户名",
  "config.users.form.email": "邮箱",
  "config.users.form.password": "密码",
  "config.users.form.passwordHelp": "编辑时留空则不修改密码",
  "config.users.form.role": "角色",
  "config.users.form.isActive": "启用",
  "config.users.role.admin": "管理员",
  "config.users.role.analyst": "分析师",
  "config.users.role.viewer": "只读用户",
  "config.users.cannotDeactivateSelf": "不能停用自己的账号"
}
```

- [ ] **Step 2: Add English translation keys**

Add to `frontend/src/locales/en.json`:

```json
{
  "config.title": "Analysis Config",
  "config.tabs.rules": "Rules",
  "config.tabs.strategies": "LLM Strategies",
  "config.tabs.templates": "Prompt Templates",
  "config.tabs.adapters": "Benchmark Adapters",

  "config.rules.title": "Analysis Rules",
  "config.rules.create": "New Rule",
  "config.rules.edit": "Edit Rule",
  "config.rules.delete": "Delete",
  "config.rules.deleteConfirm": "Delete rule \"{name}\"?",
  "config.rules.columns.name": "Name",
  "config.rules.columns.field": "Target Field",
  "config.rules.columns.conditionType": "Condition",
  "config.rules.columns.tags": "Tags",
  "config.rules.columns.confidence": "Confidence",
  "config.rules.columns.priority": "Priority",
  "config.rules.columns.status": "Status",
  "config.rules.columns.actions": "Actions",
  "config.rules.enabled": "Enabled",
  "config.rules.disabled": "Disabled",
  "config.rules.form.name": "Name",
  "config.rules.form.description": "Description",
  "config.rules.form.field": "Target Field",
  "config.rules.form.fieldHelp": "e.g. model_answer, extracted_code",
  "config.rules.form.conditionType": "Condition Type",
  "config.rules.form.pattern": "Pattern / Value",
  "config.rules.form.tags": "Output Tags",
  "config.rules.form.tagsHelp": "Tag path, e.g. Format Errors.Empty Answer",
  "config.rules.form.confidence": "Confidence",
  "config.rules.form.priority": "Priority (lower = runs first)",
  "config.rules.form.isActive": "Enabled",

  "config.strategies.title": "LLM Trigger Strategies",
  "config.strategies.create": "New Strategy",
  "config.strategies.edit": "Edit Strategy",
  "config.strategies.delete": "Delete",
  "config.strategies.deleteConfirm": "Delete strategy \"{name}\"?",
  "config.strategies.columns.name": "Name",
  "config.strategies.columns.type": "Type",
  "config.strategies.columns.provider": "LLM Provider",
  "config.strategies.columns.model": "Model",
  "config.strategies.columns.maxConcurrent": "Max Concurrent",
  "config.strategies.columns.dailyBudget": "Daily Budget",
  "config.strategies.columns.status": "Status",
  "config.strategies.columns.actions": "Actions",
  "config.strategies.form.name": "Name",
  "config.strategies.form.type": "Strategy Type",
  "config.strategies.form.provider": "LLM Provider",
  "config.strategies.form.model": "Model Name",
  "config.strategies.form.maxConcurrent": "Max Concurrent",
  "config.strategies.form.dailyBudget": "Daily Budget (USD)",
  "config.strategies.form.isActive": "Enabled",
  "config.strategies.type.full": "Full",
  "config.strategies.type.fallback": "Rule Fallback",
  "config.strategies.type.sample": "Sample",
  "config.strategies.type.manual": "Manual",

  "config.templates.title": "Prompt Templates",
  "config.templates.create": "New Template",
  "config.templates.edit": "Edit Template",
  "config.templates.delete": "Delete",
  "config.templates.deleteConfirm": "Delete template \"{name}\"?",
  "config.templates.columns.name": "Name",
  "config.templates.columns.benchmark": "Benchmark",
  "config.templates.columns.version": "Version",
  "config.templates.columns.status": "Status",
  "config.templates.columns.actions": "Actions",
  "config.templates.generic": "Generic",
  "config.templates.form.name": "Name",
  "config.templates.form.benchmark": "Benchmark (empty = generic)",
  "config.templates.form.template": "Template Content",
  "config.templates.form.templateHelp": "Variables: {question} {expected} {model_answer} {rule_tags} {task_category}",
  "config.templates.form.isActive": "Enabled",

  "config.adapters.title": "Benchmark Adapters",
  "config.adapters.description": "Adapters are registered server-side. This panel is read-only.",
  "config.adapters.columns.name": "Name",
  "config.adapters.columns.description": "Description",
  "config.adapters.columns.fields": "Detected Fields",
  "config.adapters.columns.builtin": "Type",
  "config.adapters.builtin": "Built-in",
  "config.adapters.custom": "Custom",

  "config.tabs.users": "Users",
  "config.users.title": "User Management",
  "config.users.create": "New User",
  "config.users.edit": "Edit User",
  "config.users.deactivate": "Deactivate",
  "config.users.activate": "Activate",
  "config.users.deactivateConfirm": "Deactivate user \"{name}\"? They will no longer be able to log in.",
  "config.users.columns.username": "Username",
  "config.users.columns.email": "Email",
  "config.users.columns.role": "Role",
  "config.users.columns.status": "Status",
  "config.users.columns.createdAt": "Created",
  "config.users.columns.actions": "Actions",
  "config.users.active": "Active",
  "config.users.inactive": "Inactive",
  "config.users.form.username": "Username",
  "config.users.form.email": "Email",
  "config.users.form.password": "Password",
  "config.users.form.passwordHelp": "Leave blank when editing to keep current password",
  "config.users.form.role": "Role",
  "config.users.form.isActive": "Active",
  "config.users.role.admin": "Admin",
  "config.users.role.analyst": "Analyst",
  "config.users.role.viewer": "Viewer",
  "config.users.cannotDeactivateSelf": "Cannot deactivate your own account"
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/locales/zh.json frontend/src/locales/en.json
git commit -m "feat: add i18n keys for analysis config page"
```

---

### Task 3: TanStack Query Hooks — Config CRUD

**Files:**
- Create: `frontend/src/api/queries/config.ts`
- Create: `frontend/src/api/queries/config.test.ts`

All write operations require `Analyst` or `Admin` role. Role enforcement is already done server-side; the frontend disables buttons based on the user's role from `AuthContext`, but the hooks themselves are role-agnostic.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/api/queries/config.test.ts`:

```typescript
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode } from "react";

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

jest.mock("../client", () => ({
  __esModule: true,
  default: { get: jest.fn(), post: jest.fn(), put: jest.fn(), delete: jest.fn() },
}));

import apiClient from "../client";
const mockedGet = apiClient.get as jest.Mock;
const mockedPost = apiClient.post as jest.Mock;
const mockedPut = apiClient.put as jest.Mock;
const mockedDelete = apiClient.delete as jest.Mock;

import {
  useRules,
  useCreateRule,
  useUpdateRule,
  useDeleteRule,
  useStrategies,
  useCreateStrategy,
  useUpdateStrategy,
  useDeleteStrategy,
  useTemplates,
  useCreateTemplate,
  useUpdateTemplate,
  useDeleteTemplate,
  useAdapters,
} from "./config";

// ── Rules ──────────────────────────────────────────────────────────────────

describe("useRules", () => {
  beforeEach(() => jest.clearAllMocks());

  it("fetches the rules list", async () => {
    const mockRules = [
      {
        id: "r1",
        name: "EmptyAnswerRule",
        description: "Detects empty answers",
        field: "model_answer",
        condition: { type: "field_missing" },
        tags: ["格式与规范错误.空回答"],
        confidence: 1.0,
        priority: 1,
        is_active: true,
        created_by: "system",
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
    ];
    mockedGet.mockResolvedValueOnce({ data: mockRules });

    const { result } = renderHook(() => useRules(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockRules);
    expect(mockedGet).toHaveBeenCalledWith("/rules");
  });
});

describe("useCreateRule", () => {
  beforeEach(() => jest.clearAllMocks());

  it("posts to /rules and invalidates rules query", async () => {
    const newRule = {
      name: "MyRule",
      description: "test",
      field: "model_answer",
      condition: { type: "regex" as const, pattern: "error" },
      tags: ["格式与规范错误"],
      confidence: 0.9,
      priority: 10,
      is_active: true,
    };
    const created = { id: "r2", created_by: "user1", created_at: "...", updated_at: "...", ...newRule };
    mockedPost.mockResolvedValueOnce({ data: created });

    const { result } = renderHook(() => useCreateRule(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync(newRule);
    });

    expect(mockedPost).toHaveBeenCalledWith("/rules", newRule);
  });
});

describe("useUpdateRule", () => {
  beforeEach(() => jest.clearAllMocks());

  it("puts to /rules/{id}", async () => {
    mockedPut.mockResolvedValueOnce({ data: { id: "r1", is_active: false } });

    const { result } = renderHook(() => useUpdateRule(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync({ id: "r1", data: { is_active: false } });
    });

    expect(mockedPut).toHaveBeenCalledWith("/rules/r1", { is_active: false });
  });
});

describe("useDeleteRule", () => {
  beforeEach(() => jest.clearAllMocks());

  it("deletes /rules/{id}", async () => {
    mockedDelete.mockResolvedValueOnce({ data: null });

    const { result } = renderHook(() => useDeleteRule(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync("r1");
    });

    expect(mockedDelete).toHaveBeenCalledWith("/rules/r1");
  });
});

// ── Strategies ─────────────────────────────────────────────────────────────

describe("useStrategies", () => {
  beforeEach(() => jest.clearAllMocks());

  it("fetches the strategies list", async () => {
    mockedGet.mockResolvedValueOnce({ data: [] });
    const { result } = renderHook(() => useStrategies(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedGet).toHaveBeenCalledWith("/llm/strategies");
  });
});

describe("useCreateStrategy", () => {
  beforeEach(() => jest.clearAllMocks());

  it("posts to /llm/strategies", async () => {
    mockedPost.mockResolvedValueOnce({ data: { id: "s1" } });
    const { result } = renderHook(() => useCreateStrategy(), {
      wrapper: createWrapper(),
    });
    await act(async () => {
      await result.current.mutateAsync({
        name: "S1",
        strategy_type: "fallback",
        config: {},
        llm_provider: "openai",
        llm_model: "gpt-4o",
        prompt_template_id: null,
        max_concurrent: 5,
        daily_budget: 10,
        is_active: true,
      });
    });
    expect(mockedPost).toHaveBeenCalledWith("/llm/strategies", expect.any(Object));
  });
});

describe("useUpdateStrategy / useDeleteStrategy", () => {
  beforeEach(() => jest.clearAllMocks());

  it("puts to /llm/strategies/{id}", async () => {
    mockedPut.mockResolvedValueOnce({ data: { id: "s1" } });
    const { result } = renderHook(() => useUpdateStrategy(), {
      wrapper: createWrapper(),
    });
    await act(async () => {
      await result.current.mutateAsync({ id: "s1", data: { is_active: false } });
    });
    expect(mockedPut).toHaveBeenCalledWith("/llm/strategies/s1", { is_active: false });
  });

  it("deletes /llm/strategies/{id}", async () => {
    mockedDelete.mockResolvedValueOnce({ data: null });
    const { result } = renderHook(() => useDeleteStrategy(), {
      wrapper: createWrapper(),
    });
    await act(async () => {
      await result.current.mutateAsync("s1");
    });
    expect(mockedDelete).toHaveBeenCalledWith("/llm/strategies/s1");
  });
});

// ── Templates ──────────────────────────────────────────────────────────────

describe("useTemplates", () => {
  beforeEach(() => jest.clearAllMocks());

  it("fetches the templates list", async () => {
    mockedGet.mockResolvedValueOnce({ data: [] });
    const { result } = renderHook(() => useTemplates(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedGet).toHaveBeenCalledWith("/llm/prompt-templates");
  });
});

describe("useCreateTemplate / useUpdateTemplate / useDeleteTemplate", () => {
  beforeEach(() => jest.clearAllMocks());

  it("posts to /llm/prompt-templates", async () => {
    mockedPost.mockResolvedValueOnce({ data: { id: "t1" } });
    const { result } = renderHook(() => useCreateTemplate(), {
      wrapper: createWrapper(),
    });
    await act(async () => {
      await result.current.mutateAsync({
        name: "T1",
        benchmark: null,
        template: "Analyze: {question}",
        is_active: true,
      });
    });
    expect(mockedPost).toHaveBeenCalledWith("/llm/prompt-templates", expect.any(Object));
  });

  it("puts to /llm/prompt-templates/{id}", async () => {
    mockedPut.mockResolvedValueOnce({ data: { id: "t1" } });
    const { result } = renderHook(() => useUpdateTemplate(), {
      wrapper: createWrapper(),
    });
    await act(async () => {
      await result.current.mutateAsync({ id: "t1", data: { is_active: false } });
    });
    expect(mockedPut).toHaveBeenCalledWith("/llm/prompt-templates/t1", { is_active: false });
  });

  it("deletes /llm/prompt-templates/{id}", async () => {
    mockedDelete.mockResolvedValueOnce({ data: null });
    const { result } = renderHook(() => useDeleteTemplate(), {
      wrapper: createWrapper(),
    });
    await act(async () => {
      await result.current.mutateAsync("t1");
    });
    expect(mockedDelete).toHaveBeenCalledWith("/llm/prompt-templates/t1");
  });
});

// ── Adapters ───────────────────────────────────────────────────────────────

describe("useAdapters", () => {
  beforeEach(() => jest.clearAllMocks());

  it("fetches the adapters list", async () => {
    const mockAdapters = [
      { name: "mmlu", description: "MMLU adapter", detected_fields: ["subject"], is_builtin: true },
    ];
    mockedGet.mockResolvedValueOnce({ data: mockAdapters });
    const { result } = renderHook(() => useAdapters(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockAdapters);
    expect(mockedGet).toHaveBeenCalledWith("/ingest/adapters");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx jest src/api/queries/config.test.ts --no-cache`
Expected: FAIL — module `./config` not found

- [ ] **Step 3: Implement the hooks**

Create `frontend/src/api/queries/config.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "../client";
import type {
  AnalysisRule,
  AnalysisRuleCreate,
  AnalysisRuleUpdate,
  AnalysisStrategy,
  AnalysisStrategyCreate,
  AnalysisStrategyUpdate,
  PromptTemplate,
  PromptTemplateCreate,
  PromptTemplateUpdate,
  BenchmarkAdapter,
} from "../../types/api";

// ── Rules ──────────────────────────────────────────────────────────────────

export function useRules() {
  return useQuery<AnalysisRule[]>({
    queryKey: ["rules"],
    queryFn: async () => {
      const { data } = await apiClient.get("/rules");
      return data;
    },
  });
}

export function useCreateRule() {
  const queryClient = useQueryClient();
  return useMutation<AnalysisRule, Error, AnalysisRuleCreate>({
    mutationFn: async (body) => {
      const { data } = await apiClient.post("/rules", body);
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["rules"] }),
  });
}

export function useUpdateRule() {
  const queryClient = useQueryClient();
  return useMutation<AnalysisRule, Error, { id: string; data: AnalysisRuleUpdate }>({
    mutationFn: async ({ id, data: body }) => {
      const { data } = await apiClient.put(`/rules/${id}`, body);
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["rules"] }),
  });
}

export function useDeleteRule() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      await apiClient.delete(`/rules/${id}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["rules"] }),
  });
}

// ── Strategies ─────────────────────────────────────────────────────────────

export function useStrategies() {
  return useQuery<AnalysisStrategy[]>({
    queryKey: ["strategies"],
    queryFn: async () => {
      const { data } = await apiClient.get("/llm/strategies");
      return data;
    },
  });
}

export function useCreateStrategy() {
  const queryClient = useQueryClient();
  return useMutation<AnalysisStrategy, Error, AnalysisStrategyCreate>({
    mutationFn: async (body) => {
      const { data } = await apiClient.post("/llm/strategies", body);
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["strategies"] }),
  });
}

export function useUpdateStrategy() {
  const queryClient = useQueryClient();
  return useMutation<AnalysisStrategy, Error, { id: string; data: AnalysisStrategyUpdate }>({
    mutationFn: async ({ id, data: body }) => {
      const { data } = await apiClient.put(`/llm/strategies/${id}`, body);
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["strategies"] }),
  });
}

export function useDeleteStrategy() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      await apiClient.delete(`/llm/strategies/${id}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["strategies"] }),
  });
}

// ── Templates ──────────────────────────────────────────────────────────────

export function useTemplates() {
  return useQuery<PromptTemplate[]>({
    queryKey: ["promptTemplates"],
    queryFn: async () => {
      const { data } = await apiClient.get("/llm/prompt-templates");
      return data;
    },
  });
}

export function useCreateTemplate() {
  const queryClient = useQueryClient();
  return useMutation<PromptTemplate, Error, PromptTemplateCreate>({
    mutationFn: async (body) => {
      const { data } = await apiClient.post("/llm/prompt-templates", body);
      return data;
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["promptTemplates"] }),
  });
}

export function useUpdateTemplate() {
  const queryClient = useQueryClient();
  return useMutation<PromptTemplate, Error, { id: string; data: PromptTemplateUpdate }>({
    mutationFn: async ({ id, data: body }) => {
      const { data } = await apiClient.put(`/llm/prompt-templates/${id}`, body);
      return data;
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["promptTemplates"] }),
  });
}

export function useDeleteTemplate() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      await apiClient.delete(`/llm/prompt-templates/${id}`);
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["promptTemplates"] }),
  });
}

// ── Adapters ───────────────────────────────────────────────────────────────

export function useAdapters() {
  return useQuery<BenchmarkAdapter[]>({
    queryKey: ["adapters"],
    queryFn: async () => {
      const { data } = await apiClient.get("/ingest/adapters");
      return data;
    },
  });
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx jest src/api/queries/config.test.ts --no-cache`
Expected: PASS (14 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/queries/config.ts \
        frontend/src/api/queries/config.test.ts
git commit -m "feat: add config CRUD query hooks (rules, strategies, templates, adapters)"
```

---

### Task 4: RuleFormModal Component

**Files:**
- Create: `frontend/src/pages/Config/components/RuleFormModal.tsx`
- Create: `frontend/src/pages/Config/components/RuleFormModal.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/Config/components/RuleFormModal.test.tsx`:

```typescript
import { render, screen, fireEvent } from "@testing-library/react";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "config.rules.create": "新建规则",
        "config.rules.edit": "编辑规则",
        "config.rules.form.name": "规则名称",
        "config.rules.form.field": "目标字段",
        "config.rules.form.conditionType": "条件类型",
        "config.rules.form.pattern": "匹配模式/值",
        "config.rules.form.tags": "产出标签",
        "config.rules.form.confidence": "置信度",
        "config.rules.form.priority": "优先级（越小越先执行）",
        "config.rules.form.isActive": "启用",
        "common.save": "保存",
        "common.cancel": "取消",
      };
      return map[key] ?? key;
    },
  }),
}));

import RuleFormModal from "./RuleFormModal";
import type { AnalysisRule } from "../../../types/api";

const mockRule: AnalysisRule = {
  id: "r1",
  name: "EmptyAnswerRule",
  description: "Detects empty model answers",
  field: "model_answer",
  condition: { type: "field_missing" },
  tags: ["格式与规范错误.空回答"],
  confidence: 1.0,
  priority: 1,
  is_active: true,
  created_by: "system",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("RuleFormModal", () => {
  it("renders create title when no rule provided", () => {
    render(
      <RuleFormModal
        open={true}
        rule={null}
        onSubmit={jest.fn()}
        onCancel={jest.fn()}
        loading={false}
      />
    );
    expect(screen.getByText("新建规则")).toBeInTheDocument();
  });

  it("renders edit title when rule is provided", () => {
    render(
      <RuleFormModal
        open={true}
        rule={mockRule}
        onSubmit={jest.fn()}
        onCancel={jest.fn()}
        loading={false}
      />
    );
    expect(screen.getByText("编辑规则")).toBeInTheDocument();
  });

  it("pre-fills form fields when editing", () => {
    render(
      <RuleFormModal
        open={true}
        rule={mockRule}
        onSubmit={jest.fn()}
        onCancel={jest.fn()}
        loading={false}
      />
    );
    expect(screen.getByDisplayValue("EmptyAnswerRule")).toBeInTheDocument();
    expect(screen.getByDisplayValue("model_answer")).toBeInTheDocument();
  });

  it("calls onCancel when cancel button is clicked", () => {
    const onCancel = jest.fn();
    render(
      <RuleFormModal
        open={true}
        rule={null}
        onSubmit={jest.fn()}
        onCancel={onCancel}
        loading={false}
      />
    );
    fireEvent.click(screen.getByText("取消"));
    expect(onCancel).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/pages/Config/components/RuleFormModal.test.tsx --no-cache`
Expected: FAIL — module `./RuleFormModal` not found

- [ ] **Step 3: Implement RuleFormModal**

Create `frontend/src/pages/Config/components/RuleFormModal.tsx`:

```typescript
import { useEffect } from "react";
import { Modal, Form, Input, InputNumber, Select, Switch, Space } from "antd";
import { useTranslation } from "react-i18next";
import type { AnalysisRule, AnalysisRuleCreate, RuleConditionType } from "../../../types/api";

const CONDITION_TYPES: RuleConditionType[] = [
  "regex",
  "contains",
  "not_contains",
  "length_gt",
  "length_lt",
  "field_equals",
  "field_missing",
  "python_expr",
];

interface RuleFormModalProps {
  open: boolean;
  rule: AnalysisRule | null;
  onSubmit: (values: AnalysisRuleCreate) => void;
  onCancel: () => void;
  loading: boolean;
}

export default function RuleFormModal({
  open,
  rule,
  onSubmit,
  onCancel,
  loading,
}: RuleFormModalProps) {
  const { t } = useTranslation();
  const [form] = Form.useForm<AnalysisRuleCreate>();

  useEffect(() => {
    if (open) {
      if (rule) {
        form.setFieldsValue({
          name: rule.name,
          description: rule.description,
          field: rule.field,
          condition: rule.condition,
          tags: rule.tags,
          confidence: rule.confidence,
          priority: rule.priority,
          is_active: rule.is_active,
        });
      } else {
        form.resetFields();
        form.setFieldsValue({ confidence: 0.9, priority: 10, is_active: true });
      }
    }
  }, [open, rule, form]);

  const handleOk = () => {
    form.validateFields().then(onSubmit);
  };

  const title = rule ? t("config.rules.edit") : t("config.rules.create");

  return (
    <Modal
      title={title}
      open={open}
      onOk={handleOk}
      onCancel={onCancel}
      okText={t("common.save")}
      cancelText={t("common.cancel")}
      confirmLoading={loading}
      width={600}
      destroyOnClose
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="name"
          label={t("config.rules.form.name")}
          rules={[{ required: true }]}
        >
          <Input />
        </Form.Item>

        <Form.Item name="description" label={t("config.rules.form.description")}>
          <Input.TextArea rows={2} />
        </Form.Item>

        <Form.Item
          name="field"
          label={t("config.rules.form.field")}
          extra={t("config.rules.form.fieldHelp")}
          rules={[{ required: true }]}
        >
          <Input />
        </Form.Item>

        <Form.Item
          name={["condition", "type"]}
          label={t("config.rules.form.conditionType")}
          rules={[{ required: true }]}
        >
          <Select
            options={CONDITION_TYPES.map((ct) => ({ label: ct, value: ct }))}
          />
        </Form.Item>

        <Form.Item
          name={["condition", "pattern"]}
          label={t("config.rules.form.pattern")}
        >
          <Input />
        </Form.Item>

        <Form.Item
          name="tags"
          label={t("config.rules.form.tags")}
          extra={t("config.rules.form.tagsHelp")}
          rules={[{ required: true }]}
        >
          <Select mode="tags" tokenSeparators={[","]} />
        </Form.Item>

        <Space style={{ width: "100%" }}>
          <Form.Item
            name="confidence"
            label={t("config.rules.form.confidence")}
            rules={[{ required: true }]}
          >
            <InputNumber min={0} max={1} step={0.05} style={{ width: 120 }} />
          </Form.Item>

          <Form.Item
            name="priority"
            label={t("config.rules.form.priority")}
            rules={[{ required: true }]}
          >
            <InputNumber min={1} style={{ width: 120 }} />
          </Form.Item>
        </Space>

        <Form.Item name="is_active" label={t("config.rules.form.isActive")} valuePropName="checked">
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx jest src/pages/Config/components/RuleFormModal.test.tsx --no-cache`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Config/components/RuleFormModal.tsx \
        frontend/src/pages/Config/components/RuleFormModal.test.tsx
git commit -m "feat: add RuleFormModal component"
```

---

### Task 5: RulesPanel Component

**Files:**
- Create: `frontend/src/pages/Config/components/RulesPanel.tsx`
- Create: `frontend/src/pages/Config/components/RulesPanel.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/Config/components/RulesPanel.test.tsx`:

```typescript
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode } from "react";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, string>) => {
      const map: Record<string, string> = {
        "config.rules.title": "分析规则",
        "config.rules.create": "新建规则",
        "config.rules.delete": "删除",
        "config.rules.edit": "编辑规则",
        "config.rules.columns.name": "规则名称",
        "config.rules.columns.field": "目标字段",
        "config.rules.columns.conditionType": "条件类型",
        "config.rules.columns.tags": "产出标签",
        "config.rules.columns.confidence": "置信度",
        "config.rules.columns.priority": "优先级",
        "config.rules.columns.status": "状态",
        "config.rules.columns.actions": "操作",
        "config.rules.enabled": "启用",
        "config.rules.disabled": "停用",
        "config.rules.deleteConfirm": `确认删除规则「${opts?.name ?? ""}」？`,
        "common.edit": "编辑",
        "common.save": "保存",
        "common.cancel": "取消",
      };
      return map[key] ?? key;
    },
  }),
}));

jest.mock("../../../api/queries/config", () => ({
  useRules: jest.fn(),
  useCreateRule: jest.fn(),
  useUpdateRule: jest.fn(),
  useDeleteRule: jest.fn(),
}));

import RulesPanel from "./RulesPanel";
import { useRules, useCreateRule, useUpdateRule, useDeleteRule } from "../../../api/queries/config";

const mockRule = {
  id: "r1",
  name: "EmptyAnswerRule",
  description: "",
  field: "model_answer",
  condition: { type: "field_missing" },
  tags: ["格式与规范错误.空回答"],
  confidence: 1.0,
  priority: 1,
  is_active: true,
  created_by: "system",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("RulesPanel", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useRules as jest.Mock).mockReturnValue({ data: [mockRule], isLoading: false });
    (useCreateRule as jest.Mock).mockReturnValue({ mutateAsync: jest.fn(), isPending: false });
    (useUpdateRule as jest.Mock).mockReturnValue({ mutateAsync: jest.fn(), isPending: false });
    (useDeleteRule as jest.Mock).mockReturnValue({ mutateAsync: jest.fn(), isPending: false });
  });

  it("renders the panel title and create button", () => {
    render(<RulesPanel />, { wrapper: createWrapper() });
    expect(screen.getByText("分析规则")).toBeInTheDocument();
    expect(screen.getByText("新建规则")).toBeInTheDocument();
  });

  it("renders rule rows", () => {
    render(<RulesPanel />, { wrapper: createWrapper() });
    expect(screen.getByText("EmptyAnswerRule")).toBeInTheDocument();
    expect(screen.getByText("model_answer")).toBeInTheDocument();
  });

  it("renders enabled/disabled badge for rule status", () => {
    render(<RulesPanel />, { wrapper: createWrapper() });
    expect(screen.getByText("启用")).toBeInTheDocument();
  });

  it("opens form modal when create button is clicked", () => {
    render(<RulesPanel />, { wrapper: createWrapper() });
    fireEvent.click(screen.getByText("新建规则"));
    expect(screen.getByText("新建规则", { selector: ".ant-modal-title *" })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/pages/Config/components/RulesPanel.test.tsx --no-cache`
Expected: FAIL — module `./RulesPanel` not found

- [ ] **Step 3: Implement RulesPanel**

Create `frontend/src/pages/Config/components/RulesPanel.tsx`:

```typescript
import { useState, useCallback } from "react";
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Popconfirm,
  Switch,
  message,
} from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import type { ColumnsType } from "antd/es/table";
import {
  useRules,
  useCreateRule,
  useUpdateRule,
  useDeleteRule,
} from "../../../api/queries/config";
import RuleFormModal from "./RuleFormModal";
import type { AnalysisRule, AnalysisRuleCreate } from "../../../types/api";

export default function RulesPanel() {
  const { t } = useTranslation();
  const { data: rules = [], isLoading } = useRules();
  const createRule = useCreateRule();
  const updateRule = useUpdateRule();
  const deleteRule = useDeleteRule();

  const [modalOpen, setModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<AnalysisRule | null>(null);

  const openCreate = useCallback(() => {
    setEditingRule(null);
    setModalOpen(true);
  }, []);

  const openEdit = useCallback((rule: AnalysisRule) => {
    setEditingRule(rule);
    setModalOpen(true);
  }, []);

  const handleSubmit = useCallback(
    async (values: AnalysisRuleCreate) => {
      try {
        if (editingRule) {
          await updateRule.mutateAsync({ id: editingRule.id, data: values });
        } else {
          await createRule.mutateAsync(values);
        }
        setModalOpen(false);
      } catch {
        message.error(t("common.saveFailed"));
      }
    },
    [editingRule, createRule, updateRule, t]
  );

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await deleteRule.mutateAsync(id);
      } catch {
        message.error(t("common.deleteFailed"));
      }
    },
    [deleteRule, t]
  );

  const handleToggle = useCallback(
    async (rule: AnalysisRule, is_active: boolean) => {
      try {
        await updateRule.mutateAsync({ id: rule.id, data: { is_active } });
      } catch {
        message.error(t("common.saveFailed"));
      }
    },
    [updateRule, t]
  );

  const columns: ColumnsType<AnalysisRule> = [
    {
      title: t("config.rules.columns.name"),
      dataIndex: "name",
      key: "name",
      ellipsis: true,
    },
    {
      title: t("config.rules.columns.field"),
      dataIndex: "field",
      key: "field",
      width: 140,
    },
    {
      title: t("config.rules.columns.conditionType"),
      key: "conditionType",
      width: 130,
      render: (_, r) => <Tag>{r.condition.type}</Tag>,
    },
    {
      title: t("config.rules.columns.tags"),
      dataIndex: "tags",
      key: "tags",
      render: (tags: string[]) => (
        <Space size={[4, 4]} wrap>
          {tags.map((tag) => (
            <Tag key={tag} color="red">
              {tag}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: t("config.rules.columns.confidence"),
      dataIndex: "confidence",
      key: "confidence",
      width: 90,
      align: "right",
      render: (v: number) => `${(v * 100).toFixed(0)}%`,
    },
    {
      title: t("config.rules.columns.priority"),
      dataIndex: "priority",
      key: "priority",
      width: 80,
      align: "right",
      sorter: (a, b) => a.priority - b.priority,
    },
    {
      title: t("config.rules.columns.status"),
      key: "status",
      width: 90,
      align: "center",
      render: (_, rule) => (
        <Switch
          checked={rule.is_active}
          checkedChildren={t("config.rules.enabled")}
          unCheckedChildren={t("config.rules.disabled")}
          onChange={(checked) => handleToggle(rule, checked)}
        />
      ),
    },
    {
      title: t("config.rules.columns.actions"),
      key: "actions",
      width: 120,
      render: (_, rule) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            size="small"
            onClick={() => openEdit(rule)}
          />
          <Popconfirm
            title={t("config.rules.deleteConfirm", { name: rule.name })}
            onConfirm={() => handleDelete(rule.id)}
          >
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              size="small"
            />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card
      title={t("config.rules.title")}
      extra={
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={openCreate}
        >
          {t("config.rules.create")}
        </Button>
      }
    >
      <Table<AnalysisRule>
        columns={columns}
        dataSource={rules}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={{ pageSize: 15, hideOnSinglePage: true }}
      />

      <RuleFormModal
        open={modalOpen}
        rule={editingRule}
        onSubmit={handleSubmit}
        onCancel={() => setModalOpen(false)}
        loading={createRule.isPending || updateRule.isPending}
      />
    </Card>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx jest src/pages/Config/components/RulesPanel.test.tsx --no-cache`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Config/components/RulesPanel.tsx \
        frontend/src/pages/Config/components/RulesPanel.test.tsx
git commit -m "feat: add RulesPanel with create/edit/delete/toggle"
```

---

### Task 6: StrategyFormModal + StrategiesPanel

**Files:**
- Create: `frontend/src/pages/Config/components/StrategyFormModal.tsx`
- Create: `frontend/src/pages/Config/components/StrategyFormModal.test.tsx`
- Create: `frontend/src/pages/Config/components/StrategiesPanel.tsx`
- Create: `frontend/src/pages/Config/components/StrategiesPanel.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/pages/Config/components/StrategyFormModal.test.tsx`:

```typescript
import { render, screen, fireEvent } from "@testing-library/react";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "config.strategies.create": "新建策略",
        "config.strategies.edit": "编辑策略",
        "config.strategies.form.name": "策略名称",
        "config.strategies.form.type": "策略类型",
        "config.strategies.form.provider": "LLM 提供商",
        "config.strategies.form.model": "模型名称",
        "config.strategies.form.maxConcurrent": "最大并发数",
        "config.strategies.form.dailyBudget": "每日预算上限（美元）",
        "config.strategies.form.isActive": "启用",
        "common.save": "保存",
        "common.cancel": "取消",
      };
      return map[key] ?? key;
    },
  }),
}));

import StrategyFormModal from "./StrategyFormModal";

describe("StrategyFormModal", () => {
  it("renders create title when no strategy provided", () => {
    render(
      <StrategyFormModal
        open={true}
        strategy={null}
        onSubmit={jest.fn()}
        onCancel={jest.fn()}
        loading={false}
      />
    );
    expect(screen.getByText("新建策略")).toBeInTheDocument();
  });

  it("renders edit title when strategy is provided", () => {
    render(
      <StrategyFormModal
        open={true}
        strategy={{
          id: "s1",
          name: "FallbackStrategy",
          strategy_type: "fallback",
          config: {},
          llm_provider: "openai",
          llm_model: "gpt-4o",
          prompt_template_id: null,
          max_concurrent: 5,
          daily_budget: 10,
          is_active: true,
          created_by: "admin",
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        }}
        onSubmit={jest.fn()}
        onCancel={jest.fn()}
        loading={false}
      />
    );
    expect(screen.getByText("编辑策略")).toBeInTheDocument();
  });

  it("calls onCancel when cancel is clicked", () => {
    const onCancel = jest.fn();
    render(
      <StrategyFormModal
        open={true}
        strategy={null}
        onSubmit={jest.fn()}
        onCancel={onCancel}
        loading={false}
      />
    );
    fireEvent.click(screen.getByText("取消"));
    expect(onCancel).toHaveBeenCalled();
  });
});
```

Create `frontend/src/pages/Config/components/StrategiesPanel.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode } from "react";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "config.strategies.title": "LLM 触发策略",
        "config.strategies.create": "新建策略",
        "config.strategies.columns.name": "策略名称",
        "config.strategies.columns.type": "类型",
        "config.strategies.columns.provider": "LLM 提供商",
        "config.strategies.columns.model": "模型",
        "config.strategies.columns.maxConcurrent": "最大并发",
        "config.strategies.columns.dailyBudget": "每日预算",
        "config.strategies.columns.status": "状态",
        "config.strategies.columns.actions": "操作",
        "config.strategies.enabled": "启用",
        "config.strategies.type.fallback": "规则兜底",
        "common.save": "保存",
        "common.cancel": "取消",
      };
      return map[key] ?? key;
    },
  }),
}));

jest.mock("../../../api/queries/config", () => ({
  useStrategies: jest.fn(),
  useCreateStrategy: jest.fn(),
  useUpdateStrategy: jest.fn(),
  useDeleteStrategy: jest.fn(),
  useTemplates: jest.fn(),
}));

import StrategiesPanel from "./StrategiesPanel";
import {
  useStrategies,
  useCreateStrategy,
  useUpdateStrategy,
  useDeleteStrategy,
  useTemplates,
} from "../../../api/queries/config";

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("StrategiesPanel", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useStrategies as jest.Mock).mockReturnValue({
      data: [
        {
          id: "s1",
          name: "FallbackStrategy",
          strategy_type: "fallback",
          config: {},
          llm_provider: "openai",
          llm_model: "gpt-4o",
          prompt_template_id: null,
          max_concurrent: 5,
          daily_budget: 10,
          is_active: true,
          created_by: "admin",
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
      ],
      isLoading: false,
    });
    (useCreateStrategy as jest.Mock).mockReturnValue({ mutateAsync: jest.fn(), isPending: false });
    (useUpdateStrategy as jest.Mock).mockReturnValue({ mutateAsync: jest.fn(), isPending: false });
    (useDeleteStrategy as jest.Mock).mockReturnValue({ mutateAsync: jest.fn(), isPending: false });
    (useTemplates as jest.Mock).mockReturnValue({ data: [], isLoading: false });
  });

  it("renders panel title and strategy row", () => {
    render(<StrategiesPanel />, { wrapper: createWrapper() });
    expect(screen.getByText("LLM 触发策略")).toBeInTheDocument();
    expect(screen.getByText("FallbackStrategy")).toBeInTheDocument();
    expect(screen.getByText("规则兜底")).toBeInTheDocument();
  });

  it("renders create button", () => {
    render(<StrategiesPanel />, { wrapper: createWrapper() });
    expect(screen.getByText("新建策略")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx jest src/pages/Config/components/StrategyFormModal.test.tsx src/pages/Config/components/StrategiesPanel.test.tsx --no-cache`
Expected: FAIL — modules not found

- [ ] **Step 3: Implement StrategyFormModal**

Create `frontend/src/pages/Config/components/StrategyFormModal.tsx`:

```typescript
import { useEffect } from "react";
import { Modal, Form, Input, InputNumber, Select, Switch } from "antd";
import { useTranslation } from "react-i18next";
import { useTemplates } from "../../../api/queries/config";
import type {
  AnalysisStrategy,
  AnalysisStrategyCreate,
  LLMStrategyType,
} from "../../../types/api";

const STRATEGY_TYPES: LLMStrategyType[] = ["full", "fallback", "sample", "manual"];

interface StrategyFormModalProps {
  open: boolean;
  strategy: AnalysisStrategy | null;
  onSubmit: (values: AnalysisStrategyCreate) => void;
  onCancel: () => void;
  loading: boolean;
}

export default function StrategyFormModal({
  open,
  strategy,
  onSubmit,
  onCancel,
  loading,
}: StrategyFormModalProps) {
  const { t } = useTranslation();
  const [form] = Form.useForm<AnalysisStrategyCreate>();
  const { data: templates = [] } = useTemplates();

  useEffect(() => {
    if (open) {
      if (strategy) {
        form.setFieldsValue({
          name: strategy.name,
          strategy_type: strategy.strategy_type,
          config: strategy.config,
          llm_provider: strategy.llm_provider,
          llm_model: strategy.llm_model,
          prompt_template_id: strategy.prompt_template_id,
          max_concurrent: strategy.max_concurrent,
          daily_budget: strategy.daily_budget,
          is_active: strategy.is_active,
        });
      } else {
        form.resetFields();
        form.setFieldsValue({
          strategy_type: "fallback",
          max_concurrent: 5,
          daily_budget: 10,
          is_active: true,
        });
      }
    }
  }, [open, strategy, form]);

  const title = strategy
    ? t("config.strategies.edit")
    : t("config.strategies.create");

  return (
    <Modal
      title={title}
      open={open}
      onOk={() => form.validateFields().then(onSubmit)}
      onCancel={onCancel}
      okText={t("common.save")}
      cancelText={t("common.cancel")}
      confirmLoading={loading}
      width={560}
      destroyOnClose
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="name"
          label={t("config.strategies.form.name")}
          rules={[{ required: true }]}
        >
          <Input />
        </Form.Item>

        <Form.Item
          name="strategy_type"
          label={t("config.strategies.form.type")}
          rules={[{ required: true }]}
        >
          <Select
            options={STRATEGY_TYPES.map((st) => ({
              label: t(`config.strategies.type.${st}`),
              value: st,
            }))}
          />
        </Form.Item>

        <Form.Item
          name="llm_provider"
          label={t("config.strategies.form.provider")}
          rules={[{ required: true }]}
        >
          <Select
            options={[
              { label: "OpenAI", value: "openai" },
              { label: "Claude", value: "claude" },
              { label: "Local", value: "local" },
            ]}
          />
        </Form.Item>

        <Form.Item
          name="llm_model"
          label={t("config.strategies.form.model")}
          rules={[{ required: true }]}
        >
          <Input placeholder="e.g. gpt-4o, claude-sonnet-4-6" />
        </Form.Item>

        <Form.Item name="prompt_template_id" label="Prompt Template">
          <Select
            allowClear
            options={templates.map((tpl) => ({
              label: `${tpl.name}${tpl.benchmark ? ` (${tpl.benchmark})` : ""}`,
              value: tpl.id,
            }))}
          />
        </Form.Item>

        <Form.Item
          name="max_concurrent"
          label={t("config.strategies.form.maxConcurrent")}
          rules={[{ required: true }]}
        >
          <InputNumber min={1} max={100} style={{ width: 120 }} />
        </Form.Item>

        <Form.Item
          name="daily_budget"
          label={t("config.strategies.form.dailyBudget")}
          rules={[{ required: true }]}
        >
          <InputNumber min={0} step={1} prefix="$" style={{ width: 140 }} />
        </Form.Item>

        <Form.Item
          name="is_active"
          label={t("config.strategies.form.isActive")}
          valuePropName="checked"
        >
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  );
}
```

- [ ] **Step 4: Implement StrategiesPanel**

Create `frontend/src/pages/Config/components/StrategiesPanel.tsx`:

```typescript
import { useState, useCallback } from "react";
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Popconfirm,
  Switch,
  message,
} from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import type { ColumnsType } from "antd/es/table";
import {
  useStrategies,
  useCreateStrategy,
  useUpdateStrategy,
  useDeleteStrategy,
} from "../../../api/queries/config";
import StrategyFormModal from "./StrategyFormModal";
import type { AnalysisStrategy, AnalysisStrategyCreate } from "../../../types/api";

const STRATEGY_TYPE_COLORS: Record<string, string> = {
  full: "blue",
  fallback: "green",
  sample: "orange",
  manual: "purple",
};

export default function StrategiesPanel() {
  const { t } = useTranslation();
  const { data: strategies = [], isLoading } = useStrategies();
  const createStrategy = useCreateStrategy();
  const updateStrategy = useUpdateStrategy();
  const deleteStrategy = useDeleteStrategy();

  const [modalOpen, setModalOpen] = useState(false);
  const [editingStrategy, setEditingStrategy] = useState<AnalysisStrategy | null>(null);

  const openCreate = useCallback(() => {
    setEditingStrategy(null);
    setModalOpen(true);
  }, []);

  const handleSubmit = useCallback(
    async (values: AnalysisStrategyCreate) => {
      try {
        if (editingStrategy) {
          await updateStrategy.mutateAsync({ id: editingStrategy.id, data: values });
        } else {
          await createStrategy.mutateAsync(values);
        }
        setModalOpen(false);
      } catch {
        message.error(t("common.saveFailed"));
      }
    },
    [editingStrategy, createStrategy, updateStrategy, t]
  );

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await deleteStrategy.mutateAsync(id);
      } catch {
        message.error(t("common.deleteFailed"));
      }
    },
    [deleteStrategy, t]
  );

  const handleToggle = useCallback(
    async (s: AnalysisStrategy, is_active: boolean) => {
      await updateStrategy.mutateAsync({ id: s.id, data: { is_active } });
    },
    [updateStrategy]
  );

  const columns: ColumnsType<AnalysisStrategy> = [
    {
      title: t("config.strategies.columns.name"),
      dataIndex: "name",
      key: "name",
      ellipsis: true,
    },
    {
      title: t("config.strategies.columns.type"),
      dataIndex: "strategy_type",
      key: "strategy_type",
      width: 120,
      render: (type: string) => (
        <Tag color={STRATEGY_TYPE_COLORS[type] ?? "default"}>
          {t(`config.strategies.type.${type}`)}
        </Tag>
      ),
    },
    {
      title: t("config.strategies.columns.provider"),
      dataIndex: "llm_provider",
      key: "llm_provider",
      width: 110,
    },
    {
      title: t("config.strategies.columns.model"),
      dataIndex: "llm_model",
      key: "llm_model",
      width: 150,
      ellipsis: true,
    },
    {
      title: t("config.strategies.columns.maxConcurrent"),
      dataIndex: "max_concurrent",
      key: "max_concurrent",
      width: 100,
      align: "right",
    },
    {
      title: t("config.strategies.columns.dailyBudget"),
      dataIndex: "daily_budget",
      key: "daily_budget",
      width: 110,
      align: "right",
      render: (v: number) => `$${v.toFixed(2)}`,
    },
    {
      title: t("config.strategies.columns.status"),
      key: "status",
      width: 90,
      align: "center",
      render: (_, s) => (
        <Switch
          checked={s.is_active}
          onChange={(checked) => handleToggle(s, checked)}
        />
      ),
    },
    {
      title: t("config.strategies.columns.actions"),
      key: "actions",
      width: 100,
      render: (_, s) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            size="small"
            onClick={() => {
              setEditingStrategy(s);
              setModalOpen(true);
            }}
          />
          <Popconfirm
            title={t("config.strategies.deleteConfirm", { name: s.name })}
            onConfirm={() => handleDelete(s.id)}
          >
            <Button type="link" danger icon={<DeleteOutlined />} size="small" />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card
      title={t("config.strategies.title")}
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          {t("config.strategies.create")}
        </Button>
      }
    >
      <Table<AnalysisStrategy>
        columns={columns}
        dataSource={strategies}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={{ pageSize: 10, hideOnSinglePage: true }}
      />
      <StrategyFormModal
        open={modalOpen}
        strategy={editingStrategy}
        onSubmit={handleSubmit}
        onCancel={() => setModalOpen(false)}
        loading={createStrategy.isPending || updateStrategy.isPending}
      />
    </Card>
  );
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && npx jest src/pages/Config/components/StrategyFormModal.test.tsx src/pages/Config/components/StrategiesPanel.test.tsx --no-cache`
Expected: PASS (5 tests total)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Config/components/StrategyFormModal.tsx \
        frontend/src/pages/Config/components/StrategyFormModal.test.tsx \
        frontend/src/pages/Config/components/StrategiesPanel.tsx \
        frontend/src/pages/Config/components/StrategiesPanel.test.tsx
git commit -m "feat: add StrategiesPanel with CRUD and StrategyFormModal"
```

---

### Task 7: TemplateFormModal + TemplatesPanel

**Files:**
- Create: `frontend/src/pages/Config/components/TemplateFormModal.tsx`
- Create: `frontend/src/pages/Config/components/TemplateFormModal.test.tsx`
- Create: `frontend/src/pages/Config/components/TemplatesPanel.tsx`
- Create: `frontend/src/pages/Config/components/TemplatesPanel.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/pages/Config/components/TemplateFormModal.test.tsx`:

```typescript
import { render, screen, fireEvent } from "@testing-library/react";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "config.templates.create": "新建模板",
        "config.templates.edit": "编辑模板",
        "config.templates.form.name": "模板名称",
        "config.templates.form.benchmark": "绑定 Benchmark（空=通用）",
        "config.templates.form.template": "模板内容",
        "config.templates.form.isActive": "启用",
        "common.save": "保存",
        "common.cancel": "取消",
      };
      return map[key] ?? key;
    },
  }),
}));

import TemplateFormModal from "./TemplateFormModal";

describe("TemplateFormModal", () => {
  it("renders create title when no template provided", () => {
    render(
      <TemplateFormModal
        open={true}
        template={null}
        onSubmit={jest.fn()}
        onCancel={jest.fn()}
        loading={false}
      />
    );
    expect(screen.getByText("新建模板")).toBeInTheDocument();
  });

  it("renders edit title when template is provided", () => {
    render(
      <TemplateFormModal
        open={true}
        template={{
          id: "t1",
          name: "GeneralTemplate",
          benchmark: null,
          template: "Analyze: {question}",
          version: 1,
          is_active: true,
          created_by: "admin",
          created_at: "2026-01-01T00:00:00Z",
        }}
        onSubmit={jest.fn()}
        onCancel={jest.fn()}
        loading={false}
      />
    );
    expect(screen.getByText("编辑模板")).toBeInTheDocument();
  });

  it("calls onCancel when cancel button clicked", () => {
    const onCancel = jest.fn();
    render(
      <TemplateFormModal
        open={true}
        template={null}
        onSubmit={jest.fn()}
        onCancel={onCancel}
        loading={false}
      />
    );
    fireEvent.click(screen.getByText("取消"));
    expect(onCancel).toHaveBeenCalled();
  });
});
```

Create `frontend/src/pages/Config/components/TemplatesPanel.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode } from "react";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "config.templates.title": "Prompt 模板",
        "config.templates.create": "新建模板",
        "config.templates.columns.name": "模板名称",
        "config.templates.columns.benchmark": "绑定 Benchmark",
        "config.templates.columns.version": "版本",
        "config.templates.columns.status": "状态",
        "config.templates.columns.actions": "操作",
        "config.templates.generic": "通用",
        "common.save": "保存",
        "common.cancel": "取消",
      };
      return map[key] ?? key;
    },
  }),
}));

jest.mock("../../../api/queries/config", () => ({
  useTemplates: jest.fn(),
  useCreateTemplate: jest.fn(),
  useUpdateTemplate: jest.fn(),
  useDeleteTemplate: jest.fn(),
}));

import TemplatesPanel from "./TemplatesPanel";
import {
  useTemplates,
  useCreateTemplate,
  useUpdateTemplate,
  useDeleteTemplate,
} from "../../../api/queries/config";

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("TemplatesPanel", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useTemplates as jest.Mock).mockReturnValue({
      data: [
        {
          id: "t1",
          name: "GeneralTemplate",
          benchmark: null,
          template: "Analyze: {question}",
          version: 2,
          is_active: true,
          created_by: "admin",
          created_at: "2026-01-01T00:00:00Z",
        },
      ],
      isLoading: false,
    });
    (useCreateTemplate as jest.Mock).mockReturnValue({ mutateAsync: jest.fn(), isPending: false });
    (useUpdateTemplate as jest.Mock).mockReturnValue({ mutateAsync: jest.fn(), isPending: false });
    (useDeleteTemplate as jest.Mock).mockReturnValue({ mutateAsync: jest.fn(), isPending: false });
  });

  it("renders panel title and template row", () => {
    render(<TemplatesPanel />, { wrapper: createWrapper() });
    expect(screen.getByText("Prompt 模板")).toBeInTheDocument();
    expect(screen.getByText("GeneralTemplate")).toBeInTheDocument();
  });

  it("shows generic label for null benchmark", () => {
    render(<TemplatesPanel />, { wrapper: createWrapper() });
    expect(screen.getByText("通用")).toBeInTheDocument();
  });

  it("shows version number", () => {
    render(<TemplatesPanel />, { wrapper: createWrapper() });
    expect(screen.getByText("2")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx jest src/pages/Config/components/TemplateFormModal.test.tsx src/pages/Config/components/TemplatesPanel.test.tsx --no-cache`
Expected: FAIL — modules not found

- [ ] **Step 3: Implement TemplateFormModal**

Create `frontend/src/pages/Config/components/TemplateFormModal.tsx`:

```typescript
import { useEffect } from "react";
import { Modal, Form, Input, Switch } from "antd";
import { useTranslation } from "react-i18next";
import type { PromptTemplate, PromptTemplateCreate } from "../../../types/api";

interface TemplateFormModalProps {
  open: boolean;
  template: PromptTemplate | null;
  onSubmit: (values: PromptTemplateCreate) => void;
  onCancel: () => void;
  loading: boolean;
}

export default function TemplateFormModal({
  open,
  template,
  onSubmit,
  onCancel,
  loading,
}: TemplateFormModalProps) {
  const { t } = useTranslation();
  const [form] = Form.useForm<PromptTemplateCreate>();

  useEffect(() => {
    if (open) {
      if (template) {
        form.setFieldsValue({
          name: template.name,
          benchmark: template.benchmark ?? undefined,
          template: template.template,
          is_active: template.is_active,
        });
      } else {
        form.resetFields();
        form.setFieldsValue({ is_active: true });
      }
    }
  }, [open, template, form]);

  const title = template
    ? t("config.templates.edit")
    : t("config.templates.create");

  return (
    <Modal
      title={title}
      open={open}
      onOk={() => form.validateFields().then(onSubmit)}
      onCancel={onCancel}
      okText={t("common.save")}
      cancelText={t("common.cancel")}
      confirmLoading={loading}
      width={680}
      destroyOnClose
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="name"
          label={t("config.templates.form.name")}
          rules={[{ required: true }]}
        >
          <Input />
        </Form.Item>

        <Form.Item
          name="benchmark"
          label={t("config.templates.form.benchmark")}
        >
          <Input allowClear placeholder="mmlu, gsm8k, …" />
        </Form.Item>

        <Form.Item
          name="template"
          label={t("config.templates.form.template")}
          extra={t("config.templates.form.templateHelp")}
          rules={[{ required: true }]}
        >
          <Input.TextArea rows={10} style={{ fontFamily: "monospace" }} />
        </Form.Item>

        <Form.Item
          name="is_active"
          label={t("config.templates.form.isActive")}
          valuePropName="checked"
        >
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  );
}
```

- [ ] **Step 4: Implement TemplatesPanel**

Create `frontend/src/pages/Config/components/TemplatesPanel.tsx`:

```typescript
import { useState, useCallback } from "react";
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Popconfirm,
  Switch,
  message,
} from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import type { ColumnsType } from "antd/es/table";
import {
  useTemplates,
  useCreateTemplate,
  useUpdateTemplate,
  useDeleteTemplate,
} from "../../../api/queries/config";
import TemplateFormModal from "./TemplateFormModal";
import type { PromptTemplate, PromptTemplateCreate } from "../../../types/api";

export default function TemplatesPanel() {
  const { t } = useTranslation();
  const { data: templates = [], isLoading } = useTemplates();
  const createTemplate = useCreateTemplate();
  const updateTemplate = useUpdateTemplate();
  const deleteTemplate = useDeleteTemplate();

  const [modalOpen, setModalOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<PromptTemplate | null>(null);

  const handleSubmit = useCallback(
    async (values: PromptTemplateCreate) => {
      try {
        if (editingTemplate) {
          await updateTemplate.mutateAsync({ id: editingTemplate.id, data: values });
        } else {
          await createTemplate.mutateAsync(values);
        }
        setModalOpen(false);
      } catch {
        message.error(t("common.saveFailed"));
      }
    },
    [editingTemplate, createTemplate, updateTemplate, t]
  );

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await deleteTemplate.mutateAsync(id);
      } catch {
        message.error(t("common.deleteFailed"));
      }
    },
    [deleteTemplate, t]
  );

  const columns: ColumnsType<PromptTemplate> = [
    {
      title: t("config.templates.columns.name"),
      dataIndex: "name",
      key: "name",
      ellipsis: true,
    },
    {
      title: t("config.templates.columns.benchmark"),
      dataIndex: "benchmark",
      key: "benchmark",
      width: 140,
      render: (b: string | null) =>
        b ? <Tag>{b}</Tag> : <Tag color="default">{t("config.templates.generic")}</Tag>,
    },
    {
      title: t("config.templates.columns.version"),
      dataIndex: "version",
      key: "version",
      width: 80,
      align: "right",
    },
    {
      title: t("config.templates.columns.status"),
      key: "status",
      width: 90,
      align: "center",
      render: (_, tpl) => (
        <Switch
          checked={tpl.is_active}
          onChange={(checked) =>
            updateTemplate.mutateAsync({ id: tpl.id, data: { is_active: checked } })
          }
        />
      ),
    },
    {
      title: t("config.templates.columns.actions"),
      key: "actions",
      width: 100,
      render: (_, tpl) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            size="small"
            onClick={() => {
              setEditingTemplate(tpl);
              setModalOpen(true);
            }}
          />
          <Popconfirm
            title={t("config.templates.deleteConfirm", { name: tpl.name })}
            onConfirm={() => handleDelete(tpl.id)}
          >
            <Button type="link" danger icon={<DeleteOutlined />} size="small" />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card
      title={t("config.templates.title")}
      extra={
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => {
            setEditingTemplate(null);
            setModalOpen(true);
          }}
        >
          {t("config.templates.create")}
        </Button>
      }
    >
      <Table<PromptTemplate>
        columns={columns}
        dataSource={templates}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={{ pageSize: 10, hideOnSinglePage: true }}
      />
      <TemplateFormModal
        open={modalOpen}
        template={editingTemplate}
        onSubmit={handleSubmit}
        onCancel={() => setModalOpen(false)}
        loading={createTemplate.isPending || updateTemplate.isPending}
      />
    </Card>
  );
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && npx jest src/pages/Config/components/TemplateFormModal.test.tsx src/pages/Config/components/TemplatesPanel.test.tsx --no-cache`
Expected: PASS (6 tests total)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Config/components/TemplateFormModal.tsx \
        frontend/src/pages/Config/components/TemplateFormModal.test.tsx \
        frontend/src/pages/Config/components/TemplatesPanel.tsx \
        frontend/src/pages/Config/components/TemplatesPanel.test.tsx
git commit -m "feat: add TemplatesPanel with CRUD and TemplateFormModal"
```

---

### Task 8: AdaptersPanel Component

**Files:**
- Create: `frontend/src/pages/Config/components/AdaptersPanel.tsx`
- Create: `frontend/src/pages/Config/components/AdaptersPanel.test.tsx`

This panel is read-only. Adapters are discovered and registered on the backend. The panel shows each adapter's name, description, detected fields, and whether it is built-in or custom.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/Config/components/AdaptersPanel.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode } from "react";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "config.adapters.title": "Benchmark Adapter",
        "config.adapters.description": "Adapter 由后端代码注册，此处仅查看。",
        "config.adapters.columns.name": "名称",
        "config.adapters.columns.description": "描述",
        "config.adapters.columns.fields": "检测字段",
        "config.adapters.columns.builtin": "类型",
        "config.adapters.builtin": "内置",
        "config.adapters.custom": "自定义",
      };
      return map[key] ?? key;
    },
  }),
}));

jest.mock("../../../api/queries/config", () => ({
  useAdapters: jest.fn(),
}));

import AdaptersPanel from "./AdaptersPanel";
import { useAdapters } from "../../../api/queries/config";

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("AdaptersPanel", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useAdapters as jest.Mock).mockReturnValue({
      data: [
        {
          name: "mmlu",
          description: "Massive Multitask Language Understanding",
          detected_fields: ["subject", "choices"],
          is_builtin: true,
        },
        {
          name: "custom_bench",
          description: "A custom benchmark adapter",
          detected_fields: ["input", "output"],
          is_builtin: false,
        },
      ],
      isLoading: false,
    });
  });

  it("renders panel title and read-only description", () => {
    render(<AdaptersPanel />, { wrapper: createWrapper() });
    expect(screen.getByText("Benchmark Adapter")).toBeInTheDocument();
    expect(
      screen.getByText("Adapter 由后端代码注册，此处仅查看。")
    ).toBeInTheDocument();
  });

  it("renders adapter rows with names", () => {
    render(<AdaptersPanel />, { wrapper: createWrapper() });
    expect(screen.getByText("mmlu")).toBeInTheDocument();
    expect(screen.getByText("custom_bench")).toBeInTheDocument();
  });

  it("shows builtin/custom labels correctly", () => {
    render(<AdaptersPanel />, { wrapper: createWrapper() });
    expect(screen.getByText("内置")).toBeInTheDocument();
    expect(screen.getByText("自定义")).toBeInTheDocument();
  });

  it("renders detected fields as tags", () => {
    render(<AdaptersPanel />, { wrapper: createWrapper() });
    expect(screen.getByText("subject")).toBeInTheDocument();
    expect(screen.getByText("choices")).toBeInTheDocument();
    expect(screen.getByText("input")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/pages/Config/components/AdaptersPanel.test.tsx --no-cache`
Expected: FAIL — module `./AdaptersPanel` not found

- [ ] **Step 3: Implement AdaptersPanel**

Create `frontend/src/pages/Config/components/AdaptersPanel.tsx`:

```typescript
import { Card, Table, Tag, Space, Typography } from "antd";
import { useTranslation } from "react-i18next";
import type { ColumnsType } from "antd/es/table";
import { useAdapters } from "../../../api/queries/config";
import type { BenchmarkAdapter } from "../../../types/api";

const { Text } = Typography;

export default function AdaptersPanel() {
  const { t } = useTranslation();
  const { data: adapters = [], isLoading } = useAdapters();

  const columns: ColumnsType<BenchmarkAdapter> = [
    {
      title: t("config.adapters.columns.name"),
      dataIndex: "name",
      key: "name",
      width: 160,
      render: (name: string) => <Text strong>{name}</Text>,
    },
    {
      title: t("config.adapters.columns.description"),
      dataIndex: "description",
      key: "description",
      ellipsis: true,
    },
    {
      title: t("config.adapters.columns.fields"),
      dataIndex: "detected_fields",
      key: "detected_fields",
      render: (fields: string[]) => (
        <Space size={[4, 4]} wrap>
          {fields.map((f) => (
            <Tag key={f} color="geekblue">
              {f}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: t("config.adapters.columns.builtin"),
      dataIndex: "is_builtin",
      key: "is_builtin",
      width: 100,
      align: "center",
      render: (isBuiltin: boolean) =>
        isBuiltin ? (
          <Tag color="green">{t("config.adapters.builtin")}</Tag>
        ) : (
          <Tag color="orange">{t("config.adapters.custom")}</Tag>
        ),
    },
  ];

  return (
    <Card
      title={t("config.adapters.title")}
      extra={
        <Text type="secondary">{t("config.adapters.description")}</Text>
      }
    >
      <Table<BenchmarkAdapter>
        columns={columns}
        dataSource={adapters}
        rowKey="name"
        loading={isLoading}
        size="small"
        pagination={false}
      />
    </Card>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx jest src/pages/Config/components/AdaptersPanel.test.tsx --no-cache`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Config/components/AdaptersPanel.tsx \
        frontend/src/pages/Config/components/AdaptersPanel.test.tsx
git commit -m "feat: add read-only AdaptersPanel"
```

---

### Task 9: Config Page Assembly

**Files:**
- Create: `frontend/src/pages/Config/index.tsx`
- Create: `frontend/src/pages/Config/Config.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/Config/Config.test.tsx`:

```typescript
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { type ReactNode } from "react";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "config.title": "分析配置",
        "config.tabs.rules": "规则管理",
        "config.tabs.strategies": "LLM 策略",
        "config.tabs.templates": "Prompt 模板",
        "config.tabs.adapters": "Benchmark Adapter",
      };
      return map[key] ?? key;
    },
  }),
}));

// Stub all four panels to keep test focused on the page skeleton
jest.mock("./components/RulesPanel", () => ({
  __esModule: true,
  default: () => <div data-testid="rules-panel" />,
}));
jest.mock("./components/StrategiesPanel", () => ({
  __esModule: true,
  default: () => <div data-testid="strategies-panel" />,
}));
jest.mock("./components/TemplatesPanel", () => ({
  __esModule: true,
  default: () => <div data-testid="templates-panel" />,
}));
jest.mock("./components/AdaptersPanel", () => ({
  __esModule: true,
  default: () => <div data-testid="adapters-panel" />,
}));

import Config from "./index";

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </MemoryRouter>
  );
};

describe("Config Page", () => {
  it("renders page title", () => {
    render(<Config />, { wrapper: createWrapper() });
    expect(screen.getByText("分析配置")).toBeInTheDocument();
  });

  it("renders all four tab labels", () => {
    render(<Config />, { wrapper: createWrapper() });
    expect(screen.getByText("规则管理")).toBeInTheDocument();
    expect(screen.getByText("LLM 策略")).toBeInTheDocument();
    expect(screen.getByText("Prompt 模板")).toBeInTheDocument();
    expect(screen.getByText("Benchmark Adapter")).toBeInTheDocument();
  });

  it("shows rules panel by default (first tab)", () => {
    render(<Config />, { wrapper: createWrapper() });
    expect(screen.getByTestId("rules-panel")).toBeInTheDocument();
  });

  it("switches to strategies panel when tab is clicked", () => {
    render(<Config />, { wrapper: createWrapper() });
    fireEvent.click(screen.getByText("LLM 策略"));
    expect(screen.getByTestId("strategies-panel")).toBeInTheDocument();
  });

  it("switches to templates panel when tab is clicked", () => {
    render(<Config />, { wrapper: createWrapper() });
    fireEvent.click(screen.getByText("Prompt 模板"));
    expect(screen.getByTestId("templates-panel")).toBeInTheDocument();
  });

  it("switches to adapters panel when tab is clicked", () => {
    render(<Config />, { wrapper: createWrapper() });
    fireEvent.click(screen.getByText("Benchmark Adapter"));
    expect(screen.getByTestId("adapters-panel")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/pages/Config/Config.test.tsx --no-cache`
Expected: FAIL — module `./index` not found

- [ ] **Step 3: Implement the Config page**

Create `frontend/src/pages/Config/index.tsx`:

```typescript
import { Typography, Tabs } from "antd";
import { useTranslation } from "react-i18next";
import RulesPanel from "./components/RulesPanel";
import StrategiesPanel from "./components/StrategiesPanel";
import TemplatesPanel from "./components/TemplatesPanel";
import AdaptersPanel from "./components/AdaptersPanel";
import UsersPanel from "./components/UsersPanel";
import { useAuth } from "../../contexts/AuthContext";

const { Title } = Typography;

export default function Config() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const items = [
    {
      key: "rules",
      label: t("config.tabs.rules"),
      children: <RulesPanel />,
    },
    {
      key: "strategies",
      label: t("config.tabs.strategies"),
      children: <StrategiesPanel />,
    },
    {
      key: "templates",
      label: t("config.tabs.templates"),
      children: <TemplatesPanel />,
    },
    {
      key: "adapters",
      label: t("config.tabs.adapters"),
      children: <AdaptersPanel />,
    },
    // Users tab — only visible to Admin (design doc §11)
    ...(isAdmin
      ? [
          {
            key: "users",
            label: t("config.tabs.users"),
            children: <UsersPanel />,
          },
        ]
      : []),
  ];

  return (
    <>
      <Title level={4} style={{ marginBottom: 16 }}>
        {t("config.title")}
      </Title>
      <Tabs defaultActiveKey="rules" items={items} destroyInactiveTabPane />
    </>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx jest src/pages/Config/Config.test.tsx --no-cache`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Config/index.tsx \
        frontend/src/pages/Config/Config.test.tsx
git commit -m "feat: implement Config page with five-tab layout (includes Admin-only Users tab)"
```

---

### Task 10: Update Router — Wire /config Route

**Files:**
- Modify: `frontend/src/router.tsx`

- [ ] **Step 1: Add lazy import and replace PlaceholderPage**

```typescript
// Add alongside other lazy imports:
const Config = lazy(() => import("./pages/Config"));

// Replace:
{ path: "config", element: <PlaceholderPage /> },

// With:
{
  path: "config",
  element: (
    <Suspense fallback={<LazyFallback />}>
      <Config />
    </Suspense>
  ),
},
```

- [ ] **Step 2: Run all tests**

Run: `cd frontend && npx jest --no-cache`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add frontend/src/router.tsx
git commit -m "feat: wire Config page into router — all PlaceholderPage routes replaced"
```

---

### Task 11: Integration Smoke Test

**Files:**
- Create: `frontend/src/pages/Config/Config.integration.test.tsx`

- [ ] **Step 1: Write the integration test**

Create `frontend/src/pages/Config/Config.integration.test.tsx`:

```typescript
/**
 * Integration test: renders Config page with all panels un-mocked.
 * API calls are mocked at the hook level.
 */
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { type ReactNode } from "react";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

jest.mock("../../api/queries/config", () => ({
  useRules: () => ({ data: [], isLoading: false }),
  useCreateRule: () => ({ mutateAsync: jest.fn(), isPending: false }),
  useUpdateRule: () => ({ mutateAsync: jest.fn(), isPending: false }),
  useDeleteRule: () => ({ mutateAsync: jest.fn(), isPending: false }),
  useStrategies: () => ({ data: [], isLoading: false }),
  useCreateStrategy: () => ({ mutateAsync: jest.fn(), isPending: false }),
  useUpdateStrategy: () => ({ mutateAsync: jest.fn(), isPending: false }),
  useDeleteStrategy: () => ({ mutateAsync: jest.fn(), isPending: false }),
  useTemplates: () => ({ data: [], isLoading: false }),
  useCreateTemplate: () => ({ mutateAsync: jest.fn(), isPending: false }),
  useUpdateTemplate: () => ({ mutateAsync: jest.fn(), isPending: false }),
  useDeleteTemplate: () => ({ mutateAsync: jest.fn(), isPending: false }),
  useAdapters: () => ({ data: [], isLoading: false }),
}));

import Config from "./index";

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </MemoryRouter>
  );
};

describe("Config Page (integration)", () => {
  it("renders without crashing and shows title and tab labels", () => {
    render(<Config />, { wrapper: createWrapper() });
    expect(screen.getByText("config.title")).toBeInTheDocument();
    expect(screen.getByText("config.tabs.rules")).toBeInTheDocument();
    expect(screen.getByText("config.tabs.strategies")).toBeInTheDocument();
    expect(screen.getByText("config.tabs.templates")).toBeInTheDocument();
    expect(screen.getByText("config.tabs.adapters")).toBeInTheDocument();
  });

  it("renders rules panel card title in default tab", () => {
    render(<Config />, { wrapper: createWrapper() });
    expect(screen.getByText("config.rules.title")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run integration test**

Run: `cd frontend && npx jest src/pages/Config/Config.integration.test.tsx --no-cache`
Expected: PASS (2 tests)

- [ ] **Step 3: Run full suite**

Run: `cd frontend && npx jest --no-cache`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Config/Config.integration.test.tsx
git commit -m "test: add integration smoke test for Config page"
```

---

### Task 12: User Management Query Hooks

**Files:**
- Modify: `frontend/src/api/queries/config.ts`
- Modify: `frontend/src/api/queries/config.test.ts`

- [ ] **Step 1: Add user CRUD hooks to `config.ts`**

Append to `frontend/src/api/queries/config.ts`:

```typescript
// ─── User Management (Admin only) ───────────────────────────────────────────

const USERS_KEY = ["users"] as const;

export function useUsers() {
  return useQuery({
    queryKey: USERS_KEY,
    queryFn: () => apiClient.get<UserInfo[]>("/users").then((r) => r.data),
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: UserCreate) =>
      apiClient.post<UserInfo>("/users", data).then((r) => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_KEY }),
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: UserUpdate & { id: string }) =>
      apiClient.patch<UserInfo>(`/users/${id}`, data).then((r) => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_KEY }),
  });
}
```

- [ ] **Step 2: Add tests to `config.test.ts`**

Append to `frontend/src/api/queries/config.test.ts`:

```typescript
describe("useUsers", () => {
  it("fetches user list from /users", async () => {
    mockAxios.onGet("/users").reply(200, [
      { id: "1", username: "admin", email: "a@b.com", role: "admin", is_active: true },
    ]);
    const { result } = renderHook(() => useUsers(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
  });
});

describe("useCreateUser", () => {
  it("posts to /users and invalidates cache", async () => {
    mockAxios.onPost("/users").reply(201, {
      id: "2", username: "new", email: "n@b.com", role: "analyst", is_active: true,
    });
    const { result } = renderHook(() => useCreateUser(), { wrapper: createWrapper() });
    await act(async () => {
      await result.current.mutateAsync({
        username: "new", email: "n@b.com", password: "pass", role: "analyst",
      });
    });
    expect(result.current.isSuccess).toBe(true);
  });
});

describe("useUpdateUser", () => {
  it("patches /users/:id and invalidates cache", async () => {
    mockAxios.onPatch("/users/u1").reply(200, {
      id: "u1", username: "x", email: "x@b.com", role: "viewer", is_active: true,
    });
    const { result } = renderHook(() => useUpdateUser(), { wrapper: createWrapper() });
    await act(async () => {
      await result.current.mutateAsync({ id: "u1", role: "viewer" });
    });
    expect(result.current.isSuccess).toBe(true);
  });
});
```

- [ ] **Step 3: Run tests**

Run: `cd frontend && npx jest src/api/queries/config.test.ts --no-cache`
Expected: All tests PASS (previous 14 + 3 new = 17 tests)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/queries/config.ts frontend/src/api/queries/config.test.ts
git commit -m "feat: add user management query hooks (useUsers, useCreateUser, useUpdateUser)"
```

---

### Task 13: UserFormModal Component

**Files:**
- Create: `frontend/src/pages/Config/components/UserFormModal.tsx`
- Create: `frontend/src/pages/Config/components/UserFormModal.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/Config/components/UserFormModal.test.tsx`:

```typescript
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import UserFormModal from "./UserFormModal";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

describe("UserFormModal", () => {
  const onSubmit = jest.fn().mockResolvedValue(undefined);
  const onCancel = jest.fn();

  it("renders create form when no initialValues", () => {
    render(<UserFormModal open onSubmit={onSubmit} onCancel={onCancel} />);
    expect(screen.getByText("config.users.create")).toBeInTheDocument();
    // Password field should be required in create mode
    expect(screen.getByLabelText("config.users.form.password")).toBeRequired();
  });

  it("renders edit form with initial values", () => {
    render(
      <UserFormModal
        open
        onSubmit={onSubmit}
        onCancel={onCancel}
        initialValues={{ id: "1", username: "test", email: "t@b.com", role: "analyst" }}
      />
    );
    expect(screen.getByText("config.users.edit")).toBeInTheDocument();
    expect(screen.getByDisplayValue("test")).toBeInTheDocument();
  });

  it("shows role selector with three options", () => {
    render(<UserFormModal open onSubmit={onSubmit} onCancel={onCancel} />);
    fireEvent.mouseDown(screen.getByLabelText("config.users.form.role"));
    expect(screen.getByText("config.users.role.admin")).toBeInTheDocument();
    expect(screen.getByText("config.users.role.analyst")).toBeInTheDocument();
    expect(screen.getByText("config.users.role.viewer")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Implement UserFormModal**

Create `frontend/src/pages/Config/components/UserFormModal.tsx`:

```typescript
import { Modal, Form, Input, Select } from "antd";
import { useTranslation } from "react-i18next";
import { useEffect } from "react";
import type { UserCreate, UserUpdate, UserRole } from "../../../types/api";

interface UserFormModalProps {
  open: boolean;
  onSubmit: (values: UserCreate | (UserUpdate & { id: string })) => Promise<void>;
  onCancel: () => void;
  initialValues?: { id: string; username: string; email: string; role: UserRole };
  loading?: boolean;
}

const ROLES: UserRole[] = ["admin", "analyst", "viewer"];

export default function UserFormModal({
  open,
  onSubmit,
  onCancel,
  initialValues,
  loading = false,
}: UserFormModalProps) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const isEdit = !!initialValues;

  useEffect(() => {
    if (open && initialValues) {
      form.setFieldsValue(initialValues);
    } else if (open) {
      form.resetFields();
    }
  }, [open, initialValues, form]);

  const handleOk = async () => {
    const values = await form.validateFields();
    if (isEdit) {
      // Remove empty password field in edit mode
      if (!values.password) delete values.password;
      await onSubmit({ ...values, id: initialValues!.id });
    } else {
      await onSubmit(values);
    }
    form.resetFields();
  };

  return (
    <Modal
      open={open}
      title={isEdit ? t("config.users.edit") : t("config.users.create")}
      onOk={handleOk}
      onCancel={onCancel}
      confirmLoading={loading}
      destroyOnClose
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="username"
          label={t("config.users.form.username")}
          rules={[{ required: true }]}
        >
          <Input disabled={isEdit} />
        </Form.Item>
        <Form.Item
          name="email"
          label={t("config.users.form.email")}
          rules={[{ required: true, type: "email" }]}
        >
          <Input />
        </Form.Item>
        <Form.Item
          name="password"
          label={t("config.users.form.password")}
          rules={isEdit ? [] : [{ required: true, min: 8 }]}
          extra={isEdit ? t("config.users.form.passwordHelp") : undefined}
        >
          <Input.Password />
        </Form.Item>
        <Form.Item
          name="role"
          label={t("config.users.form.role")}
          rules={[{ required: true }]}
          initialValue="analyst"
        >
          <Select>
            {ROLES.map((r) => (
              <Select.Option key={r} value={r}>
                {t(`config.users.role.${r}`)}
              </Select.Option>
            ))}
          </Select>
        </Form.Item>
      </Form>
    </Modal>
  );
}
```

- [ ] **Step 3: Run tests**

Run: `cd frontend && npx jest src/pages/Config/components/UserFormModal.test.tsx --no-cache`
Expected: PASS (3 tests)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Config/components/UserFormModal.tsx \
        frontend/src/pages/Config/components/UserFormModal.test.tsx
git commit -m "feat: add UserFormModal component for create/edit user"
```

---

### Task 14: UsersPanel Component

**Files:**
- Create: `frontend/src/pages/Config/components/UsersPanel.tsx`
- Create: `frontend/src/pages/Config/components/UsersPanel.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/Config/components/UsersPanel.test.tsx`:

```typescript
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import UsersPanel from "./UsersPanel";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

const mockUsers = [
  { id: "1", username: "admin", email: "a@b.com", role: "admin", is_active: true, created_at: "2026-01-01", updated_at: "2026-01-01" },
  { id: "2", username: "analyst1", email: "an@b.com", role: "analyst", is_active: true, created_at: "2026-01-02", updated_at: "2026-01-02" },
  { id: "3", username: "viewer1", email: "v@b.com", role: "viewer", is_active: false, created_at: "2026-01-03", updated_at: "2026-01-03" },
];

const mockCreateUser = { mutateAsync: jest.fn(), isPending: false };
const mockUpdateUser = { mutateAsync: jest.fn(), isPending: false };

jest.mock("../../../api/queries/config", () => ({
  useUsers: () => ({ data: mockUsers, isLoading: false }),
  useCreateUser: () => mockCreateUser,
  useUpdateUser: () => mockUpdateUser,
}));

// Mock AuthContext to return admin user
jest.mock("../../../contexts/AuthContext", () => ({
  useAuth: () => ({ user: { id: "1", role: "admin" } }),
}));

describe("UsersPanel", () => {
  it("renders user table with all users", () => {
    render(<UsersPanel />);
    expect(screen.getByText("admin")).toBeInTheDocument();
    expect(screen.getByText("analyst1")).toBeInTheDocument();
    expect(screen.getByText("viewer1")).toBeInTheDocument();
  });

  it("shows role badges for each user", () => {
    render(<UsersPanel />);
    expect(screen.getByText("config.users.role.admin")).toBeInTheDocument();
    expect(screen.getByText("config.users.role.analyst")).toBeInTheDocument();
    expect(screen.getByText("config.users.role.viewer")).toBeInTheDocument();
  });

  it("shows create button", () => {
    render(<UsersPanel />);
    expect(screen.getByText("config.users.create")).toBeInTheDocument();
  });

  it("shows active/inactive status", () => {
    render(<UsersPanel />);
    const activeBadges = screen.getAllByText("config.users.active");
    const inactiveBadges = screen.getAllByText("config.users.inactive");
    expect(activeBadges).toHaveLength(2);
    expect(inactiveBadges).toHaveLength(1);
  });
});
```

- [ ] **Step 2: Implement UsersPanel**

Create `frontend/src/pages/Config/components/UsersPanel.tsx`:

```typescript
import { useState } from "react";
import { Button, Card, Table, Tag, Space, Popconfirm, message } from "antd";
import { PlusOutlined, EditOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import type { ColumnsType } from "antd/es/table";
import { useUsers, useCreateUser, useUpdateUser } from "../../../api/queries/config";
import { useAuth } from "../../../contexts/AuthContext";
import UserFormModal from "./UserFormModal";
import type { UserInfo, UserCreate, UserUpdate } from "../../../types/api";

const ROLE_COLORS: Record<string, string> = {
  admin: "red",
  analyst: "blue",
  viewer: "default",
};

export default function UsersPanel() {
  const { t } = useTranslation();
  const { user: currentUser } = useAuth();
  const { data: users = [], isLoading } = useUsers();
  const createUser = useCreateUser();
  const updateUser = useUpdateUser();

  const [modalOpen, setModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<UserInfo | null>(null);

  const handleCreate = async (values: UserCreate) => {
    await createUser.mutateAsync(values);
    setModalOpen(false);
    message.success(t("common.success"));
  };

  const handleUpdate = async (values: UserUpdate & { id: string }) => {
    await updateUser.mutateAsync(values);
    setEditingUser(null);
    message.success(t("common.success"));
  };

  const handleToggleActive = async (record: UserInfo) => {
    if (record.id === currentUser?.id) {
      message.error(t("config.users.cannotDeactivateSelf"));
      return;
    }
    await updateUser.mutateAsync({
      id: record.id,
      is_active: !record.is_active,
    });
  };

  const columns: ColumnsType<UserInfo> = [
    {
      title: t("config.users.columns.username"),
      dataIndex: "username",
      key: "username",
    },
    {
      title: t("config.users.columns.email"),
      dataIndex: "email",
      key: "email",
    },
    {
      title: t("config.users.columns.role"),
      dataIndex: "role",
      key: "role",
      render: (role: string) => (
        <Tag color={ROLE_COLORS[role]}>{t(`config.users.role.${role}`)}</Tag>
      ),
    },
    {
      title: t("config.users.columns.status"),
      dataIndex: "is_active",
      key: "is_active",
      render: (active: boolean) => (
        <Tag color={active ? "green" : "default"}>
          {active ? t("config.users.active") : t("config.users.inactive")}
        </Tag>
      ),
    },
    {
      title: t("config.users.columns.createdAt"),
      dataIndex: "created_at",
      key: "created_at",
    },
    {
      title: t("config.users.columns.actions"),
      key: "actions",
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => setEditingUser(record)}
          />
          <Popconfirm
            title={
              record.is_active
                ? t("config.users.deactivateConfirm", { name: record.username })
                : undefined
            }
            onConfirm={() => handleToggleActive(record)}
            disabled={record.id === currentUser?.id}
          >
            <Button
              type="link"
              danger={record.is_active}
              disabled={record.id === currentUser?.id}
            >
              {record.is_active
                ? t("config.users.deactivate")
                : t("config.users.activate")}
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card
      title={t("config.users.title")}
      extra={
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setModalOpen(true)}
        >
          {t("config.users.create")}
        </Button>
      }
    >
      <Table<UserInfo>
        rowKey="id"
        columns={columns}
        dataSource={users}
        loading={isLoading}
        pagination={{ pageSize: 20 }}
      />

      {/* Create modal */}
      <UserFormModal
        open={modalOpen}
        onSubmit={handleCreate}
        onCancel={() => setModalOpen(false)}
        loading={createUser.isPending}
      />

      {/* Edit modal */}
      <UserFormModal
        open={!!editingUser}
        onSubmit={handleUpdate}
        onCancel={() => setEditingUser(null)}
        initialValues={
          editingUser
            ? {
                id: editingUser.id,
                username: editingUser.username,
                email: editingUser.email,
                role: editingUser.role,
              }
            : undefined
        }
        loading={updateUser.isPending}
      />
    </Card>
  );
}
```

- [ ] **Step 3: Run tests**

Run: `cd frontend && npx jest src/pages/Config/components/UsersPanel.test.tsx --no-cache`
Expected: PASS (4 tests)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Config/components/UsersPanel.tsx \
        frontend/src/pages/Config/components/UsersPanel.test.tsx
git commit -m "feat: add UsersPanel component — user CRUD table for Admin"
```

---

### Task 15: Wire Users Tab into Config Page

**Files:**
- Modify: `frontend/src/pages/Config/index.tsx`
- Modify: `frontend/src/pages/Config/Config.test.tsx`
- Modify: `frontend/src/pages/Config/Config.integration.test.tsx`

- [ ] **Step 1: Update Config page to include Users tab (Admin only)**

Modify `frontend/src/pages/Config/index.tsx`:

```typescript
import { Typography, Tabs } from "antd";
import { useTranslation } from "react-i18next";
import RulesPanel from "./components/RulesPanel";
import StrategiesPanel from "./components/StrategiesPanel";
import TemplatesPanel from "./components/TemplatesPanel";
import AdaptersPanel from "./components/AdaptersPanel";
import UsersPanel from "./components/UsersPanel";
import { useAuth } from "../../contexts/AuthContext";

const { Title } = Typography;

export default function Config() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const items = [
    {
      key: "rules",
      label: t("config.tabs.rules"),
      children: <RulesPanel />,
    },
    {
      key: "strategies",
      label: t("config.tabs.strategies"),
      children: <StrategiesPanel />,
    },
    {
      key: "templates",
      label: t("config.tabs.templates"),
      children: <TemplatesPanel />,
    },
    {
      key: "adapters",
      label: t("config.tabs.adapters"),
      children: <AdaptersPanel />,
    },
    // Users tab — only visible to Admin
    ...(isAdmin
      ? [
          {
            key: "users",
            label: t("config.tabs.users"),
            children: <UsersPanel />,
          },
        ]
      : []),
  ];

  return (
    <>
      <Title level={4} style={{ marginBottom: 16 }}>
        {t("config.title")}
      </Title>
      <Tabs defaultActiveKey="rules" items={items} destroyInactiveTabPane />
    </>
  );
}
```

- [ ] **Step 2: Update Config.test.tsx — add Users tab tests**

Append to `frontend/src/pages/Config/Config.test.tsx`:

```typescript
describe("Users tab visibility", () => {
  it("shows Users tab when user is admin", () => {
    // Mock useAuth to return admin
    jest.spyOn(require("../../contexts/AuthContext"), "useAuth")
      .mockReturnValue({ user: { id: "1", role: "admin" } });
    render(<Config />, { wrapper: createWrapper() });
    expect(screen.getByText("config.tabs.users")).toBeInTheDocument();
  });

  it("hides Users tab when user is analyst", () => {
    jest.spyOn(require("../../contexts/AuthContext"), "useAuth")
      .mockReturnValue({ user: { id: "2", role: "analyst" } });
    render(<Config />, { wrapper: createWrapper() });
    expect(screen.queryByText("config.tabs.users")).not.toBeInTheDocument();
  });

  it("hides Users tab when user is viewer", () => {
    jest.spyOn(require("../../contexts/AuthContext"), "useAuth")
      .mockReturnValue({ user: { id: "3", role: "viewer" } });
    render(<Config />, { wrapper: createWrapper() });
    expect(screen.queryByText("config.tabs.users")).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Update integration test mock to include user hooks**

Modify `frontend/src/pages/Config/Config.integration.test.tsx` mock:

```typescript
jest.mock("../../api/queries/config", () => ({
  // ... existing mocks ...
  useUsers: () => ({ data: [], isLoading: false }),
  useCreateUser: () => ({ mutateAsync: jest.fn(), isPending: false }),
  useUpdateUser: () => ({ mutateAsync: jest.fn(), isPending: false }),
}));

jest.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({ user: { id: "1", role: "admin" } }),
}));
```

Update the integration test assertions to include the Users tab:

```typescript
it("renders without crashing and shows title and tab labels", () => {
  render(<Config />, { wrapper: createWrapper() });
  expect(screen.getByText("config.title")).toBeInTheDocument();
  expect(screen.getByText("config.tabs.rules")).toBeInTheDocument();
  expect(screen.getByText("config.tabs.strategies")).toBeInTheDocument();
  expect(screen.getByText("config.tabs.templates")).toBeInTheDocument();
  expect(screen.getByText("config.tabs.adapters")).toBeInTheDocument();
  expect(screen.getByText("config.tabs.users")).toBeInTheDocument();
});
```

- [ ] **Step 4: Run all Config tests**

Run: `cd frontend && npx jest src/pages/Config/ --no-cache`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Config/index.tsx \
        frontend/src/pages/Config/Config.test.tsx \
        frontend/src/pages/Config/Config.integration.test.tsx
git commit -m "feat: add Users tab to Config page (Admin only, design doc §11)"
```

---

## Backend API Dependencies

This plan consumes these backend endpoints (from Plans 01, 03, 04):

| Endpoint | Method | Used By |
|----------|--------|---------|
| `GET /api/v1/rules` | GET | RulesPanel |
| `POST /api/v1/rules` | POST | RulesPanel create |
| `PUT /api/v1/rules/{id}` | PUT | RulesPanel edit/toggle |
| `DELETE /api/v1/rules/{id}` | DELETE | RulesPanel delete |
| `GET /api/v1/llm/strategies` | GET | StrategiesPanel |
| `POST /api/v1/llm/strategies` | POST | StrategiesPanel create |
| `PUT /api/v1/llm/strategies/{id}` | PUT | StrategiesPanel edit/toggle |
| `DELETE /api/v1/llm/strategies/{id}` | DELETE | StrategiesPanel delete |
| `GET /api/v1/llm/prompt-templates` | GET | TemplatesPanel + StrategyFormModal |
| `POST /api/v1/llm/prompt-templates` | POST | TemplatesPanel create |
| `PUT /api/v1/llm/prompt-templates/{id}` | PUT | TemplatesPanel edit/toggle |
| `DELETE /api/v1/llm/prompt-templates/{id}` | DELETE | TemplatesPanel delete |
| `GET /api/v1/ingest/adapters` | GET | AdaptersPanel (read-only) |
| `GET /api/v1/users` | GET | UsersPanel (Admin only) |
| `POST /api/v1/users` | POST | UsersPanel create (Admin only) |
| `PATCH /api/v1/users/{id}` | PATCH | UsersPanel edit/toggle (Admin only) |

## Summary of Changes

| File | Action |
|------|--------|
| `frontend/src/types/api.ts` | Add 10 new types / type aliases + UserInfo, UserCreate, UserUpdate, UserRole |
| `frontend/src/locales/zh.json` | Add 62 `config.*` keys + 28 `config.users.*` keys |
| `frontend/src/locales/en.json` | Add 62 `config.*` keys + 28 `config.users.*` keys |
| `frontend/src/api/queries/config.ts` | Create (13 hooks + 3 user hooks = 16 total) |
| `frontend/src/api/queries/config.test.ts` | Create (14 tests + 3 user tests = 17 total) |
| `frontend/src/pages/Config/components/RuleFormModal.tsx` | Create |
| `frontend/src/pages/Config/components/RuleFormModal.test.tsx` | Create (4 tests) |
| `frontend/src/pages/Config/components/RulesPanel.tsx` | Create |
| `frontend/src/pages/Config/components/RulesPanel.test.tsx` | Create (4 tests) |
| `frontend/src/pages/Config/components/StrategyFormModal.tsx` | Create |
| `frontend/src/pages/Config/components/StrategyFormModal.test.tsx` | Create (3 tests) |
| `frontend/src/pages/Config/components/StrategiesPanel.tsx` | Create |
| `frontend/src/pages/Config/components/StrategiesPanel.test.tsx` | Create (2 tests) |
| `frontend/src/pages/Config/components/TemplateFormModal.tsx` | Create |
| `frontend/src/pages/Config/components/TemplateFormModal.test.tsx` | Create (3 tests) |
| `frontend/src/pages/Config/components/TemplatesPanel.tsx` | Create |
| `frontend/src/pages/Config/components/TemplatesPanel.test.tsx` | Create (3 tests) |
| `frontend/src/pages/Config/components/AdaptersPanel.tsx` | Create |
| `frontend/src/pages/Config/components/AdaptersPanel.test.tsx` | Create (4 tests) |
| `frontend/src/pages/Config/components/UserFormModal.tsx` | Create |
| `frontend/src/pages/Config/components/UserFormModal.test.tsx` | Create (3 tests) |
| `frontend/src/pages/Config/components/UsersPanel.tsx` | Create |
| `frontend/src/pages/Config/components/UsersPanel.test.tsx` | Create (4 tests) |
| `frontend/src/pages/Config/index.tsx` | Create |
| `frontend/src/pages/Config/Config.test.tsx` | Create (6 tests + 3 user tab visibility tests = 9) |
| `frontend/src/pages/Config/Config.integration.test.tsx` | Create (2 tests, updated for Users tab) |
| `frontend/src/router.tsx` | Modify — wire real page; all `PlaceholderPage` routes now replaced |

**Total new tests: 59**

This is the final frontend plan. After Plan 10, all five Dashboard routes (`/overview`, `/analysis`, `/compare`, `/cross-benchmark`, `/config`) are implemented and no `PlaceholderPage` remains. The Config page includes a Users tab visible only to Admin role users, fulfilling design doc §11 (RBAC user management UI).
