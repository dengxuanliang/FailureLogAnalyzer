# Cross-Benchmark Analysis Page — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Cross-Benchmark Analysis page (`/cross-benchmark`), replacing its `PlaceholderPage` route from Plan 07. The page shows a heatmap of model version × benchmark error rates, an Agent-generated systemic weakness report, and a cross-benchmark common error pattern analysis panel.

**Architecture:** The page consumes two existing backend endpoints (`GET /api/v1/cross-benchmark/matrix` and `GET /api/v1/cross-benchmark/weakness`) via new TanStack Query hooks. The heatmap is rendered with ECharts. The weakness report and common error patterns are plain text/structured data from the backend (pre-computed by the Report Agent) and rendered with Ant Design Typography and Table. The page reacts to the global benchmark and model_version filters from FilterContext.

**Tech Stack:** React 18, TypeScript 5, Ant Design 5, ECharts 5 (via echarts-for-react), TanStack Query v5, React Router v6

---

## Prerequisites

This plan depends on Plan 07 (Frontend Foundation) being complete. The following are already available:

- **Types** (`frontend/src/types/api.ts`): base types; this plan adds `CrossBenchmarkMatrix`, `MatrixCell`, `WeaknessReport`, `CommonErrorPattern`
- **Components**: `EChartsWrapper` (with `onEvents` prop added in Plan 08), `StatCard`, `FilterBar`, `PlaceholderPage`
- **Hooks**: `useGlobalFilters()`
- **Contexts**: `FilterContext`, `AuthContext`
- **Layout**: `AppLayout` with sidebar nav and FilterBar
- **Router**: route for `/cross-benchmark` (currently rendering `PlaceholderPage`)

## File Structure

```
frontend/src/
  api/queries/
    cross-benchmark.ts          # CREATE — useCrossBenchmarkMatrix, useWeaknessReport hooks
    cross-benchmark.test.ts     # CREATE — tests for the two hooks
  pages/
    CrossBenchmark/
      index.tsx                 # CREATE — page orchestrator
      CrossBenchmark.test.tsx   # CREATE — page-level tests
      CrossBenchmark.integration.test.tsx  # CREATE — integration smoke test
      components/
        HeatmapChart.tsx        # CREATE — model version × benchmark heatmap
        HeatmapChart.test.tsx
        WeaknessReport.tsx      # CREATE — Agent-generated systemic weakness report
        WeaknessReport.test.tsx
        CommonPatternsTable.tsx # CREATE — cross-benchmark common error patterns table
        CommonPatternsTable.test.tsx
  types/
    api.ts                      # MODIFY — add CrossBenchmarkMatrix, MatrixCell,
                                #          WeaknessReport, CommonErrorPattern types
  locales/
    zh.json                     # MODIFY — add cross.* keys
    en.json                     # MODIFY — add cross.* keys
  router.tsx                    # MODIFY — replace PlaceholderPage for /cross-benchmark
```

---

### Task 1: Add TypeScript Types

**Files:**
- Modify: `frontend/src/types/api.ts`

The backend's `GET /api/v1/cross-benchmark/matrix` returns a matrix where rows are model versions and columns are benchmarks. Each cell holds the error rate for that (version, benchmark) combination. `GET /api/v1/cross-benchmark/weakness` returns the Agent-generated report along with structured common error patterns.

- [ ] **Step 1: Add types to `frontend/src/types/api.ts`**

Append the following interfaces (do not remove existing types):

```typescript
// ─── Cross-Benchmark Analysis ─────────────────────────────────────────────

export interface MatrixCell {
  model_version: string;
  benchmark: string;
  error_rate: number;        // 0.0 – 1.0
  error_count: number;
  total_count: number;
}

export interface CrossBenchmarkMatrix {
  model_versions: string[];  // ordered list — rows
  benchmarks: string[];      // ordered list — columns
  cells: MatrixCell[];       // flat list; locate by (model_version, benchmark)
}

export interface CommonErrorPattern {
  error_type: string;        // L1 or L2 tag path
  affected_benchmarks: string[];
  avg_error_rate: number;    // average error rate across affected benchmarks
  record_count: number;      // total records with this tag across benchmarks
}

export interface WeaknessReport {
  generated_at: string;      // ISO 8601 timestamp
  summary: string;           // Agent-generated narrative (markdown)
  common_patterns: CommonErrorPattern[];
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/api.ts
git commit -m "feat: add CrossBenchmarkMatrix and WeaknessReport types"
```

---

### Task 2: Add i18n Translation Keys

**Files:**
- Modify: `frontend/src/locales/zh.json`
- Modify: `frontend/src/locales/en.json`

- [ ] **Step 1: Add Chinese translation keys**

Add the following keys to `frontend/src/locales/zh.json`:

```json
{
  "cross.title": "Benchmark 横向分析",
  "cross.heatmap.title": "模型版本 × Benchmark 错误率热力图",
  "cross.heatmap.xAxisLabel": "Benchmark",
  "cross.heatmap.yAxisLabel": "模型版本",
  "cross.heatmap.tooltip": "错误率",
  "cross.heatmap.noData": "暂无跨 Benchmark 数据",
  "cross.heatmap.loading": "加载热力图中…",
  "cross.weakness.title": "系统性弱点识别报告",
  "cross.weakness.generatedAt": "生成时间",
  "cross.weakness.noReport": "暂无分析报告，请先完成多个 Benchmark 的评测分析",
  "cross.patterns.title": "跨 Benchmark 共性错误模式",
  "cross.patterns.columns.errorType": "错误类型",
  "cross.patterns.columns.benchmarks": "涉及 Benchmark",
  "cross.patterns.columns.avgErrorRate": "平均错误率",
  "cross.patterns.columns.recordCount": "涉及题数",
  "cross.patterns.noData": "暂无共性错误模式数据"
}
```

