# Error Analysis & Version Compare Pages — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Error Analysis page (three-level drill-down Treemap + paginated error list + record detail drawer) and the Version Compare page (dual version selector + radar chart + diff summary), replacing their PlaceholderPage routes from Plan 07.

**Architecture:** Both pages consume existing backend APIs from Plan 05 via new TanStack Query hooks. The Error Analysis page uses a Treemap for L1→L2→L3 drill-down, an Ant Design Table for paginated error records, and a Drawer for record detail view. The Version Compare page uses a dual Select for version picking, an ECharts radar chart for dimension comparison, and Ant Design Cards/Tables for the diff summary.

**Tech Stack:** React 18, TypeScript 5, Ant Design 5, ECharts 5 (via echarts-for-react), TanStack Query v5, React Router v6

---

## Prerequisites

This plan depends on Plan 07 (Frontend Foundation) being complete. The following are already available:

- **Types** (`frontend/src/types/api.ts`): `DistributionItem`, `ErrorRecordBrief`, `PaginatedRecords`, `RecordDetail`, `AnalysisResultDetail`, `VersionComparison`, `VersionMetrics`, `VersionDiff`, `DiffItem`, `RadarData`
- **Components**: `EChartsWrapper`, `StatCard`, `FilterBar`, `PlaceholderPage`
- **Hooks**: `useGlobalFilters()`, `useErrorDistribution()`
- **Contexts**: `FilterContext`, `AuthContext`
- **Layout**: `AppLayout` with sidebar nav and FilterBar
- **Router**: routes for `/analysis` and `/compare` (currently rendering `PlaceholderPage`)

## File Structure

```
frontend/src/
  api/queries/
    analysis.ts           # MODIFY — add useErrorRecords, useRecordDetail hooks
    compare.ts            # CREATE — useVersionComparison, useVersionDiff, useRadarData hooks
  pages/
    Analysis/
      index.tsx           # CREATE — Error Analysis page (orchestrates drill-down)
      Analysis.test.tsx   # CREATE — page-level tests
      components/
        ErrorTreemap.tsx   # CREATE — L1→L2→L3 drill-down Treemap chart
        ErrorTable.tsx     # CREATE — paginated error records table
        RecordDetail.tsx   # CREATE — record detail drawer
    Compare/
      index.tsx           # CREATE — Version Compare page
      Compare.test.tsx    # CREATE — page-level tests
      components/
        VersionSelector.tsx  # CREATE — dual version selector component
        RadarChart.tsx       # CREATE — radar chart for dimension comparison
        DiffSummary.tsx      # CREATE — regressed/improved/new/resolved tables
  locales/
    zh.json               # MODIFY — add analysis.* and compare.* keys
    en.json               # MODIFY — add analysis.* and compare.* keys
  router.tsx              # MODIFY — replace PlaceholderPage imports with lazy-loaded pages
```

---

### Task 1: Add i18n Translation Keys

**Files:**
- Modify: `frontend/src/locales/zh.json`
- Modify: `frontend/src/locales/en.json`

- [ ] **Step 1: Add Chinese translation keys**

Add the following keys to `frontend/src/locales/zh.json`:

```json
{
  "analysis.title": "错因分析",
  "analysis.treemapTitle": "错误类型分布",
  "analysis.backToL1": "返回 L1 总览",
  "analysis.backToL2": "返回 L2",
  "analysis.errorCount": "错题数",
  "analysis.percentage": "占比",
  "analysis.noErrors": "当前筛选条件下没有错题数据",
  "analysis.recordsTitle": "错题列表",
  "analysis.columns.questionId": "题目 ID",
  "analysis.columns.benchmark": "Benchmark",
  "analysis.columns.category": "任务类别",
  "analysis.columns.question": "题目",
  "analysis.columns.errorTags": "错因标签",
  "analysis.columns.hasLlm": "LLM 分析",
  "analysis.columns.actions": "操作",
  "analysis.viewDetail": "查看详情",
  "analysis.detail.title": "错题详情",
  "analysis.detail.question": "题目",
  "analysis.detail.expected": "标准答案",
  "analysis.detail.modelAnswer": "模型回答",
  "analysis.detail.errorTags": "错因标签",
  "analysis.detail.analysisResults": "分析结果",
  "analysis.detail.rootCause": "根因分析",
  "analysis.detail.severity": "严重程度",
  "analysis.detail.confidence": "置信度",
  "analysis.detail.evidence": "证据",
  "analysis.detail.suggestion": "改进建议",
  "analysis.detail.analysisType": "分析方式",
  "analysis.detail.llmModel": "使用模型",
  "analysis.detail.llmCost": "分析成本",
  "compare.title": "版本对比",
  "compare.selectVersionA": "选择版本 A",
  "compare.selectVersionB": "选择版本 B",
  "compare.compare": "对比",
  "compare.noVersions": "请先选择两个版本",
  "compare.radar.title": "能力雷达图",
  "compare.metrics.total": "总题数",
  "compare.metrics.errors": "错题数",
  "compare.metrics.accuracy": "准确率",
  "compare.diff.title": "变化摘要",
  "compare.diff.regressed": "退化题目",
  "compare.diff.improved": "进步题目",
  "compare.diff.newErrors": "新增错误类型",
  "compare.diff.resolvedErrors": "已解决错误类型",
  "compare.diff.noChanges": "两个版本间没有差异",
  "compare.diff.questionId": "题目 ID",
  "compare.diff.benchmark": "Benchmark",
  "compare.diff.category": "任务类别"
}
```

- [ ] **Step 2: Add English translation keys**

Add the corresponding keys to `frontend/src/locales/en.json`:

```json
{
  "analysis.title": "Error Analysis",
  "analysis.treemapTitle": "Error Type Distribution",
  "analysis.backToL1": "Back to L1 Overview",
  "analysis.backToL2": "Back to L2",
  "analysis.errorCount": "Error Count",
  "analysis.percentage": "Percentage",
  "analysis.noErrors": "No error data for the current filters",
  "analysis.recordsTitle": "Error Records",
  "analysis.columns.questionId": "Question ID",
  "analysis.columns.benchmark": "Benchmark",
  "analysis.columns.category": "Category",
  "analysis.columns.question": "Question",
  "analysis.columns.errorTags": "Error Tags",
  "analysis.columns.hasLlm": "LLM Analysis",
  "analysis.columns.actions": "Actions",
  "analysis.viewDetail": "View Detail",
  "analysis.detail.title": "Error Record Detail",
  "analysis.detail.question": "Question",
  "analysis.detail.expected": "Expected Answer",
  "analysis.detail.modelAnswer": "Model Answer",
  "analysis.detail.errorTags": "Error Tags",
  "analysis.detail.analysisResults": "Analysis Results",
  "analysis.detail.rootCause": "Root Cause",
  "analysis.detail.severity": "Severity",
  "analysis.detail.confidence": "Confidence",
  "analysis.detail.evidence": "Evidence",
  "analysis.detail.suggestion": "Suggestion",
  "analysis.detail.analysisType": "Analysis Type",
  "analysis.detail.llmModel": "LLM Model",
  "analysis.detail.llmCost": "Cost",
  "compare.title": "Version Compare",
  "compare.selectVersionA": "Select Version A",
  "compare.selectVersionB": "Select Version B",
  "compare.compare": "Compare",
  "compare.noVersions": "Please select two versions first",
  "compare.radar.title": "Capability Radar",
  "compare.metrics.total": "Total",
  "compare.metrics.errors": "Errors",
  "compare.metrics.accuracy": "Accuracy",
  "compare.diff.title": "Change Summary",
  "compare.diff.regressed": "Regressed",
  "compare.diff.improved": "Improved",
  "compare.diff.newErrors": "New Error Types",
  "compare.diff.resolvedErrors": "Resolved Error Types",
  "compare.diff.noChanges": "No differences between the two versions",
  "compare.diff.questionId": "Question ID",
  "compare.diff.benchmark": "Benchmark",
  "compare.diff.category": "Category"
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/locales/zh.json frontend/src/locales/en.json
git commit -m "feat: add i18n keys for error analysis and version compare pages"
```

---

### Task 2: TanStack Query Hooks — Error Records & Record Detail

**Files:**
- Modify: `frontend/src/api/queries/analysis.ts`
- Test: `frontend/src/api/queries/analysis.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/api/queries/analysis.test.ts`:

```typescript
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { FilterProvider } from "../../contexts/FilterContext";
import { useErrorRecords, useRecordDetail } from "./analysis";

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <FilterProvider>{children}</FilterProvider>
      </QueryClientProvider>
    </MemoryRouter>
  );
};

// Mock axios client
jest.mock("../client", () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
  },
}));

import apiClient from "../client";
const mockedGet = apiClient.get as jest.Mock;

describe("useErrorRecords", () => {
  beforeEach(() => jest.clearAllMocks());

  it("fetches paginated error records", async () => {
    const mockData = {
      items: [
        {
          id: "rec-1",
          session_id: "sess-1",
          benchmark: "mmlu",
          task_category: "math",
          question_id: "q1",
          question: "What is 2+2?",
          is_correct: false,
          score: 0,
          error_tags: ["推理性错误.数学/计算错误"],
          has_llm_analysis: true,
        },
      ],
      total: 1,
      page: 1,
      size: 20,
    };
    mockedGet.mockResolvedValueOnce({ data: mockData });

    const { result } = renderHook(
      () => useErrorRecords({ page: 1, size: 20 }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockData);
    expect(mockedGet).toHaveBeenCalledWith("/analysis/records", {
      params: expect.objectContaining({ page: 1, size: 20 }),
    });
  });

  it("includes error_type filter when provided", async () => {
    mockedGet.mockResolvedValueOnce({
      data: { items: [], total: 0, page: 1, size: 20 },
    });

    const { result } = renderHook(
      () => useErrorRecords({ page: 1, size: 20, errorType: "格式与规范错误" }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedGet).toHaveBeenCalledWith("/analysis/records", {
      params: expect.objectContaining({ error_type: "格式与规范错误" }),
    });
  });
});

describe("useRecordDetail", () => {
  beforeEach(() => jest.clearAllMocks());

  it("fetches record detail by id", async () => {
    const mockDetail = {
      record: { id: "rec-1", question: "What is 2+2?" },
      analysis_results: [
        {
          id: "ar-1",
          analysis_type: "llm",
          error_types: ["推理性错误"],
          root_cause: "calculation error",
          severity: "medium",
          confidence: 0.9,
          evidence: "model said 5",
          suggestion: "improve math training",
          llm_model: "gpt-4",
          llm_cost: 0.01,
          unmatched_tags: [],
          created_at: "2026-03-20T00:00:00Z",
        },
      ],
      error_tags: [{ tag_path: "推理性错误.数学/计算错误", tag_level: 2 }],
    };
    mockedGet.mockResolvedValueOnce({ data: mockDetail });

    const { result } = renderHook(() => useRecordDetail("rec-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockDetail);
    expect(mockedGet).toHaveBeenCalledWith("/analysis/records/rec-1/detail");
  });

  it("does not fetch when id is null", () => {
    renderHook(() => useRecordDetail(null), {
      wrapper: createWrapper(),
    });

    expect(mockedGet).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx jest src/api/queries/analysis.test.ts --no-cache`
