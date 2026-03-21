import { useQuery } from "@tanstack/react-query";
import apiClient from "@/api/client";
import { useGlobalFilters } from "@/hooks/useGlobalFilters";
import type { ErrorTrends } from "@/types/api";

export function useTrends() {
  const { benchmark, model_version } = useGlobalFilters();

  return useQuery({
    queryKey: ["trends", benchmark, model_version],
    queryFn: async () => {
      const params: Record<string, string> = {};

      if (benchmark) {
        params.benchmark = benchmark;
      }

      if (model_version) {
        params.model_version = model_version;
      }

      const { data } = await apiClient.get<ErrorTrends>("/trends", { params });
      return data;
    },
  });
}