- [ ] **Step 2: Add English translation keys**

Add the corresponding keys to `frontend/src/locales/en.json`:

```json
{
  "cross.title": "Cross-Benchmark Analysis",
  "cross.heatmap.title": "Model Version × Benchmark Error Rate Heatmap",
  "cross.heatmap.xAxisLabel": "Benchmark",
  "cross.heatmap.yAxisLabel": "Model Version",
  "cross.heatmap.tooltip": "Error Rate",
  "cross.heatmap.noData": "No cross-benchmark data available",
  "cross.heatmap.loading": "Loading heatmap…",
  "cross.weakness.title": "Systemic Weakness Report",
  "cross.weakness.generatedAt": "Generated at",
  "cross.weakness.noReport": "No report available — complete analysis across multiple benchmarks first",
  "cross.patterns.title": "Common Error Patterns Across Benchmarks",
  "cross.patterns.columns.errorType": "Error Type",
  "cross.patterns.columns.benchmarks": "Affected Benchmarks",
  "cross.patterns.columns.avgErrorRate": "Avg Error Rate",
  "cross.patterns.columns.recordCount": "Record Count",
  "cross.patterns.noData": "No common error pattern data available"
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/locales/zh.json frontend/src/locales/en.json
git commit -m "feat: add i18n keys for cross-benchmark analysis page"
```

---

### Task 3: TanStack Query Hooks — Cross-Benchmark

**Files:**
- Create: `frontend/src/api/queries/cross-benchmark.ts`
- Create: `frontend/src/api/queries/cross-benchmark.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/api/queries/cross-benchmark.test.ts`:

```typescript
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { FilterProvider } from "../../contexts/FilterContext";
import {
  useCrossBenchmarkMatrix,
  useWeaknessReport,
} from "./cross-benchmark";

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

describe("useCrossBenchmarkMatrix", () => {
  beforeEach(() => jest.clearAllMocks());

  it("fetches the matrix", async () => {
    const mockMatrix = {
      model_versions: ["v1.0", "v2.0"],
      benchmarks: ["mmlu", "gsm8k"],
      cells: [
        { model_version: "v1.0", benchmark: "mmlu", error_rate: 0.3, error_count: 30, total_count: 100 },
        { model_version: "v1.0", benchmark: "gsm8k", error_rate: 0.5, error_count: 50, total_count: 100 },
        { model_version: "v2.0", benchmark: "mmlu", error_rate: 0.2, error_count: 20, total_count: 100 },
        { model_version: "v2.0", benchmark: "gsm8k", error_rate: 0.4, error_count: 40, total_count: 100 },
      ],
    };
    mockedGet.mockResolvedValueOnce({ data: mockMatrix });

    const { result } = renderHook(() => useCrossBenchmarkMatrix(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockMatrix);
    expect(mockedGet).toHaveBeenCalledWith(
      "/cross-benchmark/matrix",
      expect.objectContaining({ params: expect.any(Object) })
    );
  });

  it("passes model_version filter when set in global filters", async () => {
    mockedGet.mockResolvedValueOnce({
      data: { model_versions: [], benchmarks: [], cells: [] },
    });

    // FilterProvider defaults: no filters set — just verify the call shape
    const { result } = renderHook(() => useCrossBenchmarkMatrix(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    // model_version is null by default, so it should NOT be in params
    const callArgs = mockedGet.mock.calls[0];
    expect(callArgs[1].params).not.toHaveProperty("model_version");
  });
});

describe("useWeaknessReport", () => {
  beforeEach(() => jest.clearAllMocks());

  it("fetches the weakness report", async () => {
    const mockReport = {
      generated_at: "2026-03-20T10:00:00Z",
      summary: "## 系统性弱点\n\n模型在数学推理方面存在普遍弱点。",
      common_patterns: [
        {
          error_type: "推理性错误.数学/计算错误",
          affected_benchmarks: ["mmlu", "gsm8k"],
          avg_error_rate: 0.45,
          record_count: 230,
        },
      ],
    };
    mockedGet.mockResolvedValueOnce({ data: mockReport });

    const { result } = renderHook(() => useWeaknessReport(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockReport);
    expect(mockedGet).toHaveBeenCalledWith(
      "/cross-benchmark/weakness",
      expect.objectContaining({ params: expect.any(Object) })
    );
  });

  it("returns null data gracefully when backend has no report", async () => {
    mockedGet.mockResolvedValueOnce({ data: null });

    const { result } = renderHook(() => useWeaknessReport(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx jest src/api/queries/cross-benchmark.test.ts --no-cache`
Expected: FAIL — module `./cross-benchmark` not found

- [ ] **Step 3: Implement the hooks**

Create `frontend/src/api/queries/cross-benchmark.ts`:

```typescript
import { useQuery } from "@tanstack/react-query";
import apiClient from "../client";
import { useGlobalFilters } from "../../hooks/useGlobalFilters";
import type { CrossBenchmarkMatrix, WeaknessReport } from "../../types/api";

export function useCrossBenchmarkMatrix() {
  const { benchmark, model_version } = useGlobalFilters();

  return useQuery<CrossBenchmarkMatrix>({
    queryKey: ["crossBenchmarkMatrix", benchmark, model_version],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (benchmark) params.benchmark = benchmark;
      if (model_version) params.model_version = model_version;
      const { data } = await apiClient.get("/cross-benchmark/matrix", {
        params,
      });
      return data;
    },
  });
}

export function useWeaknessReport() {
  const { benchmark, model_version } = useGlobalFilters();

  return useQuery<WeaknessReport | null>({
    queryKey: ["weaknessReport", benchmark, model_version],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (benchmark) params.benchmark = benchmark;
      if (model_version) params.model_version = model_version;
      const { data } = await apiClient.get("/cross-benchmark/weakness", {
        params,
      });
      return data;
    },
  });
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx jest src/api/queries/cross-benchmark.test.ts --no-cache`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/queries/cross-benchmark.ts \
        frontend/src/api/queries/cross-benchmark.test.ts
git commit -m "feat: add useCrossBenchmarkMatrix and useWeaknessReport query hooks"
```

---

### Task 4: HeatmapChart Component

**Files:**
- Create: `frontend/src/pages/CrossBenchmark/components/HeatmapChart.tsx`
- Create: `frontend/src/pages/CrossBenchmark/components/HeatmapChart.test.tsx`

The heatmap encodes error rate as color intensity (white → red). Rows are model versions (Y axis), columns are benchmarks (X axis). Clicking a cell filters the global benchmark or model_version — but for v1 we just emit an `onCellClick` callback and leave wiring to the page.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/CrossBenchmark/components/HeatmapChart.test.tsx`:

```typescript
import { render, screen, fireEvent } from "@testing-library/react";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "cross.heatmap.title": "模型版本 × Benchmark 错误率热力图",
        "cross.heatmap.xAxisLabel": "Benchmark",
        "cross.heatmap.yAxisLabel": "模型版本",
        "cross.heatmap.tooltip": "错误率",
        "cross.heatmap.noData": "暂无跨 Benchmark 数据",
      };
      return map[key] ?? key;
    },
  }),
}));

jest.mock("../../../components/EChartsWrapper", () => ({
  __esModule: true,
  default: ({ option, onEvents }: any) => (
    <div
      data-testid="echarts-mock"
      data-xaxis={JSON.stringify(option.xAxis?.data)}
      data-yaxis={JSON.stringify(option.yAxis?.data)}
      onClick={() => {
        if (onEvents?.click) {
          onEvents.click({ value: [0, 0, 0.3] });
        }
      }}
    />
  ),
}));

import HeatmapChart from "./HeatmapChart";
import type { CrossBenchmarkMatrix } from "../../../types/api";

const mockMatrix: CrossBenchmarkMatrix = {
  model_versions: ["v1.0", "v2.0"],
  benchmarks: ["mmlu", "gsm8k"],
  cells: [
    { model_version: "v1.0", benchmark: "mmlu", error_rate: 0.3, error_count: 30, total_count: 100 },
    { model_version: "v1.0", benchmark: "gsm8k", error_rate: 0.5, error_count: 50, total_count: 100 },
    { model_version: "v2.0", benchmark: "mmlu", error_rate: 0.2, error_count: 20, total_count: 100 },
    { model_version: "v2.0", benchmark: "gsm8k", error_rate: 0.4, error_count: 40, total_count: 100 },
  ],
};

describe("HeatmapChart", () => {
  it("renders card title", () => {
    render(
      <HeatmapChart
        matrix={mockMatrix}
        loading={false}
        onCellClick={jest.fn()}
      />
    );
    expect(
      screen.getByText("模型版本 × Benchmark 错误率热力图")
    ).toBeInTheDocument();
  });

  it("passes benchmarks as x-axis data and model versions as y-axis data", () => {
    render(
      <HeatmapChart
        matrix={mockMatrix}
        loading={false}
        onCellClick={jest.fn()}
      />
    );
    const chart = screen.getByTestId("echarts-mock");
    const xAxis = JSON.parse(chart.getAttribute("data-xaxis") ?? "[]");
    const yAxis = JSON.parse(chart.getAttribute("data-yaxis") ?? "[]");
    expect(xAxis).toEqual(["mmlu", "gsm8k"]);
    expect(yAxis).toEqual(["v1.0", "v2.0"]);
  });

  it("calls onCellClick when a heatmap cell is clicked", () => {
    const onCellClick = jest.fn();
    render(
      <HeatmapChart
        matrix={mockMatrix}
        loading={false}
        onCellClick={onCellClick}
      />
    );
    fireEvent.click(screen.getByTestId("echarts-mock"));
    expect(onCellClick).toHaveBeenCalledWith({
      model_version: "v1.0",
      benchmark: "mmlu",
      error_rate: 0.3,
    });
  });

  it("shows empty state when matrix has no cells", () => {
    render(
      <HeatmapChart
        matrix={{ model_versions: [], benchmarks: [], cells: [] }}
        loading={false}
        onCellClick={jest.fn()}
      />
    );
    expect(screen.getByText("暂无跨 Benchmark 数据")).toBeInTheDocument();
  });

  it("shows skeleton when loading", () => {
    const { container } = render(
      <HeatmapChart
        matrix={null}
        loading={true}
        onCellClick={jest.fn()}
      />
    );
    expect(container.querySelector(".ant-skeleton")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/pages/CrossBenchmark/components/HeatmapChart.test.tsx --no-cache`
Expected: FAIL — module `./HeatmapChart` not found

- [ ] **Step 3: Implement HeatmapChart**

Create `frontend/src/pages/CrossBenchmark/components/HeatmapChart.tsx`:

```typescript
import { Card, Skeleton, Empty } from "antd";
import { useTranslation } from "react-i18next";
import EChartsWrapper from "../../../components/EChartsWrapper";
import type { CrossBenchmarkMatrix } from "../../../types/api";

interface CellClickPayload {
  model_version: string;
  benchmark: string;
  error_rate: number;
}

interface HeatmapChartProps {
  matrix: CrossBenchmarkMatrix | null;
  loading: boolean;
  onCellClick: (payload: CellClickPayload) => void;
}

export default function HeatmapChart({
  matrix,
  loading,
  onCellClick,
}: HeatmapChartProps) {
  const { t } = useTranslation();

  if (loading || !matrix) {
    return (
      <Card title={t("cross.heatmap.title")}>
        <Skeleton active paragraph={{ rows: 8 }} />
      </Card>
    );
  }

  const { model_versions, benchmarks, cells } = matrix;

  if (cells.length === 0) {
    return (
      <Card title={t("cross.heatmap.title")}>
        <Empty description={t("cross.heatmap.noData")} />
      </Card>
    );
  }

  // Build [benchmarkIndex, versionIndex, errorRate] tuples for ECharts heatmap
  const seriesData = cells.map((cell) => [
    benchmarks.indexOf(cell.benchmark),
    model_versions.indexOf(cell.model_version),
    cell.error_rate,
  ]);

  const option = {
    tooltip: {
      formatter: (params: any) => {
        const [bIdx, vIdx, rate] = params.value;
        return [
          `${t("cross.heatmap.yAxisLabel")}: ${model_versions[vIdx]}`,
          `${t("cross.heatmap.xAxisLabel")}: ${benchmarks[bIdx]}`,
          `${t("cross.heatmap.tooltip")}: ${(rate * 100).toFixed(1)}%`,
        ].join("<br/>");
      },
    },
    grid: { top: "10%", bottom: "15%", left: "15%", right: "5%" },
    xAxis: {
      type: "category",
      data: benchmarks,
      name: t("cross.heatmap.xAxisLabel"),
      axisLabel: { rotate: 30 },
    },
    yAxis: {
      type: "category",
      data: model_versions,
      name: t("cross.heatmap.yAxisLabel"),
    },
    visualMap: {
      min: 0,
      max: 1,
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      inRange: {
        color: ["#fff5f0", "#fc8d59", "#d73027"],
      },
    },
    series: [
      {
        type: "heatmap",
        data: seriesData,
        label: {
          show: true,
          formatter: (params: any) =>
            `${(params.value[2] * 100).toFixed(0)}%`,
          fontSize: 12,
        },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: "rgba(0,0,0,0.5)" },
        },
      },
    ],
  };

  const handleCellClick = (params: any) => {
    const [bIdx, vIdx, error_rate] = params.value;
    onCellClick({
      model_version: model_versions[vIdx],
      benchmark: benchmarks[bIdx],
      error_rate,
    });
  };

  return (
    <Card title={t("cross.heatmap.title")}>
      <EChartsWrapper
        option={option}
        height={Math.max(300, model_versions.length * 60 + 80)}
        onEvents={{ click: handleCellClick }}
      />
    </Card>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx jest src/pages/CrossBenchmark/components/HeatmapChart.test.tsx --no-cache`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/CrossBenchmark/components/HeatmapChart.tsx \
        frontend/src/pages/CrossBenchmark/components/HeatmapChart.test.tsx
git commit -m "feat: add HeatmapChart component for cross-benchmark error rate matrix"
```

---

### Task 5: WeaknessReport Component

**Files:**
- Create: `frontend/src/pages/CrossBenchmark/components/WeaknessReport.tsx`
- Create: `frontend/src/pages/CrossBenchmark/components/WeaknessReport.test.tsx`

This component renders the Agent-generated narrative as Markdown (via Ant Design `Typography.Paragraph`; we use a simple pre-wrap rendering to avoid adding a markdown library dependency) and a timestamp.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/CrossBenchmark/components/WeaknessReport.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "cross.weakness.title": "系统性弱点识别报告",
        "cross.weakness.generatedAt": "生成时间",
        "cross.weakness.noReport": "暂无分析报告，请先完成多个 Benchmark 的评测分析",
      };
      return map[key] ?? key;
    },
  }),
}));

import WeaknessReport from "./WeaknessReport";
import type { WeaknessReport as WeaknessReportType } from "../../../types/api";

const mockReport: WeaknessReportType = {
  generated_at: "2026-03-20T10:00:00Z",
  summary: "## 系统性弱点\n\n模型在数学推理方面存在普遍弱点。\n\n建议增加数学训练数据。",
  common_patterns: [],
};

describe("WeaknessReport", () => {
  it("renders the card title", () => {
    render(<WeaknessReport report={mockReport} loading={false} />);
    expect(screen.getByText("系统性弱点识别报告")).toBeInTheDocument();
  });

  it("renders generated_at timestamp", () => {
    render(<WeaknessReport report={mockReport} loading={false} />);
    expect(screen.getByText("生成时间")).toBeInTheDocument();
    // Timestamp is formatted — just verify the label is present
  });

  it("renders the summary text", () => {
    render(<WeaknessReport report={mockReport} loading={false} />);
    // Summary is rendered as pre-wrapped text; check part of it
    expect(
      screen.getByText(/模型在数学推理方面存在普遍弱点/)
    ).toBeInTheDocument();
  });

  it("shows empty state when report is null", () => {
    render(<WeaknessReport report={null} loading={false} />);
    expect(
      screen.getByText("暂无分析报告，请先完成多个 Benchmark 的评测分析")
    ).toBeInTheDocument();
  });

  it("shows skeleton when loading", () => {
    const { container } = render(
      <WeaknessReport report={null} loading={true} />
    );
    expect(container.querySelector(".ant-skeleton")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/pages/CrossBenchmark/components/WeaknessReport.test.tsx --no-cache`