Expected: FAIL — `useErrorRecords` and `useRecordDetail` are not exported

- [ ] **Step 3: Implement the hooks**

Add to `frontend/src/api/queries/analysis.ts` (after existing `useErrorDistribution`):

```typescript
import { useQuery } from "@tanstack/react-query";
import apiClient from "../client";
import { useGlobalFilters } from "../../hooks/useGlobalFilters";
import type {
  DistributionItem,
  PaginatedRecords,
  RecordDetail,
} from "../../types/api";

// ... existing useAnalysisSummary and useErrorDistribution hooks ...

interface UseErrorRecordsParams {
  page: number;
  size: number;
  errorType?: string | null;
}

export function useErrorRecords({ page, size, errorType }: UseErrorRecordsParams) {
  const { benchmark, model_version } = useGlobalFilters();

  return useQuery<PaginatedRecords>({
    queryKey: ["errorRecords", page, size, errorType, benchmark, model_version],
    queryFn: async () => {
      const params: Record<string, string | number> = { page, size };
      if (errorType) params.error_type = errorType;
      if (benchmark) params.benchmark = benchmark;
      if (model_version) params.model_version = model_version;
      const { data } = await apiClient.get("/analysis/records", { params });
      return data;
    },
  });
}

export function useRecordDetail(recordId: string | null) {
  return useQuery<RecordDetail>({
    queryKey: ["recordDetail", recordId],
    queryFn: async () => {
      const { data } = await apiClient.get(
        `/analysis/records/${recordId}/detail`
      );
      return data;
    },
    enabled: !!recordId,
  });
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx jest src/api/queries/analysis.test.ts --no-cache`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/queries/analysis.ts frontend/src/api/queries/analysis.test.ts
git commit -m "feat: add useErrorRecords and useRecordDetail query hooks"
```

---

### Task 3: TanStack Query Hooks — Version Compare

**Files:**
- Create: `frontend/src/api/queries/compare.ts`
- Create: `frontend/src/api/queries/compare.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/api/queries/compare.test.ts`:

```typescript
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { FilterProvider } from "../../contexts/FilterContext";
import { useVersionComparison, useVersionDiff, useRadarData } from "./compare";

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <FilterProvider>{children}</FilterProvider>
      </QueryClientProvider>
    </MemoryRouter>
  );
};

jest.mock("../client", () => ({
  __esModule: true,
  default: { get: jest.fn() },
}));

import apiClient from "../client";
const mockedGet = apiClient.get as jest.Mock;

describe("useVersionComparison", () => {
  beforeEach(() => jest.clearAllMocks());

  it("fetches version comparison when both versions provided", async () => {
    const mockData = {
      version_a: "v1.0",
      version_b: "v2.0",
      benchmark: null,
      metrics_a: { total: 100, errors: 30, accuracy: 0.7, error_type_distribution: {} },
      metrics_b: { total: 100, errors: 20, accuracy: 0.8, error_type_distribution: {} },
    };
    mockedGet.mockResolvedValueOnce({ data: mockData });

    const { result } = renderHook(
      () => useVersionComparison("v1.0", "v2.0"),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockData);
    expect(mockedGet).toHaveBeenCalledWith("/compare/versions", {
      params: expect.objectContaining({ version_a: "v1.0", version_b: "v2.0" }),
    });
  });

  it("does not fetch when version_a is null", () => {
    renderHook(() => useVersionComparison(null, "v2.0"), {
      wrapper: createWrapper(),
    });
    expect(mockedGet).not.toHaveBeenCalled();
  });
});

describe("useVersionDiff", () => {
  beforeEach(() => jest.clearAllMocks());

  it("fetches diff data", async () => {
    const mockDiff = {
      regressed: [{ question_id: "q1", benchmark: "mmlu", task_category: "math", question: "2+2?" }],
      improved: [],
      new_errors: ["格式与规范错误"],
      resolved_errors: [],
    };
    mockedGet.mockResolvedValueOnce({ data: mockDiff });

    const { result } = renderHook(
      () => useVersionDiff("v1.0", "v2.0"),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockDiff);
  });

  it("does not fetch when version_b is null", () => {
    renderHook(() => useVersionDiff("v1.0", null), {
      wrapper: createWrapper(),
    });
    expect(mockedGet).not.toHaveBeenCalled();
  });
});

describe("useRadarData", () => {
  beforeEach(() => jest.clearAllMocks());

  it("fetches radar data", async () => {
    const mockRadar = {
      dimensions: ["math", "logic", "reading"],
      scores_a: [0.8, 0.7, 0.9],
      scores_b: [0.85, 0.75, 0.88],
    };
    mockedGet.mockResolvedValueOnce({ data: mockRadar });

    const { result } = renderHook(
      () => useRadarData("v1.0", "v2.0"),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockRadar);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx jest src/api/queries/compare.test.ts --no-cache`
Expected: FAIL — module `./compare` not found

- [ ] **Step 3: Implement the hooks**

Create `frontend/src/api/queries/compare.ts`:

```typescript
import { useQuery } from "@tanstack/react-query";
import apiClient from "../client";
import { useGlobalFilters } from "../../hooks/useGlobalFilters";
import type {
  VersionComparison,
  VersionDiff,
  RadarData,
} from "../../types/api";

export function useVersionComparison(
  versionA: string | null,
  versionB: string | null
) {
  const { benchmark } = useGlobalFilters();

  return useQuery<VersionComparison>({
    queryKey: ["versionComparison", versionA, versionB, benchmark],
    queryFn: async () => {
      const params: Record<string, string> = {
        version_a: versionA!,
        version_b: versionB!,
      };
      if (benchmark) params.benchmark = benchmark;
      const { data } = await apiClient.get("/compare/versions", { params });
      return data;
    },
    enabled: !!versionA && !!versionB,
  });
}

export function useVersionDiff(
  versionA: string | null,
  versionB: string | null
) {
  const { benchmark } = useGlobalFilters();

  return useQuery<VersionDiff>({
    queryKey: ["versionDiff", versionA, versionB, benchmark],
    queryFn: async () => {
      const params: Record<string, string> = {
        version_a: versionA!,
        version_b: versionB!,
      };
      if (benchmark) params.benchmark = benchmark;
      const { data } = await apiClient.get("/compare/diff", { params });
      return data;
    },
    enabled: !!versionA && !!versionB,
  });
}

export function useRadarData(
  versionA: string | null,
  versionB: string | null
) {
  const { benchmark } = useGlobalFilters();

  return useQuery<RadarData>({
    queryKey: ["radarData", versionA, versionB, benchmark],
    queryFn: async () => {
      const params: Record<string, string> = {
        version_a: versionA!,
        version_b: versionB!,
      };
      if (benchmark) params.benchmark = benchmark;
      const { data } = await apiClient.get("/compare/radar", { params });
      return data;
    },
    enabled: !!versionA && !!versionB,
  });
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx jest src/api/queries/compare.test.ts --no-cache`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/queries/compare.ts frontend/src/api/queries/compare.test.ts
git commit -m "feat: add version comparison query hooks"
```

---

### Task 4: ErrorTreemap Component

**Files:**
- Create: `frontend/src/pages/Analysis/components/ErrorTreemap.tsx`
- Create: `frontend/src/pages/Analysis/components/ErrorTreemap.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/Analysis/components/ErrorTreemap.test.tsx`:

```typescript
import { render, screen, fireEvent } from "@testing-library/react";

jest.mock("../../../components/EChartsWrapper", () => ({
  __esModule: true,
  default: ({ option, onEvents }: any) => (
    <div data-testid="echarts-mock" onClick={() => {
      if (onEvents?.click) {
        onEvents.click({ name: "格式与规范错误", value: 42 });
      }
    }}>
      {JSON.stringify(option.series?.[0]?.data?.map((d: any) => d.name))}
    </div>
  ),
}));

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "analysis.treemapTitle": "错误类型分布",
        "analysis.backToL1": "返回 L1 总览",
        "analysis.backToL2": "返回 L2",
        "analysis.errorCount": "错题数",
      };
      return map[key] ?? key;
    },
  }),
}));

import ErrorTreemap from "./ErrorTreemap";
import type { DistributionItem } from "../../../types/api";

const mockL1Data: DistributionItem[] = [
  { label: "格式与规范错误", count: 42, percentage: 30 },
  { label: "推理性错误", count: 28, percentage: 20 },
  { label: "知识性错误", count: 70, percentage: 50 },
];

describe("ErrorTreemap", () => {
  it("renders treemap with L1 data", () => {
    render(
      <ErrorTreemap
        data={mockL1Data}
        loading={false}
        onDrillDown={jest.fn()}
      />
    );
    expect(screen.getByText("错误类型分布")).toBeInTheDocument();
    expect(screen.getByTestId("echarts-mock")).toBeInTheDocument();
  });

  it("calls onDrillDown when a treemap node is clicked", () => {
    const onDrillDown = jest.fn();
    render(
      <ErrorTreemap
        data={mockL1Data}
        loading={false}
        onDrillDown={onDrillDown}
      />
    );
    fireEvent.click(screen.getByTestId("echarts-mock"));
    expect(onDrillDown).toHaveBeenCalledWith("格式与规范错误");
  });

  it("shows back button and breadcrumb when drillLevel > 0", () => {
    render(
      <ErrorTreemap
        data={mockL1Data}
        loading={false}
        onDrillDown={jest.fn()}
        drillLevel={1}
        breadcrumb={["格式与规范错误"]}
        onBack={jest.fn()}
      />
    );
    expect(screen.getByText("返回 L1 总览")).toBeInTheDocument();
  });

  it("calls onBack when back button is clicked", () => {
    const onBack = jest.fn();
    render(
      <ErrorTreemap
        data={mockL1Data}
        loading={false}
        onDrillDown={jest.fn()}
        drillLevel={1}
        breadcrumb={["格式与规范错误"]}
        onBack={onBack}
      />
    );
    fireEvent.click(screen.getByText("返回 L1 总览"));
    expect(onBack).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/pages/Analysis/components/ErrorTreemap.test.tsx --no-cache`
Expected: FAIL — module `./ErrorTreemap` not found

- [ ] **Step 3: Implement ErrorTreemap**

Create `frontend/src/pages/Analysis/components/ErrorTreemap.tsx`:

```typescript
import { Button, Card, Space, Skeleton } from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import EChartsWrapper from "../../../components/EChartsWrapper";
import type { DistributionItem } from "../../../types/api";

interface ErrorTreemapProps {
  data: DistributionItem[];
  loading: boolean;
  onDrillDown: (label: string) => void;
  drillLevel?: number;
  breadcrumb?: string[];
  onBack?: () => void;
}

export default function ErrorTreemap({
  data,
  loading,
  onDrillDown,
  drillLevel = 0,
  breadcrumb = [],
  onBack,
}: ErrorTreemapProps) {
  const { t } = useTranslation();

  const treemapData = data.map((item) => ({
    name: item.label,
    value: item.count,
  }));

  const option = {
    tooltip: {
      formatter: (params: any) =>
        `${params.name}<br/>${t("analysis.errorCount")}: ${params.value}`,
    },
    series: [
      {
        type: "treemap",
        data: treemapData,
        roam: false,
        nodeClick: false,
        breadcrumb: { show: false },
        label: {
          show: true,
          formatter: "{b}\n{c}",
          fontSize: 14,
        },
        itemStyle: {
          borderColor: "#fff",
          borderWidth: 2,
          gapWidth: 2,
        },
      },
    ],
  };

  const handleChartClick = (params: any) => {
    if (params.name) {
      onDrillDown(params.name);
    }
  };

  const backLabel =
    drillLevel === 1
      ? t("analysis.backToL1")
      : drillLevel === 2
        ? t("analysis.backToL2")
        : "";

  return (
    <Card
      title={
        <Space>
          {drillLevel > 0 && onBack && (
            <Button
              type="link"
              icon={<ArrowLeftOutlined />}
              onClick={onBack}
            >
              {backLabel}
            </Button>
          )}
          <span>
            {t("analysis.treemapTitle")}
            {breadcrumb.length > 0 && ` — ${breadcrumb.join(" > ")}`}
          </span>
        </Space>
      }
    >
      {loading ? (
        <Skeleton active paragraph={{ rows: 8 }} />
      ) : (
        <EChartsWrapper
          option={option}
          height={400}
          onEvents={{ click: handleChartClick }}
        />
      )}
    </Card>
  );
}
```

- [ ] **Step 4: Update EChartsWrapper to support onEvents**

The `EChartsWrapper` component from Plan 07 needs an `onEvents` prop. Modify `frontend/src/components/EChartsWrapper.tsx` to add it:

```typescript
import ReactECharts from "echarts-for-react";
import { Skeleton } from "antd";
import type { EChartsOption } from "echarts";

interface EChartsWrapperProps {
  option: EChartsOption;
  height?: number;
  loading?: boolean;
  onEvents?: Record<string, (params: any) => void>;
}

export default function EChartsWrapper({
  option,
  height = 400,
  loading = false,
  onEvents,
}: EChartsWrapperProps) {
  if (loading) {
    return <Skeleton active paragraph={{ rows: 6 }} />;
  }

  return (
    <ReactECharts
      option={option}
      style={{ height }}
      opts={{ renderer: "canvas" }}
      onEvents={onEvents}
    />
  );
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && npx jest src/pages/Analysis/components/ErrorTreemap.test.tsx --no-cache`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Analysis/components/ErrorTreemap.tsx \
       frontend/src/pages/Analysis/components/ErrorTreemap.test.tsx \
       frontend/src/components/EChartsWrapper.tsx
git commit -m "feat: add ErrorTreemap component with drill-down support"
```

---

### Task 5: ErrorTable Component

**Files:**
- Create: `frontend/src/pages/Analysis/components/ErrorTable.tsx`
- Create: `frontend/src/pages/Analysis/components/ErrorTable.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/Analysis/components/ErrorTable.test.tsx`:

```typescript
import { render, screen, fireEvent } from "@testing-library/react";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "analysis.recordsTitle": "错题列表",
        "analysis.columns.questionId": "题目 ID",
        "analysis.columns.benchmark": "Benchmark",
        "analysis.columns.category": "任务类别",
        "analysis.columns.question": "题目",
        "analysis.columns.errorTags": "错因标签",
        "analysis.columns.hasLlm": "LLM 分析",
        "analysis.columns.actions": "操作",
        "analysis.viewDetail": "查看详情",
      };
      return map[key] ?? key;
    },
  }),
}));

