import { useQuery } from "@tanstack/react-query";
import apiClient from "@/api/client";
import { useGlobalFilters } from "@/hooks/useGlobalFilters";
import type {
  AnalysisSummary,
  DistributionItem,
  GlobalFilters,
} from "@/types/api";

const filterParams = (filters: GlobalFilters): Record<string, string> => {
  const params: Record<string, string> = {};

  if (filters.benchmark) {
    params.benchmark = filters.benchmark;
  }
  if (filters.model_version) {
    params.model_version = filters.model_version;
  }
  if (filters.time_range_start) {
    params.time_range_start = filters.time_range_start;
  }
  if (filters.time_range_end) {
    params.time_range_end = filters.time_range_end;
  }

  return params;
};

export function useAnalysisSummary() {
  const filters = useGlobalFilters();

  return useQuery({
    queryKey: [
      "analysisSummary",
      filters.benchmark,
      filters.model_version,
      filters.time_range_start,
      filters.time_range_end,
    ],
    queryFn: async () => {
      const { data } = await apiClient.get<AnalysisSummary>("/analysis/summary", {
        params: filterParams(filters),
      });
      return data;
    },
  });
}

export function useErrorDistribution(
  groupBy: "error_type" | "category" | "severity",
) {
  const filters = useGlobalFilters();

  return useQuery({
    queryKey: [
      "errorDistribution",
      groupBy,
      filters.benchmark,
      filters.model_version,
      filters.time_range_start,
      filters.time_range_end,
    ],
    queryFn: async () => {
      const { data } = await apiClient.get<DistributionItem[]>(
        "/analysis/error-distribution",
        {
          params: {
            group_by: groupBy,
            ...filterParams(filters),
          },
        },
      );

      return data;
    },
  });
}
