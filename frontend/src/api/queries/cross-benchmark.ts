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

  return useQuery({
    queryKey: ["crossBenchmarkMatrix", benchmark, model_version],
    queryFn: async () => {
      const { data } = await apiClient.get<CrossBenchmarkMatrix>("/cross-benchmark/matrix", {
        params: filterParams({ benchmark, model_version }),
      });

      return data;
    },
  });
}

export function useWeaknessReport() {
  const { benchmark, model_version } = useGlobalFilters();

  return useQuery({
    queryKey: ["weaknessReport", benchmark, model_version],
    queryFn: async () => {
      const { data } = await apiClient.get<CrossBenchmarkWeaknessReport | null>(
        "/cross-benchmark/weakness",
        {
          params: filterParams({ benchmark, model_version }),
        },
      );

      return data;
    },
  });
}