import ErrorTable from "./ErrorTable";
import type { ErrorRecordBrief } from "../../../types/api";

const mockRecords: ErrorRecordBrief[] = [
  {
    id: "rec-1",
    session_id: "sess-1",
    benchmark: "mmlu",
    task_category: "math",
    question_id: "q1",
    question: "What is 2+2?",
    is_correct: false,
    score: 0,
    error_tags: ["推理性错误.数学/计算错误"],
    has_llm_analysis: true,
  },
  {
    id: "rec-2",
    session_id: "sess-1",
    benchmark: "mmlu",
    task_category: "logic",
    question_id: "q2",
    question: "All cats are...",
    is_correct: false,
    score: 0,
    error_tags: ["推理性错误.逻辑推理错误"],
    has_llm_analysis: false,
  },
];

describe("ErrorTable", () => {
  it("renders table with records", () => {
    render(
      <ErrorTable
        records={mockRecords}
        total={2}
        page={1}
        size={20}
        loading={false}
        onPageChange={jest.fn()}
        onViewDetail={jest.fn()}
      />
    );
    expect(screen.getByText("错题列表")).toBeInTheDocument();
    expect(screen.getByText("q1")).toBeInTheDocument();
    expect(screen.getByText("q2")).toBeInTheDocument();
  });

  it("calls onViewDetail when view button is clicked", () => {
    const onViewDetail = jest.fn();
    render(
      <ErrorTable
        records={mockRecords}
        total={2}
        page={1}
        size={20}
        loading={false}
        onPageChange={jest.fn()}
        onViewDetail={onViewDetail}
      />
    );
    const buttons = screen.getAllByText("查看详情");
    fireEvent.click(buttons[0]);
    expect(onViewDetail).toHaveBeenCalledWith("rec-1");
  });

  it("shows LLM analysis status as check/close icons", () => {
    const { container } = render(
      <ErrorTable
        records={mockRecords}
        total={2}
        page={1}
        size={20}
        loading={false}
        onPageChange={jest.fn()}
        onViewDetail={jest.fn()}
      />
    );
    // rec-1 has LLM analysis (check), rec-2 does not (close)
    const checkIcons = container.querySelectorAll(".anticon-check-circle");
    const closeIcons = container.querySelectorAll(".anticon-close-circle");
    expect(checkIcons.length).toBe(1);
    expect(closeIcons.length).toBe(1);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/pages/Analysis/components/ErrorTable.test.tsx --no-cache`
Expected: FAIL — module `./ErrorTable` not found

- [ ] **Step 3: Implement ErrorTable**

Create `frontend/src/pages/Analysis/components/ErrorTable.tsx`:

```typescript
import { Table, Card, Tag, Button, Space } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  EyeOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import type { ColumnsType } from "antd/es/table";
import type { ErrorRecordBrief } from "../../../types/api";

interface ErrorTableProps {
  records: ErrorRecordBrief[];
  total: number;
  page: number;
  size: number;
  loading: boolean;
  onPageChange: (page: number, size: number) => void;
  onViewDetail: (recordId: string) => void;
}

export default function ErrorTable({
  records,
  total,
  page,
  size,
  loading,
  onPageChange,
  onViewDetail,
}: ErrorTableProps) {
  const { t } = useTranslation();

  const columns: ColumnsType<ErrorRecordBrief> = [
    {
      title: t("analysis.columns.questionId"),
      dataIndex: "question_id",
      key: "question_id",
      width: 120,
      ellipsis: true,
    },
    {
      title: t("analysis.columns.benchmark"),
      dataIndex: "benchmark",
      key: "benchmark",
      width: 120,
    },
    {
      title: t("analysis.columns.category"),
      dataIndex: "task_category",
      key: "task_category",
      width: 120,
      ellipsis: true,
    },
    {
      title: t("analysis.columns.question"),
      dataIndex: "question",
      key: "question",
      ellipsis: true,
    },
    {
      title: t("analysis.columns.errorTags"),
      dataIndex: "error_tags",
      key: "error_tags",
      width: 240,
      render: (tags: string[]) => (
        <Space size={[0, 4]} wrap>
          {tags.map((tag) => (
            <Tag key={tag} color="red">
              {tag}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: t("analysis.columns.hasLlm"),
      dataIndex: "has_llm_analysis",
      key: "has_llm_analysis",
      width: 100,
      align: "center",
      render: (hasLlm: boolean) =>
        hasLlm ? (
          <CheckCircleOutlined style={{ color: "#52c41a" }} />
        ) : (
          <CloseCircleOutlined style={{ color: "#ff4d4f" }} />
        ),
    },
    {
      title: t("analysis.columns.actions"),
      key: "actions",
      width: 120,
      render: (_, record) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => onViewDetail(record.id)}
        >
          {t("analysis.viewDetail")}
        </Button>
      ),
    },
  ];

  return (
    <Card title={t("analysis.recordsTitle")}>
      <Table<ErrorRecordBrief>
        columns={columns}
        dataSource={records}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize: size,
          total,
          showSizeChanger: true,
          showTotal: (total) => `${total} items`,
          onChange: onPageChange,
        }}
      />
    </Card>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx jest src/pages/Analysis/components/ErrorTable.test.tsx --no-cache`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Analysis/components/ErrorTable.tsx \
       frontend/src/pages/Analysis/components/ErrorTable.test.tsx
git commit -m "feat: add ErrorTable component with pagination"
```

---

### Task 6: RecordDetail Drawer Component

**Files:**
- Create: `frontend/src/pages/Analysis/components/RecordDetail.tsx`
- Create: `frontend/src/pages/Analysis/components/RecordDetail.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/Analysis/components/RecordDetail.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "analysis.detail.title": "错题详情",
        "analysis.detail.question": "题目",
        "analysis.detail.expected": "标准答案",
        "analysis.detail.modelAnswer": "模型回答",
        "analysis.detail.errorTags": "错因标签",
        "analysis.detail.analysisResults": "分析结果",
        "analysis.detail.rootCause": "根因分析",
        "analysis.detail.severity": "严重程度",
        "analysis.detail.confidence": "置信度",
        "analysis.detail.evidence": "证据",
        "analysis.detail.suggestion": "改进建议",
        "analysis.detail.analysisType": "分析方式",
        "analysis.detail.llmModel": "使用模型",
        "analysis.detail.llmCost": "分析成本",
      };
      return map[key] ?? key;
    },
  }),
}));

import RecordDetail from "./RecordDetail";
import type { RecordDetail as RecordDetailType } from "../../../types/api";

const mockDetail: RecordDetailType = {
  record: {
    id: "rec-1",
    question: "What is 2+2?",
    expected_answer: "4",
    model_answer: "5",
    benchmark: "mmlu",
    task_category: "math",
  },
  analysis_results: [
    {
      id: "ar-1",
      analysis_type: "llm",
      error_types: ["推理性错误.数学/计算错误"],
      root_cause: "模型在简单算术计算中出错",
      severity: "medium",
      confidence: 0.92,
      evidence: "模型回答 5，正确答案是 4",
      suggestion: "加强基础算术训练数据",
      llm_model: "gpt-4",
      llm_cost: 0.01,
      unmatched_tags: [],
      created_at: "2026-03-20T00:00:00Z",
    },
  ],
  error_tags: [
    { tag_path: "推理性错误.数学/计算错误.算术错误", tag_level: 3 },
  ],
};

describe("RecordDetail", () => {
  it("renders question, expected answer, and model answer", () => {
    render(
      <RecordDetail detail={mockDetail} open={true} onClose={jest.fn()} />
    );
    expect(screen.getByText("What is 2+2?")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("renders error tags", () => {
    render(
      <RecordDetail detail={mockDetail} open={true} onClose={jest.fn()} />
    );
    expect(screen.getByText("推理性错误.数学/计算错误.算术错误")).toBeInTheDocument();
  });

  it("renders analysis result fields", () => {
    render(
      <RecordDetail detail={mockDetail} open={true} onClose={jest.fn()} />
    );
    expect(screen.getByText("模型在简单算术计算中出错")).toBeInTheDocument();
    expect(screen.getByText("模型回答 5，正确答案是 4")).toBeInTheDocument();
    expect(screen.getByText("加强基础算术训练数据")).toBeInTheDocument();
    expect(screen.getByText("gpt-4")).toBeInTheDocument();
  });

  it("does not render when open is false", () => {
    const { container } = render(
      <RecordDetail detail={mockDetail} open={false} onClose={jest.fn()} />
    );
    expect(container.querySelector(".ant-drawer")).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/pages/Analysis/components/RecordDetail.test.tsx --no-cache`
Expected: FAIL — module `./RecordDetail` not found

- [ ] **Step 3: Implement RecordDetail**

Create `frontend/src/pages/Analysis/components/RecordDetail.tsx`:

```typescript
import {
  Drawer,
  Descriptions,
  Tag,
  Typography,
  Divider,
  Card,
  Space,
} from "antd";
import { useTranslation } from "react-i18next";
import type {
  RecordDetail as RecordDetailType,
  AnalysisResultDetail,
} from "../../../types/api";

const { Text, Paragraph } = Typography;

interface RecordDetailProps {
  detail: RecordDetailType | null;
  open: boolean;
  onClose: () => void;
}

function AnalysisCard({ result }: { result: AnalysisResultDetail }) {
  const { t } = useTranslation();

  return (
    <Card
      size="small"
      title={
        <Space>
          <Tag color={result.analysis_type === "llm" ? "blue" : "green"}>
            {result.analysis_type.toUpperCase()}
          </Tag>
          <Text type="secondary">
            {t("analysis.detail.analysisType")}: {result.analysis_type}
          </Text>
        </Space>
      }
      style={{ marginBottom: 12 }}
    >
      <Descriptions column={2} size="small" bordered>
        {result.root_cause && (
          <Descriptions.Item
            label={t("analysis.detail.rootCause")}
            span={2}
          >
            {result.root_cause}
          </Descriptions.Item>
        )}
        {result.severity && (
          <Descriptions.Item label={t("analysis.detail.severity")}>
            <Tag
              color={
                result.severity === "high"
                  ? "red"
                  : result.severity === "medium"
                    ? "orange"
                    : "green"
              }
            >
              {result.severity}
            </Tag>
          </Descriptions.Item>
        )}
        {result.confidence != null && (
          <Descriptions.Item label={t("analysis.detail.confidence")}>
            {(result.confidence * 100).toFixed(1)}%
          </Descriptions.Item>
        )}
        {result.evidence && (
          <Descriptions.Item label={t("analysis.detail.evidence")} span={2}>
            {result.evidence}
          </Descriptions.Item>
        )}
        {result.suggestion && (
          <Descriptions.Item label={t("analysis.detail.suggestion")} span={2}>
            {result.suggestion}
          </Descriptions.Item>
        )}
        {result.llm_model && (
          <Descriptions.Item label={t("analysis.detail.llmModel")}>
            {result.llm_model}
          </Descriptions.Item>
        )}
        {result.llm_cost != null && (
          <Descriptions.Item label={t("analysis.detail.llmCost")}>
            ${result.llm_cost.toFixed(4)}
          </Descriptions.Item>
        )}
      </Descriptions>
    </Card>
  );
}

export default function RecordDetail({
  detail,
  open,
  onClose,
}: RecordDetailProps) {
  const { t } = useTranslation();

  if (!detail) return null;

  const { record, analysis_results, error_tags } = detail;

  return (
    <Drawer
      title={t("analysis.detail.title")}
      open={open}
      onClose={onClose}
      width={720}
      destroyOnClose
    >
      {/* Question / Expected / Model Answer */}
      <Descriptions column={1} bordered size="small">
        <Descriptions.Item label={t("analysis.detail.question")}>
          <Paragraph style={{ marginBottom: 0 }}>
            {record.question as string}
          </Paragraph>
        </Descriptions.Item>
        <Descriptions.Item label={t("analysis.detail.expected")}>
          <Paragraph style={{ marginBottom: 0 }}>
            {record.expected_answer as string}
          </Paragraph>
        </Descriptions.Item>
        <Descriptions.Item label={t("analysis.detail.modelAnswer")}>
          <Paragraph style={{ marginBottom: 0 }}>
            {record.model_answer as string}
          </Paragraph>
        </Descriptions.Item>
      </Descriptions>

      {/* Error Tags */}
      <Divider orientation="left">{t("analysis.detail.errorTags")}</Divider>
      <Space size={[4, 8]} wrap>
        {error_tags.map((tag: any, idx: number) => (
          <Tag key={idx} color="red">
            {tag.tag_path}
          </Tag>
        ))}
      </Space>

      {/* Analysis Results */}
      <Divider orientation="left">
        {t("analysis.detail.analysisResults")}
      </Divider>
      {analysis_results.map((result) => (
        <AnalysisCard key={result.id} result={result} />
      ))}

      {/* Note: "Re-analyze with LLM" and "Manual Annotate" buttons
          (spec section 9.3) are deferred to a future plan — they depend
          on POST /api/v1/llm/trigger and manual annotation endpoints. */}
    </Drawer>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx jest src/pages/Analysis/components/RecordDetail.test.tsx --no-cache`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Analysis/components/RecordDetail.tsx \
       frontend/src/pages/Analysis/components/RecordDetail.test.tsx
git commit -m "feat: add RecordDetail drawer component"
```

---

### Task 7: Error Analysis Page Assembly

**Files:**
- Create: `frontend/src/pages/Analysis/index.tsx`
- Create: `frontend/src/pages/Analysis/Analysis.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/Analysis/Analysis.test.tsx`:

```typescript
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { type ReactNode } from "react";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "analysis.title": "错因分析",
        "analysis.treemapTitle": "错误类型分布",
        "analysis.recordsTitle": "错题列表",
        "analysis.noErrors": "当前筛选条件下没有错题数据",
        "analysis.backToL1": "返回 L1 总览",
        "analysis.columns.questionId": "题目 ID",
        "analysis.columns.benchmark": "Benchmark",
        "analysis.columns.category": "任务类别",
        "analysis.columns.question": "题目",
        "analysis.columns.errorTags": "错因标签",
        "analysis.columns.hasLlm": "LLM 分析",
        "analysis.columns.actions": "操作",
        "analysis.viewDetail": "查看详情",
        "analysis.detail.title": "错题详情",
        "analysis.errorCount": "错题数",
        "common.error": "加载失败",
        "common.retry": "重试",
      };
      return map[key] ?? key;
    },
  }),
}));

