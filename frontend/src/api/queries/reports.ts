import { useMutation, useQuery } from "@tanstack/react-query";
import apiClient from "../client";
import type { ReportDetail, ReportExportPayload, ReportListItem } from "@/types/api";

const REPORTS_KEY = ["reports"] as const;

export function useReports() {
  return useQuery<ReportListItem[]>({
    queryKey: REPORTS_KEY,
    queryFn: () => apiClient.get<ReportListItem[]>("/reports").then((response) => response.data),
  });
}

export function useReportDetail(reportId: string | null) {
  return useQuery<ReportDetail>({
    queryKey: [...REPORTS_KEY, reportId],
    queryFn: () => apiClient.get<ReportDetail>(`/reports/${reportId}`).then((response) => response.data),
    enabled: Boolean(reportId),
  });
}

export function useReportExport() {
  return useMutation<ReportExportPayload, Error, { reportId: string; format: "json" | "markdown" }>({
    mutationFn: async ({ reportId, format }) => {
      const response = await apiClient.get<globalThis.Blob>(`/reports/${reportId}/export`, {
        params: { format },
        responseType: "blob",
      });
      const disposition = response.headers?.["content-disposition"] as string | undefined;
      let filename = `report-${reportId}.${format === "markdown" ? "md" : "json"}`;
      if (disposition) {
        const match = /filename="?([^";]+)"?/i.exec(disposition);
        if (match?.[1]) {
          filename = match[1];
        }
      }
      return { blob: response.data, filename };
    },
  });
}