Expected: FAIL — module `./WeaknessReport` not found

- [ ] **Step 3: Implement WeaknessReport**

Create `frontend/src/pages/CrossBenchmark/components/WeaknessReport.tsx`:

```typescript
import { Card, Skeleton, Empty, Descriptions, Typography } from "antd";
import { useTranslation } from "react-i18next";
import type { WeaknessReport as WeaknessReportType } from "../../../types/api";

const { Text } = Typography;

interface WeaknessReportProps {
  report: WeaknessReportType | null | undefined;
  loading: boolean;
}

export default function WeaknessReport({
  report,
  loading,
}: WeaknessReportProps) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <Card title={t("cross.weakness.title")}>
        <Skeleton active paragraph={{ rows: 6 }} />
      </Card>
    );
  }

  if (!report) {
    return (
      <Card title={t("cross.weakness.title")}>
        <Empty description={t("cross.weakness.noReport")} />
      </Card>
    );
  }

  const formattedDate = new Date(report.generated_at).toLocaleString();

  return (
    <Card title={t("cross.weakness.title")}>
      <Descriptions size="small" style={{ marginBottom: 16 }}>
        <Descriptions.Item label={t("cross.weakness.generatedAt")}>
          <Text type="secondary">{formattedDate}</Text>
        </Descriptions.Item>
      </Descriptions>
      {/* Render Agent-generated markdown as pre-formatted text.
          A markdown renderer can be swapped in later without changing the
          interface — just replace the <pre> with a Markdown component. */}
      <pre
        style={{
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          fontFamily: "inherit",
          margin: 0,
          fontSize: 14,
          lineHeight: 1.7,
        }}
      >
        {report.summary}
      </pre>
    </Card>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx jest src/pages/CrossBenchmark/components/WeaknessReport.test.tsx --no-cache`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/CrossBenchmark/components/WeaknessReport.tsx \
        frontend/src/pages/CrossBenchmark/components/WeaknessReport.test.tsx
git commit -m "feat: add WeaknessReport component for systemic weakness narrative"
```

---

### Task 6: CommonPatternsTable Component

**Files:**
- Create: `frontend/src/pages/CrossBenchmark/components/CommonPatternsTable.tsx`
- Create: `frontend/src/pages/CrossBenchmark/components/CommonPatternsTable.test.tsx`

This table is derived from `WeaknessReport.common_patterns`. It shows which error types appear across the most benchmarks and with the highest average error rate, helping teams identify the most impactful systemic issues.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/CrossBenchmark/components/CommonPatternsTable.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "cross.patterns.title": "跨 Benchmark 共性错误模式",
        "cross.patterns.columns.errorType": "错误类型",
        "cross.patterns.columns.benchmarks": "涉及 Benchmark",
        "cross.patterns.columns.avgErrorRate": "平均错误率",
        "cross.patterns.columns.recordCount": "涉及题数",
        "cross.patterns.noData": "暂无共性错误模式数据",
      };
      return map[key] ?? key;
    },
  }),
}));

import CommonPatternsTable from "./CommonPatternsTable";
import type { CommonErrorPattern } from "../../../types/api";

const mockPatterns: CommonErrorPattern[] = [
  {
    error_type: "推理性错误.数学/计算错误",
    affected_benchmarks: ["mmlu", "gsm8k", "math"],
    avg_error_rate: 0.45,
    record_count: 230,
  },
  {
    error_type: "格式与规范错误.输出格式不符",
    affected_benchmarks: ["humaneval", "mbpp"],
    avg_error_rate: 0.28,
    record_count: 110,
  },
];

describe("CommonPatternsTable", () => {
  it("renders the card title", () => {
    render(
      <CommonPatternsTable patterns={mockPatterns} loading={false} />
    );
    expect(screen.getByText("跨 Benchmark 共性错误模式")).toBeInTheDocument();
  });

  it("renders column headers", () => {
    render(
      <CommonPatternsTable patterns={mockPatterns} loading={false} />
    );
    expect(screen.getByText("错误类型")).toBeInTheDocument();
    expect(screen.getByText("涉及 Benchmark")).toBeInTheDocument();
    expect(screen.getByText("平均错误率")).toBeInTheDocument();
    expect(screen.getByText("涉及题数")).toBeInTheDocument();
  });

  it("renders error type values", () => {
    render(
      <CommonPatternsTable patterns={mockPatterns} loading={false} />
    );
    expect(
      screen.getByText("推理性错误.数学/计算错误")
    ).toBeInTheDocument();
    expect(
      screen.getByText("格式与规范错误.输出格式不符")
    ).toBeInTheDocument();
  });

  it("renders affected benchmarks as tags", () => {
    render(
      <CommonPatternsTable patterns={mockPatterns} loading={false} />
    );
    expect(screen.getByText("mmlu")).toBeInTheDocument();
    expect(screen.getByText("gsm8k")).toBeInTheDocument();
    expect(screen.getByText("humaneval")).toBeInTheDocument();
  });

  it("renders formatted average error rates", () => {
    render(
      <CommonPatternsTable patterns={mockPatterns} loading={false} />
    );
    // 0.45 → "45.0%"
    expect(screen.getByText("45.0%")).toBeInTheDocument();
    // 0.28 → "28.0%"
    expect(screen.getByText("28.0%")).toBeInTheDocument();
  });

  it("shows empty state when patterns list is empty", () => {
    render(<CommonPatternsTable patterns={[]} loading={false} />);
    expect(screen.getByText("暂无共性错误模式数据")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/pages/CrossBenchmark/components/CommonPatternsTable.test.tsx --no-cache`
