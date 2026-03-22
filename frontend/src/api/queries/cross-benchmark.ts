import { useQuery } from "@tanstack/react-query";
import apiClient from "@/api/client";
import { useGlobalFilters } from "@/hooks/useGlobalFilters";
import type { GlobalFilters } from "@/types/api";

export interface MatrixCell {
  model_version: string;
  benchmark: string;
  error_rate: number;
  error_count: number;
  total_count: number;
}

export interface CrossBenchmarkMatrix {
  model_versions: string[];
  benchmarks: string[];
  cells: MatrixCell[];
}

export interface CommonErrorPattern {
  error_type: string;
  affected_benchmarks: string[];
  avg_error_rate: number;
  record_count: number;
}

export interface CrossBenchmarkWeaknessReport {
  generated_at: string;
  summary: string;
  common_patterns: CommonErrorPattern[];
}

interface BackendBenchmarkMatrix {
  models?: string[];
  benchmarks?: string[];
  matrix?: number[][];
}

interface BackendWeaknessItem {
  tag?: string;
  affected_benchmarks?: string[];
  avg_error_rate?: number;
}

interface BackendSystematicWeaknesses {
  weaknesses?: BackendWeaknessItem[];
}

const clampRate = (value: number): number => {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.min(1, Math.max(0, value));
};

const toMatrixCells = (payload: BackendBenchmarkMatrix): CrossBenchmarkMatrix => {
  const model_versions = payload.models ?? [];
  const benchmarks = payload.benchmarks ?? [];
  const matrix = payload.matrix ?? [];

  const cells: MatrixCell[] = [];
  model_versions.forEach((model_version, modelIndex) => {
    benchmarks.forEach((benchmark, benchmarkIndex) => {
      const accuracy = Number(matrix[modelIndex]?.[benchmarkIndex] ?? 0);
      cells.push({
        model_version,
        benchmark,
        error_rate: clampRate(1 - accuracy),
        error_count: 0,
        total_count: 0,
      });
    });
  });

  return {
    model_versions,
    benchmarks,
    cells,
  };
};

const toWeaknessReport = (
  payload: BackendSystematicWeaknesses | CrossBenchmarkWeaknessReport | null,
): CrossBenchmarkWeaknessReport | null => {
  if (!payload) {
    return null;
  }

  if ("summary" in payload && "common_patterns" in payload) {
    return payload;
  }

  const weaknesses = payload.weaknesses ?? [];
  if (weaknesses.length === 0) {
    return null;
  }

  return {
    generated_at: new Date().toISOString(),
    summary: `Detected ${weaknesses.length} recurring weakness pattern(s).`,
    common_patterns: weaknesses.map((item) => ({
      error_type: item.tag ?? "unknown",
      affected_benchmarks: item.affected_benchmarks ?? [],
      avg_error_rate: clampRate(Number(item.avg_error_rate ?? 0)),
      record_count: 0,
    })),
  };
};

const filterParams = (
  filters: Pick<GlobalFilters, "benchmark" | "model_version">,
): Record<string, string> => {
  const params: Record<string, string> = {};

  if (filters.benchmark) {
    params.benchmark = filters.benchmark;
  }

  if (filters.model_version) {
    params.model_version = filters.model_version;
  }

  return params;
};

export function useCrossBenchmarkMatrix() {
  const { benchmark, model_version } = useGlobalFilters();

  return useQuery<CrossBenchmarkMatrix>({
    queryKey: ["crossBenchmarkMatrix", benchmark, model_version],
    queryFn: async () => {
      const { data } = await apiClient.get<CrossBenchmarkMatrix | BackendBenchmarkMatrix>(
        "/cross-benchmark/matrix",
        {
          params: filterParams({ benchmark, model_version }),
        },
      );

      if ("cells" in data && "model_versions" in data) {
        return data;
      }

      return toMatrixCells(data);
    },
  });
}

export function useWeaknessReport() {
  const { benchmark, model_version } = useGlobalFilters();

  return useQuery<CrossBenchmarkWeaknessReport | null>({
    queryKey: ["weaknessReport", benchmark, model_version],
    queryFn: async () => {
      const { data } = await apiClient.get<
        CrossBenchmarkWeaknessReport | BackendSystematicWeaknesses | null
      >(
        "/cross-benchmark/weakness",
        {
          params: filterParams({ benchmark, model_version }),
        },
      );

      return toWeaknessReport(data);
    },
  });
}