// Mock the query hooks
jest.mock("../../api/queries/analysis", () => ({
  useErrorDistribution: jest.fn(),
  useErrorRecords: jest.fn(),
  useRecordDetail: jest.fn(),
}));

jest.mock("../../hooks/useGlobalFilters", () => ({
  useGlobalFilters: () => ({
    benchmark: null,
    model_version: null,
    time_range_start: null,
    time_range_end: null,
    setFilter: jest.fn(),
    resetFilters: jest.fn(),
  }),
}));

jest.mock("../../components/EChartsWrapper", () => ({
  __esModule: true,
  default: ({ option }: any) => (
    <div data-testid="echarts-mock">
      {JSON.stringify(option.series?.[0]?.data?.map((d: any) => d.name))}
    </div>
  ),
}));

import Analysis from "./index";
import {
  useErrorDistribution,
  useErrorRecords,
  useRecordDetail,
} from "../../api/queries/analysis";

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

describe("Analysis Page", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useErrorDistribution as jest.Mock).mockReturnValue({
      data: [
        { label: "格式与规范错误", count: 42, percentage: 30 },
        { label: "推理性错误", count: 28, percentage: 20 },
      ],
      isLoading: false,
      isError: false,
    });
    (useErrorRecords as jest.Mock).mockReturnValue({
      data: {
        items: [
          {
            id: "rec-1",
            session_id: "s1",
            benchmark: "mmlu",
            task_category: "math",
            question_id: "q1",
            question: "2+2?",
            is_correct: false,
            score: 0,
            error_tags: ["推理性错误"],
            has_llm_analysis: false,
          },
        ],
        total: 1,
        page: 1,
        size: 20,
      },
      isLoading: false,
      isError: false,
    });
    (useRecordDetail as jest.Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });
  });

  it("renders the treemap and table", () => {
    render(<Analysis />, { wrapper: createWrapper() });
    expect(screen.getByText("错误类型分布")).toBeInTheDocument();
    expect(screen.getByText("错题列表")).toBeInTheDocument();
  });

  it("shows empty state when no distribution data", () => {
    (useErrorDistribution as jest.Mock).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    });
    (useErrorRecords as jest.Mock).mockReturnValue({
      data: { items: [], total: 0, page: 1, size: 20 },
      isLoading: false,
      isError: false,
    });

    render(<Analysis />, { wrapper: createWrapper() });
    expect(screen.getByText("当前筛选条件下没有错题数据")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/pages/Analysis/Analysis.test.tsx --no-cache`
Expected: FAIL — module `./index` not found

- [ ] **Step 3: Implement the Analysis page**

Create `frontend/src/pages/Analysis/index.tsx`:

```typescript
import { useState, useCallback } from "react";
import { Typography, Space, Alert, Empty, Button } from "antd";
import { useTranslation } from "react-i18next";
import {
  useErrorDistribution,
  useErrorRecords,
  useRecordDetail,
} from "../../api/queries/analysis";
import ErrorTreemap from "./components/ErrorTreemap";
import ErrorTable from "./components/ErrorTable";
import RecordDetail from "./components/RecordDetail";

const { Title } = Typography;

export default function Analysis() {
  const { t } = useTranslation();

  // Drill-down state: L1 → L2 → L3
  const [drillPath, setDrillPath] = useState<string[]>([]);
  const drillLevel = drillPath.length;

  // Build the error_type filter from drill path
  // L0: no filter (all L1 categories)
  // L1: filter by L1 label (shows L2 subcategories)
  // L2: filter by L1.L2 label (shows L3 subcategories)
  const currentErrorType = drillPath.length > 0 ? drillPath.join(".") : undefined;

  // Always group by error_type — the error_type filter controls which
  // level of the taxonomy the backend returns (L1 → L2 → L3)
  const groupBy = "error_type" as const;

  // Distribution data for the treemap
  const {
    data: distributionData,
    isLoading: distLoading,
    isError: distError,
    refetch: refetchDist,
  } = useErrorDistribution(groupBy, currentErrorType);

  // Paginated error records (filtered by current drill path)
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const {
    data: recordsData,
    isLoading: recordsLoading,
    isError: recordsError,
  } = useErrorRecords({ page, size: pageSize, errorType: currentErrorType });

  // Record detail drawer
  const [selectedRecordId, setSelectedRecordId] = useState<string | null>(null);
  const { data: recordDetail } = useRecordDetail(selectedRecordId);

  const handleDrillDown = useCallback((label: string) => {
    if (drillLevel >= 2) return; // L3 is the deepest level
    setDrillPath((prev) => [...prev, label]);
    setPage(1);
  }, [drillLevel]);

  const handleBack = useCallback(() => {
    setDrillPath((prev) => prev.slice(0, -1));
    setPage(1);
  }, []);

  const handlePageChange = useCallback((newPage: number, newSize: number) => {
    setPage(newPage);
    setPageSize(newSize);
  }, []);

  const handleViewDetail = useCallback((recordId: string) => {
    setSelectedRecordId(recordId);
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedRecordId(null);
  }, []);

  // Empty state
  const isEmpty =
    !distLoading &&
    !distError &&
    (!distributionData || distributionData.length === 0);

  if (distError || recordsError) {
    return (
      <Alert
        type="error"
        message={t("common.error")}
        action={
          <Button size="small" onClick={() => refetchDist()}>
            {t("common.retry")}
          </Button>
        }
      />
    );
  }

  if (isEmpty) {
    return <Empty description={t("analysis.noErrors")} />;
  }

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Title level={4}>{t("analysis.title")}</Title>

      <ErrorTreemap
        data={distributionData ?? []}
        loading={distLoading}
        onDrillDown={handleDrillDown}
        drillLevel={drillLevel}
        breadcrumb={drillPath}
        onBack={handleBack}
      />

      <ErrorTable
        records={recordsData?.items ?? []}
        total={recordsData?.total ?? 0}
        page={page}
        size={pageSize}
        loading={recordsLoading}
        onPageChange={handlePageChange}
        onViewDetail={handleViewDetail}
      />

      <RecordDetail
        detail={recordDetail ?? null}
        open={!!selectedRecordId}
        onClose={handleCloseDetail}
      />
    </Space>
  );
}
```

- [ ] **Step 4: Update useErrorDistribution to support drill-down**

The existing `useErrorDistribution` in `frontend/src/api/queries/analysis.ts` accepts only `groupBy`. We need to extend it to accept an optional `errorType` for drill-down filtering. Update the hook:

```typescript
export function useErrorDistribution(
  groupBy: "error_type" | "category" | "severity",
  errorType?: string
) {
  const { benchmark, model_version, time_range_start, time_range_end } =
    useGlobalFilters();

  return useQuery<DistributionItem[]>({
    queryKey: [
      "errorDistribution",
      groupBy,
      errorType,
      benchmark,
      model_version,
      time_range_start,
      time_range_end,
    ],
    queryFn: async () => {
      const params: Record<string, string> = { group_by: groupBy };
      if (errorType) params.error_type = errorType;
      if (benchmark) params.benchmark = benchmark;
      if (model_version) params.model_version = model_version;
      if (time_range_start) params.time_range_start = time_range_start;
      if (time_range_end) params.time_range_end = time_range_end;
      const { data } = await apiClient.get("/analysis/error-distribution", {
        params,
      });
      return data;
    },
  });
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && npx jest src/pages/Analysis/Analysis.test.tsx --no-cache`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Analysis/index.tsx \
       frontend/src/pages/Analysis/Analysis.test.tsx \
       frontend/src/api/queries/analysis.ts
git commit -m "feat: implement Error Analysis page with treemap drill-down"
```

---

### Task 8: VersionSelector Component

**Files:**
- Create: `frontend/src/pages/Compare/components/VersionSelector.tsx`
- Create: `frontend/src/pages/Compare/components/VersionSelector.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/Compare/components/VersionSelector.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "compare.selectVersionA": "选择版本 A",
        "compare.selectVersionB": "选择版本 B",
        "compare.compare": "对比",
      };
      return map[key] ?? key;
    },
  }),
}));

import VersionSelector from "./VersionSelector";

const mockVersions = ["v1.0", "v2.0", "v3.0"];

describe("VersionSelector", () => {
  it("renders two Select dropdowns and a compare button", () => {
    render(
      <VersionSelector
        versions={mockVersions}
        versionA={null}
        versionB={null}
        onVersionAChange={jest.fn()}
        onVersionBChange={jest.fn()}
        onCompare={jest.fn()}
        loading={false}
      />
    );
    expect(screen.getByText("选择版本 A")).toBeInTheDocument();
    expect(screen.getByText("选择版本 B")).toBeInTheDocument();
    expect(screen.getByText("对比")).toBeInTheDocument();
  });

  it("disables compare button when versions not selected", () => {
    render(
      <VersionSelector
        versions={mockVersions}
        versionA={null}
        versionB={null}
        onVersionAChange={jest.fn()}
        onVersionBChange={jest.fn()}
        onCompare={jest.fn()}
        loading={false}
      />
    );
    const button = screen.getByText("对比").closest("button");
    expect(button).toBeDisabled();
  });

  it("enables compare button when both versions selected", () => {
    render(
      <VersionSelector
        versions={mockVersions}
        versionA="v1.0"
        versionB="v2.0"
        onVersionAChange={jest.fn()}
        onVersionBChange={jest.fn()}
        onCompare={jest.fn()}
        loading={false}
      />
    );
    const button = screen.getByText("对比").closest("button");
    expect(button).not.toBeDisabled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/pages/Compare/components/VersionSelector.test.tsx --no-cache`
Expected: FAIL — module `./VersionSelector` not found

- [ ] **Step 3: Implement VersionSelector**

Create `frontend/src/pages/Compare/components/VersionSelector.tsx`:

```typescript
import { Select, Button, Space, Card } from "antd";
import { SwapOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";

interface VersionSelectorProps {
  versions: string[];
  versionA: string | null;
  versionB: string | null;
  onVersionAChange: (version: string) => void;
  onVersionBChange: (version: string) => void;
  onCompare: () => void;
  loading: boolean;
}

export default function VersionSelector({
  versions,
  versionA,
  versionB,
  onVersionAChange,
  onVersionBChange,
  onCompare,
  loading,
}: VersionSelectorProps) {
  const { t } = useTranslation();

  const options = versions.map((v) => ({ label: v, value: v }));

  return (
    <Card>
      <Space size="middle" wrap>
        <Select
          placeholder={t("compare.selectVersionA")}
          value={versionA}
          onChange={onVersionAChange}
          options={options}
          style={{ width: 200 }}
          showSearch
        />
        <Select
          placeholder={t("compare.selectVersionB")}
          value={versionB}
          onChange={onVersionBChange}
          options={options}
          style={{ width: 200 }}
          showSearch
        />
        <Button
          type="primary"
          icon={<SwapOutlined />}
          onClick={onCompare}
          disabled={!versionA || !versionB}
          loading={loading}
        >
          {t("compare.compare")}
        </Button>
      </Space>
    </Card>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx jest src/pages/Compare/components/VersionSelector.test.tsx --no-cache`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Compare/components/VersionSelector.tsx \
       frontend/src/pages/Compare/components/VersionSelector.test.tsx
git commit -m "feat: add VersionSelector component"
```

---

### Task 9: RadarChart Component

**Files:**
- Create: `frontend/src/pages/Compare/components/RadarChart.tsx`
- Create: `frontend/src/pages/Compare/components/RadarChart.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/Compare/components/RadarChart.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "compare.radar.title": "能力雷达图",
      };
      return map[key] ?? key;
    },
  }),
}));

