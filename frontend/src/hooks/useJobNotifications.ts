import { useEffect, useRef } from "react";
import { App } from "antd";
import { useTranslation } from "react-i18next";

export type JobType = "ingest" | "llm";

interface JobProgressEvent {
  status?: string;
  processed?: number;
  error?: string;
  job_id?: string;
}

const buildProgressWebSocketUrl = (jobId: string): string => {
  const env = (import.meta.env ?? {}) as Partial<ImportMetaEnv>;
  const apiBaseUrl = env.VITE_API_BASE_URL ?? "/api/v1";

  const base =
    apiBaseUrl.startsWith("http://") || apiBaseUrl.startsWith("https://")
      ? apiBaseUrl.replace(/^http/, "ws")
      : `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}${apiBaseUrl}`;

  return `${base}/ws/progress?job_id=${encodeURIComponent(jobId)}`;
};

export function useJobNotifications(jobId: string | null, jobType: JobType): void {
  const { notification } = App.useApp();
  const { t } = useTranslation();
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!jobId || typeof WebSocket === "undefined") {
      return undefined;
    }

    const ws = new WebSocket(buildProgressWebSocketUrl(jobId));
    wsRef.current = ws;

    ws.onmessage = (event: MessageEvent) => {
      let payload: JobProgressEvent;
      try {
        payload = JSON.parse(String(event.data)) as JobProgressEvent;
      } catch {
        return;
      }

      if (payload.job_id && payload.job_id !== jobId) {
        return;
      }

      if (payload.status === "done") {
        if (jobType === "ingest") {
          notification.success({
            message: t("notify.ingestDone"),
            description: t("notify.ingestDoneDesc", {
              jobId,
              count: payload.processed ?? 0,
            }),
            placement: "topRight",
          });
        } else {
          notification.success({
            message: t("notify.llmDone"),
            description: t("notify.llmDoneDesc", {
              count: payload.processed ?? 0,
            }),
            placement: "topRight",
          });
        }
        ws.close();
      }

      if (payload.status === "failed") {
        if (jobType === "ingest") {
          notification.error({
            message: t("notify.ingestFailed"),
            description: t("notify.ingestFailedDesc", {
              jobId,
              error: payload.error ?? "unknown",
            }),
            placement: "topRight",
          });
        } else {
          notification.error({
            message: t("notify.llmFailed"),
            description: t("notify.llmFailedDesc", {
              jobId,
              error: payload.error ?? "unknown",
            }),
            placement: "topRight",
          });
        }
        ws.close();
      }
    };

    ws.onerror = () => {
      ws.close();
    };

    return () => {
      ws.onmessage = null;
      ws.close();
      wsRef.current = null;
    };
  }, [jobId, jobType, notification, t]);
}