Expected: FAIL — module `./CommonPatternsTable` not found

- [ ] **Step 3: Implement CommonPatternsTable**

Create `frontend/src/pages/CrossBenchmark/components/CommonPatternsTable.tsx`:

```typescript
import { Card, Table, Tag, Space, Empty } from "antd";
import { useTranslation } from "react-i18next";
import type { ColumnsType } from "antd/es/table";
import type { CommonErrorPattern } from "../../../types/api";

interface CommonPatternsTableProps {
  patterns: CommonErrorPattern[];
  loading: boolean;
}

export default function CommonPatternsTable({
  patterns,
  loading,
}: CommonPatternsTableProps) {
  const { t } = useTranslation();

  const columns: ColumnsType<CommonErrorPattern> = [
    {
      title: t("cross.patterns.columns.errorType"),
      dataIndex: "error_type",
      key: "error_type",
      ellipsis: true,
    },
    {
      title: t("cross.patterns.columns.benchmarks"),
      dataIndex: "affected_benchmarks",
      key: "affected_benchmarks",
      render: (benchmarks: string[]) => (
        <Space size={[4, 4]} wrap>
          {benchmarks.map((b) => (
            <Tag key={b} color="blue">
              {b}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: t("cross.patterns.columns.avgErrorRate"),
      dataIndex: "avg_error_rate",
      key: "avg_error_rate",
      width: 130,
      align: "right",
      sorter: (a, b) => a.avg_error_rate - b.avg_error_rate,
      defaultSortOrder: "descend",
      render: (rate: number) => `${(rate * 100).toFixed(1)}%`,
    },
    {
      title: t("cross.patterns.columns.recordCount"),
      dataIndex: "record_count",
      key: "record_count",
      width: 110,
      align: "right",
      sorter: (a, b) => a.record_count - b.record_count,
    },
  ];

  return (
    <Card title={t("cross.patterns.title")}>
      {patterns.length === 0 && !loading ? (
        <Empty description={t("cross.patterns.noData")} />
      ) : (
        <Table<CommonErrorPattern>
          columns={columns}
          dataSource={patterns}
          rowKey="error_type"
          loading={loading}
          size="small"
          pagination={{ pageSize: 10, hideOnSinglePage: true }}
        />
      )}
    </Card>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx jest src/pages/CrossBenchmark/components/CommonPatternsTable.test.tsx --no-cache`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/CrossBenchmark/components/CommonPatternsTable.tsx \
        frontend/src/pages/CrossBenchmark/components/CommonPatternsTable.test.tsx
git commit -m "feat: add CommonPatternsTable component for shared error patterns"
```

---

### Task 7: CrossBenchmark Page Assembly

**Files:**
- Create: `frontend/src/pages/CrossBenchmark/index.tsx`
- Create: `frontend/src/pages/CrossBenchmark/CrossBenchmark.test.tsx`

The page wires together the three child components. Clicking a heatmap cell sets the global `benchmark` and `model_version` filters via `useGlobalFilters().setFilter`, which causes all query hooks (including those on other pages) to refetch filtered data. This gives users a drill-down path: spot a hot cell in the heatmap → click it → other pages update.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/CrossBenchmark/CrossBenchmark.test.tsx`:

```typescript
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { type ReactNode } from "react";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "cross.title": "Benchmark 横向分析",
        "cross.heatmap.title": "模型版本 × Benchmark 错误率热力图",
        "cross.weakness.title": "系统性弱点识别报告",
        "cross.patterns.title": "跨 Benchmark 共性错误模式",
        "cross.heatmap.noData": "暂无跨 Benchmark 数据",
        "cross.weakness.noReport": "暂无分析报告，请先完成多个 Benchmark 的评测分析",
        "cross.patterns.noData": "暂无共性错误模式数据",
        "cross.heatmap.xAxisLabel": "Benchmark",
        "cross.heatmap.yAxisLabel": "模型版本",
        "cross.heatmap.tooltip": "错误率",
      };
      return map[key] ?? key;
    },
  }),
}));

jest.mock("../../api/queries/cross-benchmark", () => ({
  useCrossBenchmarkMatrix: jest.fn(),
  useWeaknessReport: jest.fn(),
}));

const mockSetFilter = jest.fn();
jest.mock("../../hooks/useGlobalFilters", () => ({
  useGlobalFilters: () => ({
    benchmark: null,
    model_version: null,
    time_range_start: null,
    time_range_end: null,
    setFilter: mockSetFilter,
    resetFilters: jest.fn(),
  }),
}));

jest.mock("../../components/EChartsWrapper", () => ({
  __esModule: true,
  default: ({ onEvents }: any) => (
    <div
      data-testid="echarts-mock"
      onClick={() => {
        if (onEvents?.click) {
          onEvents.click({ value: [0, 0, 0.3] });
        }
      }}
    />
  ),
}));

import CrossBenchmark from "./index";
import {
  useCrossBenchmarkMatrix,
  useWeaknessReport,
} from "../../api/queries/cross-benchmark";

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

describe("CrossBenchmark Page", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useCrossBenchmarkMatrix as jest.Mock).mockReturnValue({
      data: null,
      isLoading: false,
      isError: false,
    });
    (useWeaknessReport as jest.Mock).mockReturnValue({
      data: null,
      isLoading: false,
      isError: false,
    });
  });

  it("renders page title", () => {
    render(<CrossBenchmark />, { wrapper: createWrapper() });
    expect(screen.getByText("Benchmark 横向分析")).toBeInTheDocument();
  });

  it("renders all three section titles", () => {
    render(<CrossBenchmark />, { wrapper: createWrapper() });
    expect(
      screen.getByText("模型版本 × Benchmark 错误率热力图")
    ).toBeInTheDocument();
    expect(screen.getByText("系统性弱点识别报告")).toBeInTheDocument();
    expect(screen.getByText("跨 Benchmark 共性错误模式")).toBeInTheDocument();
  });

  it("renders heatmap when matrix data is available", () => {
    (useCrossBenchmarkMatrix as jest.Mock).mockReturnValue({
      data: {
        model_versions: ["v1.0", "v2.0"],
        benchmarks: ["mmlu", "gsm8k"],
        cells: [
          { model_version: "v1.0", benchmark: "mmlu", error_rate: 0.3, error_count: 30, total_count: 100 },
        ],
      },
      isLoading: false,
      isError: false,
    });

    render(<CrossBenchmark />, { wrapper: createWrapper() });
    expect(screen.getByTestId("echarts-mock")).toBeInTheDocument();
  });

  it("calls setFilter with benchmark and model_version when heatmap cell is clicked", () => {
    (useCrossBenchmarkMatrix as jest.Mock).mockReturnValue({
      data: {
        model_versions: ["v1.0", "v2.0"],
        benchmarks: ["mmlu", "gsm8k"],
        cells: [
          { model_version: "v1.0", benchmark: "mmlu", error_rate: 0.3, error_count: 30, total_count: 100 },
        ],
      },
      isLoading: false,
      isError: false,
    });

    render(<CrossBenchmark />, { wrapper: createWrapper() });
    fireEvent.click(screen.getByTestId("echarts-mock"));
    expect(mockSetFilter).toHaveBeenCalledWith("benchmark", "mmlu");
    expect(mockSetFilter).toHaveBeenCalledWith("model_version", "v1.0");
  });

  it("renders weakness report when data is available", () => {
    (useWeaknessReport as jest.Mock).mockReturnValue({
      data: {
        generated_at: "2026-03-20T10:00:00Z",
        summary: "模型存在系统性弱点。",
        common_patterns: [],
      },
      isLoading: false,
      isError: false,
    });

    render(<CrossBenchmark />, { wrapper: createWrapper() });
    expect(screen.getByText(/模型存在系统性弱点/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/pages/CrossBenchmark/CrossBenchmark.test.tsx --no-cache`
Expected: FAIL — module `./index` not found

- [ ] **Step 3: Implement the CrossBenchmark page**

Create `frontend/src/pages/CrossBenchmark/index.tsx`:

```typescript
import { useCallback } from "react";
import { Typography, Space, Alert, Button } from "antd";
import { useTranslation } from "react-i18next";
import {
  useCrossBenchmarkMatrix,
  useWeaknessReport,
} from "../../api/queries/cross-benchmark";
import { useGlobalFilters } from "../../hooks/useGlobalFilters";
import HeatmapChart from "./components/HeatmapChart";
import WeaknessReport from "./components/WeaknessReport";
import CommonPatternsTable from "./components/CommonPatternsTable";

const { Title } = Typography;

export default function CrossBenchmark() {
  const { t } = useTranslation();
  const { setFilter } = useGlobalFilters();

  const {
    data: matrix,
    isLoading: matrixLoading,
    isError: matrixError,
    refetch: refetchMatrix,
  } = useCrossBenchmarkMatrix();

  const {
    data: report,
    isLoading: reportLoading,
    isError: reportError,
    refetch: refetchReport,
  } = useWeaknessReport();

  const handleCellClick = useCallback(
    ({
      model_version,
      benchmark,
    }: {
      model_version: string;
      benchmark: string;
      error_rate: number;
    }) => {
      // Update global filters so all other pages reflect this selection
      setFilter("benchmark", benchmark);
      setFilter("model_version", model_version);
    },
    [setFilter]
  );

  if (matrixError || reportError) {
    return (
      <Alert
        type="error"
        message={t("common.error")}
        action={
          <Button
            size="small"
            onClick={() => {
              if (matrixError) refetchMatrix();
              if (reportError) refetchReport();
            }}
          >
            {t("common.retry")}
          </Button>
        }
      />
    );
  }

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Title level={4}>{t("cross.title")}</Title>

      <HeatmapChart
        matrix={matrix ?? null}
        loading={matrixLoading}
        onCellClick={handleCellClick}
      />

      <WeaknessReport
        report={report ?? null}
        loading={reportLoading}
      />

      <CommonPatternsTable
        patterns={report?.common_patterns ?? []}
        loading={reportLoading}
      />
    </Space>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx jest src/pages/CrossBenchmark/CrossBenchmark.test.tsx --no-cache`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/CrossBenchmark/index.tsx \
        frontend/src/pages/CrossBenchmark/CrossBenchmark.test.tsx
git commit -m "feat: implement CrossBenchmark page with heatmap, weakness report, and patterns"
```

---

### Task 8: Update Router — Wire /cross-benchmark Route

**Files:**
- Modify: `frontend/src/router.tsx`

- [ ] **Step 1: Update the router**

Add a lazy import for `CrossBenchmark` and replace the `PlaceholderPage` at `/cross-benchmark`. The diff from Plan 08's router is:

```typescript
// Add this lazy import alongside Analysis and Compare:
const CrossBenchmark = lazy(() => import("./pages/CrossBenchmark"));