jest.mock("../../../components/EChartsWrapper", () => ({
  __esModule: true,
  default: ({ option }: any) => (
    <div data-testid="echarts-mock">
      {JSON.stringify(option.radar?.indicator?.map((i: any) => i.name))}
    </div>
  ),
}));

import RadarChart from "./RadarChart";
import type { RadarData } from "../../../types/api";

const mockData: RadarData = {
  dimensions: ["math", "logic", "reading", "writing"],
  scores_a: [0.8, 0.7, 0.9, 0.6],
  scores_b: [0.85, 0.75, 0.88, 0.7],
};

describe("RadarChart", () => {
  it("renders the radar chart card with title", () => {
    render(
      <RadarChart data={mockData} versionA="v1.0" versionB="v2.0" loading={false} />
    );
    expect(screen.getByText("能力雷达图")).toBeInTheDocument();
  });

  it("passes dimensions as radar indicators", () => {
    render(
      <RadarChart data={mockData} versionA="v1.0" versionB="v2.0" loading={false} />
    );
    const chart = screen.getByTestId("echarts-mock");
    expect(chart.textContent).toContain("math");
    expect(chart.textContent).toContain("logic");
    expect(chart.textContent).toContain("reading");
    expect(chart.textContent).toContain("writing");
  });

  it("renders loading skeleton when loading", () => {
    const { container } = render(
      <RadarChart data={null} versionA="v1.0" versionB="v2.0" loading={true} />
    );
    expect(container.querySelector(".ant-skeleton")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/pages/Compare/components/RadarChart.test.tsx --no-cache`
Expected: FAIL — module `./RadarChart` not found

- [ ] **Step 3: Implement RadarChart**

Create `frontend/src/pages/Compare/components/RadarChart.tsx`:

```typescript
import { Card, Skeleton } from "antd";
import { useTranslation } from "react-i18next";
import EChartsWrapper from "../../../components/EChartsWrapper";
import type { RadarData } from "../../../types/api";

interface RadarChartProps {
  data: RadarData | null;
  versionA: string;
  versionB: string;
  loading: boolean;
}

export default function RadarChart({
  data,
  versionA,
  versionB,
  loading,
}: RadarChartProps) {
  const { t } = useTranslation();

  if (loading || !data) {
    return (
      <Card title={t("compare.radar.title")}>
        <Skeleton active paragraph={{ rows: 8 }} />
      </Card>
    );
  }

  const indicator = data.dimensions.map((dim) => ({
    name: dim,
    max: 1,
  }));

  const option = {
    tooltip: {},
    legend: {
      data: [versionA, versionB],
      bottom: 0,
    },
    radar: {
      indicator,
    },
    series: [
      {
        type: "radar",
        data: [
          {
            value: data.scores_a,
            name: versionA,
            areaStyle: { opacity: 0.2 },
          },
          {
            value: data.scores_b,
            name: versionB,
            areaStyle: { opacity: 0.2 },
          },
        ],
      },
    ],
  };

  return (
    <Card title={t("compare.radar.title")}>
      <EChartsWrapper option={option} height={400} />
    </Card>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx jest src/pages/Compare/components/RadarChart.test.tsx --no-cache`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Compare/components/RadarChart.tsx \
       frontend/src/pages/Compare/components/RadarChart.test.tsx
git commit -m "feat: add RadarChart component for version comparison"
```

---

### Task 10: DiffSummary Component

**Files:**
- Create: `frontend/src/pages/Compare/components/DiffSummary.tsx`
- Create: `frontend/src/pages/Compare/components/DiffSummary.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/Compare/components/DiffSummary.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "compare.diff.title": "变化摘要",
        "compare.diff.regressed": "退化题目",
        "compare.diff.improved": "进步题目",
        "compare.diff.newErrors": "新增错误类型",
        "compare.diff.resolvedErrors": "已解决错误类型",
        "compare.diff.noChanges": "两个版本间没有差异",
        "compare.diff.questionId": "题目 ID",
        "compare.diff.benchmark": "Benchmark",
        "compare.diff.category": "任务类别",
        "compare.metrics.total": "总题数",
        "compare.metrics.errors": "错题数",
        "compare.metrics.accuracy": "准确率",
      };
      return map[key] ?? key;
    },
  }),
}));

import DiffSummary from "./DiffSummary";
import type { VersionComparison, VersionDiff } from "../../../types/api";

const mockComparison: VersionComparison = {
  version_a: "v1.0",
  version_b: "v2.0",
  benchmark: null,
  metrics_a: { total: 100, errors: 30, accuracy: 0.7, error_type_distribution: {} },
  metrics_b: { total: 100, errors: 20, accuracy: 0.8, error_type_distribution: {} },
};

const mockDiff: VersionDiff = {
  regressed: [
    { question_id: "q1", benchmark: "mmlu", task_category: "math", question: "2+2?" },
  ],
  improved: [
    { question_id: "q2", benchmark: "mmlu", task_category: "logic", question: "If A then B" },
  ],
  new_errors: ["格式与规范错误"],
  resolved_errors: ["解析类错误"],
};

describe("DiffSummary", () => {
  it("renders metrics comparison", () => {
    render(
      <DiffSummary
        comparison={mockComparison}
        diff={mockDiff}
        loading={false}
      />
    );
    expect(screen.getByText("变化摘要")).toBeInTheDocument();
    expect(screen.getByText("总题数")).toBeInTheDocument();
  });

  it("renders regressed items", () => {
    render(
      <DiffSummary
        comparison={mockComparison}
        diff={mockDiff}
        loading={false}
      />
    );
    expect(screen.getByText("退化题目")).toBeInTheDocument();
    expect(screen.getByText("q1")).toBeInTheDocument();
  });

  it("renders improved items", () => {
    render(
      <DiffSummary
        comparison={mockComparison}
        diff={mockDiff}
        loading={false}
      />
    );
    expect(screen.getByText("进步题目")).toBeInTheDocument();
    expect(screen.getByText("q2")).toBeInTheDocument();
  });

  it("renders new and resolved error types", () => {
    render(
      <DiffSummary
        comparison={mockComparison}
        diff={mockDiff}
        loading={false}
      />
    );
    expect(screen.getByText("新增错误类型")).toBeInTheDocument();
    expect(screen.getByText("格式与规范错误")).toBeInTheDocument();
    expect(screen.getByText("已解决错误类型")).toBeInTheDocument();
    expect(screen.getByText("解析类错误")).toBeInTheDocument();
  });

  it("shows no-changes message when diff is empty", () => {
    const emptyDiff: VersionDiff = {
      regressed: [],
      improved: [],
      new_errors: [],
      resolved_errors: [],
    };
    render(
      <DiffSummary
        comparison={mockComparison}
        diff={emptyDiff}
        loading={false}
      />
    );
    expect(screen.getByText("两个版本间没有差异")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/pages/Compare/components/DiffSummary.test.tsx --no-cache`
Expected: FAIL — module `./DiffSummary` not found

- [ ] **Step 3: Implement DiffSummary**

Create `frontend/src/pages/Compare/components/DiffSummary.tsx`:

```typescript
import {
  Card,
  Table,
  Descriptions,
  Tag,
  Tabs,
  Space,
  Empty,
  Skeleton,
} from "antd";
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  PlusOutlined,
  CheckOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import type { ColumnsType } from "antd/es/table";
import type {
  VersionComparison,
  VersionDiff,
  DiffItem,
} from "../../../types/api";

interface DiffSummaryProps {
  comparison: VersionComparison | null;
  diff: VersionDiff | null;
  loading: boolean;
}

export default function DiffSummary({
  comparison,
  diff,
  loading,
}: DiffSummaryProps) {
  const { t } = useTranslation();

  if (loading || !comparison || !diff) {
    return (
      <Card title={t("compare.diff.title")}>
        <Skeleton active paragraph={{ rows: 6 }} />
      </Card>
    );
  }

  const hasChanges =
    diff.regressed.length > 0 ||
    diff.improved.length > 0 ||
    diff.new_errors.length > 0 ||
    diff.resolved_errors.length > 0;

  const diffColumns: ColumnsType<DiffItem> = [
    {
      title: t("compare.diff.questionId"),
      dataIndex: "question_id",
      key: "question_id",
      width: 140,
    },
    {
      title: t("compare.diff.benchmark"),
      dataIndex: "benchmark",
      key: "benchmark",
      width: 120,
    },
    {
      title: t("compare.diff.category"),
      dataIndex: "task_category",
      key: "task_category",
      width: 120,
    },
  ];

  const tabItems = [
    {
      key: "regressed",
      label: (
        <Space>
          <ArrowDownOutlined style={{ color: "#ff4d4f" }} />
          {t("compare.diff.regressed")} ({diff.regressed.length})
        </Space>
      ),
      children: (
        <Table<DiffItem>
          columns={diffColumns}
          dataSource={diff.regressed}
          rowKey="question_id"
          size="small"
          pagination={{ pageSize: 10 }}
        />
      ),
    },
    {
      key: "improved",
      label: (
        <Space>
          <ArrowUpOutlined style={{ color: "#52c41a" }} />
          {t("compare.diff.improved")} ({diff.improved.length})
        </Space>
      ),
      children: (
        <Table<DiffItem>
          columns={diffColumns}
          dataSource={diff.improved}
          rowKey="question_id"
          size="small"
          pagination={{ pageSize: 10 }}
        />
      ),
    },
    {
      key: "newErrors",
      label: (
        <Space>
          <PlusOutlined style={{ color: "#ff4d4f" }} />
          {t("compare.diff.newErrors")} ({diff.new_errors.length})
        </Space>
      ),
      children: (
        <Space wrap>
          {diff.new_errors.map((err) => (
            <Tag key={err} color="red">
              {err}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      key: "resolvedErrors",
      label: (
        <Space>
          <CheckOutlined style={{ color: "#52c41a" }} />
          {t("compare.diff.resolvedErrors")} ({diff.resolved_errors.length})
        </Space>
      ),
      children: (
        <Space wrap>
          {diff.resolved_errors.map((err) => (
            <Tag key={err} color="green">
              {err}
            </Tag>
          ))}
        </Space>
      ),
    },
  ];

  return (
    <Card title={t("compare.diff.title")}>
      {/* Metrics comparison */}
      <Descriptions bordered size="small" column={3} style={{ marginBottom: 16 }}>
        <Descriptions.Item label={t("compare.metrics.total")}>
          {comparison.metrics_a.total} → {comparison.metrics_b.total}
        </Descriptions.Item>
        <Descriptions.Item label={t("compare.metrics.errors")}>
          {comparison.metrics_a.errors} → {comparison.metrics_b.errors}
        </Descriptions.Item>
        <Descriptions.Item label={t("compare.metrics.accuracy")}>
          {(comparison.metrics_a.accuracy * 100).toFixed(1)}% →{" "}
          {(comparison.metrics_b.accuracy * 100).toFixed(1)}%
        </Descriptions.Item>
      </Descriptions>

      {/* Diff tabs or empty */}
      {hasChanges ? (
        <Tabs items={tabItems} />
      ) : (
        <Empty description={t("compare.diff.noChanges")} />
      )}
    </Card>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx jest src/pages/Compare/components/DiffSummary.test.tsx --no-cache`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Compare/components/DiffSummary.tsx \
       frontend/src/pages/Compare/components/DiffSummary.test.tsx
git commit -m "feat: add DiffSummary component with tabbed diff view"
```

---

### Task 11: Version Compare Page Assembly

**Files:**
- Create: `frontend/src/pages/Compare/index.tsx`
- Create: `frontend/src/pages/Compare/Compare.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/Compare/Compare.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { type ReactNode } from "react";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "compare.title": "版本对比",
        "compare.selectVersionA": "选择版本 A",
        "compare.selectVersionB": "选择版本 B",
        "compare.compare": "对比",
        "compare.noVersions": "请先选择两个版本",
        "compare.radar.title": "能力雷达图",
        "compare.diff.title": "变化摘要",
        "common.error": "加载失败",
        "common.retry": "重试",
      };
      return map[key] ?? key;
    },
  }),
}));

