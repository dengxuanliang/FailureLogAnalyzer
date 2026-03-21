import { useQuery } from "@tanstack/react-query";
import apiClient from "@/api/client";
import { useGlobalFilters } from "@/hooks/useGlobalFilters";
import type { RadarData, VersionComparison, VersionDiff } from "@/types/api";

function buildCompareParams(
  versionA: string | null,
  versionB: string | null,
  benchmark: string | null,
) {
  const params: Record<string, string> = {
    version_a: versionA!,
    version_b: versionB!,
  };

  if (benchmark) {
    params.benchmark = benchmark;
  }

  return params;
}

export function useVersionComparison(versionA: string | null, versionB: string | null) {
  const { benchmark } = useGlobalFilters();

  return useQuery<VersionComparison>({
    queryKey: ["versionComparison", versionA, versionB, benchmark],
    queryFn: async () => {
      const { data } = await apiClient.get<VersionComparison>("/compare/versions", {
        params: buildCompareParams(versionA, versionB, benchmark),
      });
      return data;
    },
    enabled: Boolean(versionA && versionB),
  });
}

export function useVersionDiff(versionA: string | null, versionB: string | null) {
  const { benchmark } = useGlobalFilters();

  return useQuery<VersionDiff>({
    queryKey: ["versionDiff", versionA, versionB, benchmark],
    queryFn: async () => {
      const { data } = await apiClient.get<VersionDiff>("/compare/diff", {
        params: buildCompareParams(versionA, versionB, benchmark),
      });
      return data;
    },
    enabled: Boolean(versionA && versionB),
  });
}

export function useRadarData(versionA: string | null, versionB: string | null) {
  const { benchmark } = useGlobalFilters();

  return useQuery<RadarData>({
    queryKey: ["radarData", versionA, versionB, benchmark],
    queryFn: async () => {
      const { data } = await apiClient.get<RadarData>("/compare/radar", {
        params: buildCompareParams(versionA, versionB, benchmark),
      });
      return data;
    },
    enabled: Boolean(versionA && versionB),
  });
}