// Replace:
{ path: "cross-benchmark", element: <PlaceholderPage /> },

// With:
{
  path: "cross-benchmark",
  element: (
    <Suspense fallback={<LazyFallback />}>
      <CrossBenchmark />
    </Suspense>
  ),
},
```

- [ ] **Step 2: Run all tests to verify nothing broke**

Run: `cd frontend && npx jest --no-cache`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add frontend/src/router.tsx
git commit -m "feat: wire CrossBenchmark page into router"
```

---

### Task 9: Integration Smoke Test

**Files:**
- Create: `frontend/src/pages/CrossBenchmark/CrossBenchmark.integration.test.tsx`

- [ ] **Step 1: Write the integration test**

Create `frontend/src/pages/CrossBenchmark/CrossBenchmark.integration.test.tsx`:

```typescript
/**
 * Integration test: verifies the CrossBenchmark page renders without errors
 * when all sub-components are wired together (no child component mocking).
 * API calls are still mocked at the hook level.
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

jest.mock("../../api/queries/cross-benchmark", () => ({
  useCrossBenchmarkMatrix: () => ({
    data: {
      model_versions: ["v1.0"],
      benchmarks: ["mmlu"],
      cells: [
        {
          model_version: "v1.0",
          benchmark: "mmlu",
          error_rate: 0.3,
          error_count: 30,
          total_count: 100,
        },
      ],
    },
    isLoading: false,
    isError: false,
    refetch: jest.fn(),
  }),
  useWeaknessReport: () => ({
    data: {
      generated_at: "2026-03-20T10:00:00Z",
      summary: "Test summary.",
      common_patterns: [
        {
          error_type: "推理性错误",
          affected_benchmarks: ["mmlu"],
          avg_error_rate: 0.3,
          record_count: 100,
        },
      ],
    },
    isLoading: false,
    isError: false,
    refetch: jest.fn(),
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

import CrossBenchmark from "./index";

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

describe("CrossBenchmark Page (integration)", () => {
  it("renders all three sections without crashing", () => {
    render(<CrossBenchmark />, { wrapper: createWrapper() });
    expect(screen.getByText("cross.title")).toBeInTheDocument();
    expect(screen.getByText("cross.heatmap.title")).toBeInTheDocument();
    expect(screen.getByText("cross.weakness.title")).toBeInTheDocument();
    expect(screen.getByText("cross.patterns.title")).toBeInTheDocument();
  });

  it("renders heatmap chart element", () => {
    render(<CrossBenchmark />, { wrapper: createWrapper() });
    expect(screen.getByTestId("echarts")).toBeInTheDocument();
  });

  it("renders weakness summary text", () => {
    render(<CrossBenchmark />, { wrapper: createWrapper() });
    expect(screen.getByText(/Test summary/)).toBeInTheDocument();
  });

  it("renders common pattern row in table", () => {
    render(<CrossBenchmark />, { wrapper: createWrapper() });
    expect(screen.getByText("推理性错误")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the integration test**

Run: `cd frontend && npx jest src/pages/CrossBenchmark/CrossBenchmark.integration.test.tsx --no-cache`
Expected: PASS (4 tests)

- [ ] **Step 3: Run the full test suite**

Run: `cd frontend && npx jest --no-cache`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/CrossBenchmark/CrossBenchmark.integration.test.tsx
git commit -m "test: add integration smoke test for CrossBenchmark page"
```

---

## Backend API Dependencies

This plan consumes these backend endpoints (from Plan 05):

| Endpoint | Response Type | Used By |
|----------|--------------|---------|
| `GET /api/v1/cross-benchmark/matrix` | `CrossBenchmarkMatrix` | HeatmapChart |
| `GET /api/v1/cross-benchmark/weakness` | `WeaknessReport \| null` | WeaknessReport, CommonPatternsTable |

Both endpoints accept optional `benchmark` and `model_version` query parameters for filtering. The `weakness` endpoint returns `null` (or HTTP 204) when no analysis has been run yet.

## Summary of Changes

| File | Action |
|------|--------|
| `frontend/src/types/api.ts` | Add 4 new types |
| `frontend/src/locales/zh.json` | Add 14 `cross.*` keys |
| `frontend/src/locales/en.json` | Add 14 `cross.*` keys |
| `frontend/src/api/queries/cross-benchmark.ts` | Create (2 hooks) |
| `frontend/src/api/queries/cross-benchmark.test.ts` | Create (4 tests) |
| `frontend/src/pages/CrossBenchmark/components/HeatmapChart.tsx` | Create |
| `frontend/src/pages/CrossBenchmark/components/HeatmapChart.test.tsx` | Create (5 tests) |
| `frontend/src/pages/CrossBenchmark/components/WeaknessReport.tsx` | Create |
| `frontend/src/pages/CrossBenchmark/components/WeaknessReport.test.tsx` | Create (5 tests) |
| `frontend/src/pages/CrossBenchmark/components/CommonPatternsTable.tsx` | Create |
| `frontend/src/pages/CrossBenchmark/components/CommonPatternsTable.test.tsx` | Create (6 tests) |
| `frontend/src/pages/CrossBenchmark/index.tsx` | Create |
| `frontend/src/pages/CrossBenchmark/CrossBenchmark.test.tsx` | Create (5 tests) |
| `frontend/src/pages/CrossBenchmark/CrossBenchmark.integration.test.tsx` | Create (4 tests) |
| `frontend/src/router.tsx` | Modify — wire real page |

**Total new tests: 29**
