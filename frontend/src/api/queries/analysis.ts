import { useQuery } from "@tanstack/react-query";
import apiClient from "@/api/client";
import { useGlobalFilters } from "@/hooks/useGlobalFilters";
import type {
  AnalysisSummary,
  DistributionItem,
  GlobalFilters,
  PaginatedRecords,
  RecordDetail,
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
  errorType?: string,
) {
  const filters = useGlobalFilters();

  return useQuery({
    queryKey: [
      "errorDistribution",
      groupBy,
      errorType,
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
            ...(errorType ? { error_type: errorType } : {}),
            ...filterParams(filters),
          },
        },
      );

      return data;
    },
  });
}

interface UseErrorRecordsParams {
  page: number;
  size: number;
  errorType?: string | null;
}

export function useErrorRecords({ page, size, errorType }: UseErrorRecordsParams) {
  const filters = useGlobalFilters();

  return useQuery({
    queryKey: [
      "errorRecords",
      page,
      size,
      errorType,
      filters.benchmark,
      filters.model_version,
      filters.time_range_start,
      filters.time_range_end,
    ],
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedRecords>("/analysis/records", {
        params: {
          page,
          size,
          ...(errorType ? { error_type: errorType } : {}),
          ...filterParams(filters),
        },
      });

      return data;
    },
  });
}

export function useRecordDetail(recordId: string | null) {
  return useQuery({
    queryKey: ["recordDetail", recordId],
    queryFn: async () => {
      const { data } = await apiClient.get<RecordDetail>(
        `/analysis/records/${recordId}/detail`,
      );
      return data;
    },
    enabled: Boolean(recordId),
  });
}
