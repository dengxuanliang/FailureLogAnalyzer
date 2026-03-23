import { jest } from "@jest/globals";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { PropsWithChildren } from "react";
import { MemoryRouter, useLocation } from "react-router-dom";

jest.unstable_mockModule("antd", () => ({
  Space: ({ children }: PropsWithChildren) => <div>{children}</div>,
  Select: ({
    value,
    options,
    onChange,
    "data-testid": testId,
  }: {
    value?: string;
    options?: Array<{ label: string; value: string }>;
    onChange?: (value: string | undefined) => void;
    "data-testid"?: string;
  }) => (
    <select
      data-testid={testId}
      value={value ?? ""}
      onChange={(event) => onChange?.(event.target.value || undefined)}
    >
      <option value="">--</option>
      {(options ?? []).map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  ),
  DatePicker: {
    RangePicker: ({ "data-testid": testId }: { "data-testid"?: string }) => (
      <div data-testid={testId}>range-picker</div>
    ),
  },
  Typography: {
    Text: ({ children }: PropsWithChildren) => <span>{children}</span>,
  },
}));

jest.unstable_mockModule("@/api/queries/sessions", () => ({
  useSessions: () => ({
    data: [
      {
        id: "sess-1",
        model: "gpt-4o",
        model_version: "v1.0",
        benchmark: "mmlu",
        dataset_name: null,
        total_count: 100,
        error_count: 20,
        accuracy: 0.8,
        tags: [],
        created_at: "2026-03-20T00:00:00Z",
      },
      {
        id: "sess-2",
        model: "gpt-4o-mini",
        model_version: "v2.0",
        benchmark: "ceval",
        dataset_name: null,
        total_count: 200,
        error_count: 30,
        accuracy: 0.85,
        tags: [],
        created_at: "2026-03-21T00:00:00Z",
      },
      {
        id: "sess-3",
        model: "gpt-4o-mini",
        model_version: "v2.0",
        benchmark: "ceval",
        dataset_name: null,
        total_count: 220,
        error_count: 32,
        accuracy: 0.854,
        tags: [],
        created_at: "2026-03-22T00:00:00Z",
      },
    ],
    isLoading: false,
  }),
}));

jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "filter.benchmark": "Benchmark",
        "filter.modelVersion": "模型版本",
        "filter.timeRange": "时间范围",
      };
      return map[key] ?? key;
    },
  }),
}));

const { FilterProvider } = await import("@/contexts/FilterContext");
const { useGlobalFilters } = await import("@/hooks/useGlobalFilters");
const { default: FilterBar } = await import("./FilterBar");

function FilterProbe() {
  const filters = useGlobalFilters();
  const location = useLocation();

  return (
    <>
      <div data-testid="benchmark-value">{filters.benchmark ?? "null"}</div>
      <div data-testid="model-version-value">{filters.model_version ?? "null"}</div>
      <div data-testid="search-value">{location.search}</div>
    </>
  );
}

const renderFilterBar = (initialEntries: string[] = ["/"]) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        initialEntries={initialEntries}
      >
        <FilterProvider>
          <FilterBar />
          <FilterProbe />
        </FilterProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

describe("FilterBar", () => {
  it("renders benchmark/model version/time range controls", () => {
    renderFilterBar();

    expect(screen.getByText("Benchmark")).toBeInTheDocument();
    expect(screen.getByText("模型版本")).toBeInTheDocument();
    expect(screen.getByText("时间范围")).toBeInTheDocument();
    expect(screen.getByTestId("time-range-picker")).toBeInTheDocument();
  });

  it("uses sessions options and updates global filters", async () => {
    const user = userEvent.setup();
    renderFilterBar(["/?benchmark=mmlu&model_version=v1.0"]);

    const benchmarkSelect = screen.getByTestId("benchmark-select");
    const versionSelect = screen.getByTestId("model-version-select");

    expect(screen.getByRole("option", { name: "mmlu" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "ceval" })).toBeInTheDocument();
    expect(screen.getAllByRole("option", { name: "v2.0" })).toHaveLength(1);

    await user.selectOptions(benchmarkSelect, "ceval");
    await waitFor(() => {
      expect(screen.getByTestId("benchmark-value")).toHaveTextContent("ceval");
    });

    await user.selectOptions(versionSelect, "v2.0");
    await waitFor(() => {
      expect(screen.getByTestId("model-version-value")).toHaveTextContent("v2.0");
    });

    const params = new URLSearchParams(screen.getByTestId("search-value").textContent ?? "");
    expect(params.get("benchmark")).toBe("ceval");
    expect(params.get("model_version")).toBe("v2.0");
  });

  it("always includes built-in benchmark options before dynamic session values", () => {
    renderFilterBar();

    const benchmarkOptions = screen.getAllByRole("option").map((option) => option.textContent);
    expect(benchmarkOptions).toContain("livecodebench v6");
    expect(benchmarkOptions).toContain("fullstackbench");
    expect(benchmarkOptions).toContain("codeforces");
    expect(benchmarkOptions).toContain("mmlu");
    expect(benchmarkOptions).toContain("ceval");
  });
});