jest.mock("../../api/queries/sessions", () => ({
  useSessions: jest.fn(),
}));

jest.mock("../../api/queries/compare", () => ({
  useVersionComparison: jest.fn(),
  useVersionDiff: jest.fn(),
  useRadarData: jest.fn(),
}));

jest.mock("../../hooks/useGlobalFilters", () => ({
  useGlobalFilters: () => ({
    benchmark: null,
    model_version: null,
    time_range_start: null,
    time_range_end: null,
    setFilter: jest.fn(),
    resetFilters: jest.fn(),
  }),
}));

jest.mock("../../components/EChartsWrapper", () => ({
  __esModule: true,
  default: () => <div data-testid="echarts-mock" />,
}));

import Compare from "./index";
import { useSessions } from "../../api/queries/sessions";
import {
  useVersionComparison,
  useVersionDiff,
  useRadarData,
} from "../../api/queries/compare";

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

describe("Compare Page", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useSessions as jest.Mock).mockReturnValue({
      data: [
        { id: "s1", model_version: "v1.0", benchmark: "mmlu" },
        { id: "s2", model_version: "v2.0", benchmark: "mmlu" },
      ],
      isLoading: false,
    });
    (useVersionComparison as jest.Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });
    (useVersionDiff as jest.Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });
    (useRadarData as jest.Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });
  });

  it("renders version selector and prompt message", () => {
    render(<Compare />, { wrapper: createWrapper() });
    expect(screen.getByText("版本对比")).toBeInTheDocument();
    expect(screen.getByText("请先选择两个版本")).toBeInTheDocument();
  });

  it("shows radar and diff when comparison data is available", () => {
    (useVersionComparison as jest.Mock).mockReturnValue({
      data: {
        version_a: "v1.0",
        version_b: "v2.0",
        benchmark: null,
        metrics_a: { total: 100, errors: 30, accuracy: 0.7, error_type_distribution: {} },
        metrics_b: { total: 100, errors: 20, accuracy: 0.8, error_type_distribution: {} },
      },
      isLoading: false,
    });
    (useVersionDiff as jest.Mock).mockReturnValue({
      data: { regressed: [], improved: [], new_errors: [], resolved_errors: [] },
      isLoading: false,
    });
    (useRadarData as jest.Mock).mockReturnValue({
      data: {
        dimensions: ["math", "logic"],
        scores_a: [0.8, 0.7],
        scores_b: [0.85, 0.75],
      },
      isLoading: false,
    });

    render(<Compare />, { wrapper: createWrapper() });
    expect(screen.getByText("能力雷达图")).toBeInTheDocument();
    expect(screen.getByText("变化摘要")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/pages/Compare/Compare.test.tsx --no-cache`
Expected: FAIL — module `./index` not found

- [ ] **Step 3: Implement the Compare page**

Create `frontend/src/pages/Compare/index.tsx`:

```typescript
import { useState, useCallback, useMemo } from "react";
import { Typography, Space, Row, Col, Empty } from "antd";
import { useTranslation } from "react-i18next";
import { useSessions } from "../../api/queries/sessions";
import {
  useVersionComparison,
  useVersionDiff,
  useRadarData,
} from "../../api/queries/compare";
import VersionSelector from "./components/VersionSelector";
import RadarChart from "./components/RadarChart";
import DiffSummary from "./components/DiffSummary";

const { Title } = Typography;

export default function Compare() {
  const { t } = useTranslation();
  const [versionA, setVersionA] = useState<string | null>(null);
  const [versionB, setVersionB] = useState<string | null>(null);

  // Get available versions from sessions
  const { data: sessions } = useSessions();
  const versions = useMemo(() => {
    if (!sessions) return [];
    const unique = new Set(sessions.map((s) => s.model_version));
    return Array.from(unique).sort();
  }, [sessions]);

  // Fetch comparison data only when both versions are selected
  const { data: comparison, isLoading: compLoading } = useVersionComparison(
    versionA,
    versionB
  );
  const { data: diff, isLoading: diffLoading } = useVersionDiff(
    versionA,
    versionB
  );
  const { data: radarData, isLoading: radarLoading } = useRadarData(
    versionA,
    versionB
  );

  const handleCompare = useCallback(() => {
    // Data fetches automatically via TanStack Query when versions change.
    // This handler exists for explicit "Compare" button UX if needed.
  }, []);

  const hasData = !!comparison;

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Title level={4}>{t("compare.title")}</Title>

      <VersionSelector
        versions={versions}
        versionA={versionA}
        versionB={versionB}
        onVersionAChange={setVersionA}
        onVersionBChange={setVersionB}
        onCompare={handleCompare}
        loading={compLoading}
      />

      {!hasData && !compLoading && (
        <Empty description={t("compare.noVersions")} />
      )}

      {hasData && (
        <>
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={12}>
              <RadarChart
                data={radarData ?? null}
                versionA={versionA!}
                versionB={versionB!}
                loading={radarLoading}
              />
            </Col>
            <Col xs={24} lg={12}>
              <DiffSummary
                comparison={comparison}
                diff={diff ?? null}
                loading={diffLoading}
              />
            </Col>
          </Row>
        </>
      )}
    </Space>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx jest src/pages/Compare/Compare.test.tsx --no-cache`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Compare/index.tsx \
       frontend/src/pages/Compare/Compare.test.tsx
git commit -m "feat: implement Version Compare page with radar and diff"
```

---

### Task 12: Update Router — Replace PlaceholderPage with Real Pages

**Files:**
- Modify: `frontend/src/router.tsx`

- [ ] **Step 1: Update the router**

Replace the PlaceholderPage imports for `/analysis` and `/compare` routes with lazy-loaded real pages in `frontend/src/router.tsx`:

```typescript
import { createBrowserRouter, Navigate } from "react-router-dom";
import { lazy, Suspense } from "react";
import { Spin } from "antd";
import AppLayout from "./layouts/AppLayout";
import Login from "./pages/Login";
import ProtectedRoute from "./components/ProtectedRoute"; // or wherever it's defined
import PlaceholderPage from "./components/PlaceholderPage";

const LazyFallback = () => (
  <div style={{ display: "flex", justifyContent: "center", padding: 48 }}>
    <Spin size="large" />
  </div>
);

const Overview = lazy(() => import("./pages/Overview"));
const Analysis = lazy(() => import("./pages/Analysis"));
const Compare = lazy(() => import("./pages/Compare"));

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <Login />,
  },
  {
    path: "/",
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { index: true, element: <Navigate to="/overview" replace /> },
          {
            path: "overview",
            element: (
              <Suspense fallback={<LazyFallback />}>
                <Overview />
              </Suspense>
            ),
          },
          {
            path: "analysis",
            element: (
              <Suspense fallback={<LazyFallback />}>
                <Analysis />
              </Suspense>
            ),
          },
          {
            path: "compare",
            element: (
              <Suspense fallback={<LazyFallback />}>
                <Compare />
              </Suspense>
            ),
          },
          { path: "cross-benchmark", element: <PlaceholderPage /> },
          { path: "config", element: <PlaceholderPage /> },
        ],
      },
    ],
  },
  { path: "*", element: <Navigate to="/overview" replace /> },
]);
```

- [ ] **Step 2: Run all tests to verify nothing broke**

Run: `cd frontend && npx jest --no-cache`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add frontend/src/router.tsx
git commit -m "feat: wire Analysis and Compare pages into router"
```

---

### Task 13: Integration Smoke Test

**Files:**
- Create: `frontend/src/pages/Analysis/Analysis.integration.test.tsx`
- Create: `frontend/src/pages/Compare/Compare.integration.test.tsx`

- [ ] **Step 1: Write Analysis integration test**

Create `frontend/src/pages/Analysis/Analysis.integration.test.tsx`:

```typescript
/**
 * Integration test: verifies the Analysis page renders without errors
 * when all sub-components are wired together (not mocking child components).
 * API calls are still mocked.
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

jest.mock("../../api/queries/analysis", () => ({
  useErrorDistribution: () => ({
    data: [
      { label: "Format", count: 10, percentage: 50 },
      { label: "Reasoning", count: 10, percentage: 50 },
    ],
    isLoading: false,
    isError: false,
    refetch: jest.fn(),
  }),
  useErrorRecords: () => ({
    data: { items: [], total: 0, page: 1, size: 20 },
    isLoading: false,
    isError: false,
  }),
  useRecordDetail: () => ({
    data: null,
    isLoading: false,
  }),
}));

jest.mock("../../hooks/useGlobalFilters", () => ({
  useGlobalFilters: () => ({
    benchmark: null,
    model_version: null,
    time_range_start: null,
    time_range_end: null,
    setFilter: jest.fn(),
    resetFilters: jest.fn(),
  }),
}));

jest.mock("echarts-for-react", () => ({
  __esModule: true,
  default: () => <div data-testid="echarts" />,
}));

import Analysis from "./index";

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

describe("Analysis Page (integration)", () => {
  it("renders treemap and table without crashing", () => {
    render(<Analysis />, { wrapper: createWrapper() });
    expect(screen.getByText("analysis.title")).toBeInTheDocument();
    expect(screen.getByText("analysis.treemapTitle")).toBeInTheDocument();
    expect(screen.getByText("analysis.recordsTitle")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Write Compare integration test**

Create `frontend/src/pages/Compare/Compare.integration.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { type ReactNode } from "react";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

jest.mock("../../api/queries/sessions", () => ({
  useSessions: () => ({
    data: [
      { id: "s1", model_version: "v1.0", benchmark: "mmlu" },
      { id: "s2", model_version: "v2.0", benchmark: "mmlu" },
    ],
    isLoading: false,
  }),
}));

jest.mock("../../api/queries/compare", () => ({
  useVersionComparison: () => ({ data: null, isLoading: false }),
  useVersionDiff: () => ({ data: null, isLoading: false }),
  useRadarData: () => ({ data: null, isLoading: false }),
}));

jest.mock("../../hooks/useGlobalFilters", () => ({
  useGlobalFilters: () => ({
    benchmark: null,
    model_version: null,
    time_range_start: null,
    time_range_end: null,
    setFilter: jest.fn(),
    resetFilters: jest.fn(),
  }),
}));

import Compare from "./index";

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

describe("Compare Page (integration)", () => {
  it("renders version selector and empty prompt", () => {
    render(<Compare />, { wrapper: createWrapper() });
    expect(screen.getByText("compare.title")).toBeInTheDocument();
    expect(screen.getByText("compare.noVersions")).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run all tests**

Run: `cd frontend && npx jest --no-cache`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Analysis/Analysis.integration.test.tsx \
       frontend/src/pages/Compare/Compare.integration.test.tsx
git commit -m "test: add integration smoke tests for Analysis and Compare pages"
```

---

### Task 14: Manual Annotation in RecordDetail (§9.3 / §13.4)

**Design doc reference:** §9.3 — "re-analyze with LLM, manual annotation" buttons; §13.4 — user corrects error tags, marks `source=manual`, overrides LLM result.

**Files:**
- Create: `frontend/src/api/queries/annotations.ts`
- Modify: `frontend/src/pages/Analysis/components/RecordDetail.tsx`
- Create: `frontend/src/pages/Analysis/components/ManualAnnotationModal.tsx`
- Create: `frontend/src/pages/Analysis/components/ManualAnnotationModal.test.tsx`
- Modify: `frontend/src/locales/zh.json`
- Modify: `frontend/src/locales/en.json`

#### Backend dependency

This task requires a backend endpoint not covered in earlier plans:

```
PATCH /api/v1/analysis/records/{record_id}/tags
Body: { tags: string[], note?: string }   // tag_path list to set as source=manual
```

The endpoint should:
1. Delete existing `error_tags` rows for this record where `source = 'manual'`
2. Insert new `error_tags` rows with `source = 'manual'`, `confidence = 1.0`
3. Return the updated record detail (same shape as `GET /analysis/records/{id}/detail`)

> **Implementor note:** Add this endpoint to `backend/app/api/v1/routers/analysis.py` (Plan 05 scope). It requires `Analyst` role minimum (§11.2).

#### Steps

- [ ] **Step 1: Add i18n keys**

Add to `zh.json`:
```json
{
  "analysis.detail.annotate": "手动标注",
  "analysis.detail.reanalyze": "LLM 重新分析",
  "annotation.title": "手动标注错误标签",
  "annotation.description": "选择正确的错因标签。提交后将覆盖此条记录的现有标签，并标记为 source=manual。",
  "annotation.selectTags": "选择标签",
  "annotation.note": "备注（可选）",
  "annotation.submit": "保存标注",
  "annotation.cancel": "取消",
  "annotation.success": "标注已保存",
  "annotation.error": "保存失败，请重试"
}
```

Add to `en.json`:
```json
{
  "analysis.detail.annotate": "Manual Annotate",
  "analysis.detail.reanalyze": "Re-analyze with LLM",
  "annotation.title": "Manual Error Tag Annotation",
  "annotation.description": "Select the correct error tags. On submit, existing tags for this record will be replaced and marked source=manual.",
  "annotation.selectTags": "Select tags",
  "annotation.note": "Note (optional)",
  "annotation.submit": "Save Annotation",
  "annotation.cancel": "Cancel",
  "annotation.success": "Annotation saved",
  "annotation.error": "Save failed, please retry"
}
```

- [ ] **Step 2: Add TanStack Query mutation hook**

Create `frontend/src/api/queries/annotations.ts`:

```typescript
// frontend/src/api/queries/annotations.ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../client";

interface AnnotatePayload {
  record_id: string;
  tags: string[];       // tag_path strings
  note?: string;
}

interface AnnotateResponse {
  record_id: string;
  saved_tags: string[];
}

export function useAnnotateRecord() {
  const queryClient = useQueryClient();
  return useMutation<AnnotateResponse, Error, AnnotatePayload>({
    mutationFn: ({ record_id, tags, note }) =>
      apiClient
        .patch<AnnotateResponse>(`/analysis/records/${record_id}/tags`, { tags, note })
        .then((r) => r.data),
    onSuccess: (_, { record_id }) => {
      // Invalidate the detail query so RecordDetail re-fetches updated tags
      queryClient.invalidateQueries({ queryKey: ["record-detail", record_id] });
    },
  });
}
```

- [ ] **Step 3: Write failing tests for `ManualAnnotationModal`**

Create `frontend/src/pages/Analysis/components/ManualAnnotationModal.test.tsx`:

```typescript
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ManualAnnotationModal } from "./ManualAnnotationModal";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

jest.mock("../../../api/queries/annotations", () => ({
  useAnnotateRecord: () => ({
    mutate: jest.fn(),
    isPending: false,
  }),
}));

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>
);

const TAXONOMY_TAGS = [
  "格式性错误.空回答",
  "格式性错误.格式不符",
  "推理性错误.逻辑推理.推理链断裂",
];

test("renders modal with tag selector when open", () => {
  render(
    <ManualAnnotationModal
      open={true}
      recordId="r1"
      existingTags={["格式性错误.空回答"]}
      taxonomyTags={TAXONOMY_TAGS}
      onClose={jest.fn()}
    />,
    { wrapper }
  );
  expect(screen.getByText("annotation.title")).toBeInTheDocument();
  expect(screen.getByText("annotation.selectTags")).toBeInTheDocument();
});

test("does not render when closed", () => {
  render(
    <ManualAnnotationModal
      open={false}
      recordId="r1"
      existingTags={[]}
      taxonomyTags={TAXONOMY_TAGS}
      onClose={jest.fn()}
    />,
    { wrapper }
  );
  expect(screen.queryByText("annotation.title")).not.toBeInTheDocument();
});

test("calls onClose when cancel clicked", () => {
  const onClose = jest.fn();
  render(
    <ManualAnnotationModal
      open={true}
      recordId="r1"
      existingTags={[]}
      taxonomyTags={TAXONOMY_TAGS}
      onClose={onClose}
    />,
    { wrapper }
  );
  fireEvent.click(screen.getByText("annotation.cancel"));
  expect(onClose).toHaveBeenCalled();
});
```

- [ ] Run: `npx jest ManualAnnotationModal` → **FAILED**

- [ ] **Step 4: Implement `ManualAnnotationModal.tsx`**

Create `frontend/src/pages/Analysis/components/ManualAnnotationModal.tsx`:

```typescript
// frontend/src/pages/Analysis/components/ManualAnnotationModal.tsx
import React, { useState, useEffect } from "react";
import { Modal, Select, Input, Space, Typography, App } from "antd";
import { useTranslation } from "react-i18next";
import { useAnnotateRecord } from "../../../api/queries/annotations";

interface Props {
  open: boolean;
  recordId: string;
  existingTags: string[];    // current tag_path values (pre-selected)
  taxonomyTags: string[];    // full list from TaxonomyTree (flat paths)
  onClose: () => void;
}

export function ManualAnnotationModal({
  open,
  recordId,
  existingTags,
  taxonomyTags,
  onClose,
}: Props) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [selectedTags, setSelectedTags] = useState<string[]>(existingTags);
  const [note, setNote] = useState("");

  // Reset selections when modal opens for a new record
  useEffect(() => {
    if (open) {
      setSelectedTags(existingTags);
      setNote("");
    }
  }, [open, existingTags]);

  const { mutate, isPending } = useAnnotateRecord();

  const handleSubmit = () => {
    mutate(
      { record_id: recordId, tags: selectedTags, note: note || undefined },
      {
        onSuccess: () => {
          message.success(t("annotation.success"));
          onClose();
        },
        onError: () => {
          message.error(t("annotation.error"));
        },
      }
    );
  };

  const tagOptions = taxonomyTags.map((tag) => ({ label: tag, value: tag }));

  return (
    <Modal
      title={t("annotation.title")}
      open={open}
      onCancel={onClose}
      onOk={handleSubmit}
      okText={t("annotation.submit")}
      cancelText={t("annotation.cancel")}
      confirmLoading={isPending}
      width={560}
      destroyOnClose
    >
      <Space direction="vertical" style={{ width: "100%" }} size="middle">
        <Typography.Text type="secondary">{t("annotation.description")}</Typography.Text>

        <div>
          <Typography.Text strong>{t("annotation.selectTags")}</Typography.Text>
          <Select
            mode="multiple"
            allowClear
            style={{ width: "100%", marginTop: 8 }}
            options={tagOptions}
            value={selectedTags}
            onChange={setSelectedTags}
            optionFilterProp="label"
            placeholder={t("annotation.selectTags")}
          />
        </div>

        <div>
          <Typography.Text strong>{t("annotation.note")}</Typography.Text>
          <Input.TextArea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={3}
            style={{ marginTop: 8 }}
          />
        </div>
      </Space>
    </Modal>
  );
}
```

- [ ] Run: `npx jest ManualAnnotationModal` → **PASSED** (3 tests)

- [ ] **Step 5: Wire buttons into `RecordDetail.tsx`**

Replace the deferred comment block in `RecordDetail.tsx`:

```diff
-      {/* Note: "Re-analyze with LLM" and "Manual Annotate" buttons
-          (spec section 9.3) are deferred to a future plan — they depend
-          on POST /api/v1/llm/trigger and manual annotation endpoints. */}
+      {/* Action buttons — §9.3 */}
+      <Divider />
+      <Space>
+        <Button
+          icon={<EditOutlined />}
+          onClick={() => setAnnotateOpen(true)}
+          disabled={currentUser?.role === "viewer"}
+        >
+          {t("analysis.detail.annotate")}
+        </Button>
+        <Button
+          icon={<SyncOutlined />}
+          onClick={handleReanalyze}
+          loading={reanalyzePending}
+          disabled={currentUser?.role === "viewer"}
+        >
+          {t("analysis.detail.reanalyze")}
+        </Button>
+      </Space>
+
+      <ManualAnnotationModal
+        open={annotateOpen}
+        recordId={record.id}
+        existingTags={error_tags.map((t: any) => t.tag_path)}
+        taxonomyTags={taxonomyTags}
+        onClose={() => setAnnotateOpen(false)}
+      />
```

Add state and handler at top of `RecordDetail` component:

```typescript
const [annotateOpen, setAnnotateOpen] = useState(false);
// taxonomyTags: flat list of all tag paths from the taxonomy tree.
// Fetched once on first open. In MVP, hardcode the 20 known paths from Plan 03.
const taxonomyTags = KNOWN_TAXONOMY_PATHS;  // see constant below

// Re-analyze: send record to LLM Judge queue
const { mutate: triggerLlm, isPending: reanalyzePending } = useMutation({
  mutationFn: () =>
    apiClient.post("/llm/trigger", {
      record_ids: [record.id],
      strategy: "manual",
    }),
});
const handleReanalyze = () => triggerLlm();
```

Add constant above component:

```typescript
// All L2/L3 tag paths from the taxonomy tree (Plan 03 §5.1).
// In a future iteration, fetch dynamically from GET /api/v1/rules/taxonomy.
const KNOWN_TAXONOMY_PATHS = [
  "格式性错误.输出格式不符", "格式性错误.JSON解析失败",
  "格式性错误.空回答", "格式性错误.语言不符", "格式性错误.答案过长截断",
  "提取性错误.代码提取为空", "提取性错误.代码提取不完整",
  "提取性错误.答案提取错误", "提取性错误.提取字段类型不符",
  "知识性错误.事实错误.核心知识点错误", "知识性错误.事实错误.边界知识缺失",
  "知识性错误.事实错误.知识时效性", "知识性错误.概念混淆", "知识性错误.领域知识盲区",
  "推理性错误.逻辑推理.推理链断裂", "推理性错误.逻辑推理.因果推断错误",
  "推理性错误.逻辑推理.缺少关键条件", "推理性错误.数学计算.算术错误",
  "推理性错误.数学计算.公式应用错误", "推理性错误.数学计算.单位量级错误",
  "推理性错误.多步推理退化",
  "理解性错误.题意理解错误", "理解性错误.指令遵循失败",
  "理解性错误.上下文遗漏", "理解性错误.歧义理解偏差",
  "生成质量.幻觉", "生成质量.重复生成", "生成质量.回答不完整", "生成质量.过度对齐",
];
```

- [ ] **Step 6: Run tests**

```bash
cd frontend && npx jest RecordDetail ManualAnnotationModal --no-cache
```
Expected: all tests PASS (existing 4 RecordDetail tests + 3 new ManualAnnotationModal tests = 7)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/api/queries/annotations.ts \
       frontend/src/pages/Analysis/components/ManualAnnotationModal.tsx \
       frontend/src/pages/Analysis/components/ManualAnnotationModal.test.tsx \
       frontend/src/pages/Analysis/components/RecordDetail.tsx \
       frontend/src/locales/zh.json \
       frontend/src/locales/en.json
git commit -m "feat(analysis): add manual annotation modal and re-analyze button to RecordDetail"
```

---

## Backend API Dependencies

This plan consumes these existing backend endpoints (from Plan 05):

| Endpoint | Response Type | Used By |
|----------|--------------|---------|
| `GET /api/v1/analysis/error-distribution?group_by=&error_type=` | `DistributionItem[]` | ErrorTreemap |
| `GET /api/v1/analysis/records?error_type=&page=&size=` | `PaginatedRecords` | ErrorTable |
| `GET /api/v1/analysis/records/{id}/detail` | `RecordDetail` | RecordDetail drawer |
| `GET /api/v1/sessions` | `EvalSession[]` | VersionSelector (extract versions) |
| `GET /api/v1/compare/versions?version_a=&version_b=` | `VersionComparison` | DiffSummary metrics |
| `GET /api/v1/compare/diff?version_a=&version_b=` | `VersionDiff` | DiffSummary tabs |
| `GET /api/v1/compare/radar?version_a=&version_b=` | `RadarData` | RadarChart |
