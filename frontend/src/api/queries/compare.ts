import { useQuery } from "@tanstack/react-query";
import apiClient from "@/api/client";
import { useGlobalFilters } from "@/hooks/useGlobalFilters";
import type { RadarData, VersionComparison, VersionDiff } from "@/types/api";

interface BackendVersionComparison {
  version_a: string;
  version_b: string;
  benchmark?: string | null;
  sessions_a: number;
  sessions_b: number;
  accuracy_a: number;
  accuracy_b: number;
  error_rate_a: number;
  error_rate_b: number;
}

interface BackendDiffItem {
  question_id?: string | null;
  benchmark?: string | null;
  category?: string | null;
  old_tag?: string | null;
  new_tag?: string | null;
}

interface BackendVersionDiff {
  version_a: string;
  version_b: string;
  regressed: BackendDiffItem[];
  improved: BackendDiffItem[];
  new_errors: BackendDiffItem[];
  fixed_errors: BackendDiffItem[];
}

const isLegacyComparison = (
  payload: VersionComparison | BackendVersionComparison,
): payload is VersionComparison => "metrics_a" in payload && "metrics_b" in payload;

const normalizeComparison = (
  payload: VersionComparison | BackendVersionComparison,
): VersionComparison => {
  if (isLegacyComparison(payload)) {
    return payload;
  }

  return {
    version_a: payload.version_a,
    version_b: payload.version_b,
    benchmark: payload.benchmark ?? null,
    metrics_a: {
      total: payload.sessions_a ?? 0,
      errors: Math.max(0, Math.round((payload.error_rate_a ?? 0) * (payload.sessions_a ?? 0))),
      accuracy: payload.accuracy_a ?? 0,
      error_type_distribution: {},
    },
    metrics_b: {
      total: payload.sessions_b ?? 0,
      errors: Math.max(0, Math.round((payload.error_rate_b ?? 0) * (payload.sessions_b ?? 0))),
      accuracy: payload.accuracy_b ?? 0,
      error_type_distribution: {},
    },
  };
};

const normalizeDiffItem = (item: BackendDiffItem): VersionDiff["regressed"][number] => ({
  question_id: item.question_id ?? "",
  benchmark: item.benchmark ?? "",
  task_category: item.category ?? null,
  question: "",
});

const diffTagFromItem = (item: BackendDiffItem): string =>
  item.new_tag ?? item.old_tag ?? item.category ?? item.question_id ?? item.benchmark ?? "unknown";

const isLegacyDiff = (payload: VersionDiff | BackendVersionDiff): payload is VersionDiff =>
  "resolved_errors" in payload;

const normalizeDiff = (payload: VersionDiff | BackendVersionDiff): VersionDiff => {
  if (isLegacyDiff(payload)) {
    return payload;
  }

  return {
    regressed: (payload.regressed ?? []).map(normalizeDiffItem),
    improved: (payload.improved ?? []).map(normalizeDiffItem),
    new_errors: (payload.new_errors ?? []).map(diffTagFromItem),
    resolved_errors: (payload.fixed_errors ?? []).map(diffTagFromItem),
  };
};

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
      const { data } = await apiClient.get<VersionComparison | BackendVersionComparison>(
        "/compare/versions",
        {
        params: buildCompareParams(versionA, versionB, benchmark),
        },
      );
      return normalizeComparison(data);
    },
    enabled: Boolean(versionA && versionB),
  });
}

export function useVersionDiff(versionA: string | null, versionB: string | null) {
  const { benchmark } = useGlobalFilters();

  return useQuery<VersionDiff>({
    queryKey: ["versionDiff", versionA, versionB, benchmark],
    queryFn: async () => {
      const { data } = await apiClient.get<VersionDiff | BackendVersionDiff>("/compare/diff", {
        params: buildCompareParams(versionA, versionB, benchmark),
      });
      return normalizeDiff(data);
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
