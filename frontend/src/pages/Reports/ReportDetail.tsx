import { Alert, Button, Card, Descriptions, Empty, Space } from "antd";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { useReportDetail, useReportExport } from "@/api/queries/reports";

const formatDateTime = (value: string | null | undefined) => {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
};

const triggerDownload = (payload: { blob: globalThis.Blob; filename: string }) => {
  if (typeof URL.createObjectURL !== "function") {
    return;
  }
  const url = URL.createObjectURL(payload.blob);
  if (typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent)) {
    URL.revokeObjectURL(url);
    return;
  }
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = payload.filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
};

export default function ReportDetail() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { reportId } = useParams();
  const reportQuery = useReportDetail(reportId ?? null);
  const exportReport = useReportExport();

  const handleExport = async (format: "json" | "markdown") => {
    if (!reportId) {
      return;
    }
    const payload = await exportReport.mutateAsync({ reportId, format });
    triggerDownload(payload);
  };

  if (reportQuery.isError) {
    return (
      <Alert
        type="error"
        message={t("common.error")}
        action={
          <Button size="small" onClick={() => void reportQuery.refetch()}>
            {t("common.retry")}
          </Button>
        }
        showIcon
      />
    );
  }

  if (!reportQuery.data && reportQuery.isLoading) {
    return <Empty />;
  }

  if (!reportQuery.data) {
    return <Empty />;
  }

  const report = reportQuery.data;

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Space>
        <Button onClick={() => navigate("/reports")}>{t("reports.actions.back")}</Button>
        <Button onClick={() => void handleExport("json")}>{t("reports.actions.exportJson")}</Button>
        <Button onClick={() => void handleExport("markdown")}>{t("reports.actions.exportMarkdown")}</Button>
      </Space>

      <Card title={t("reports.detail.title")}>
        <Descriptions bordered column={1} size="small" styles={{ label: { width: 180 } }}>
          <Descriptions.Item label={t("reports.detail.id")}>{report.id}</Descriptions.Item>
          <Descriptions.Item label={t("reports.detail.titleLabel")}>{report.title}</Descriptions.Item>
          <Descriptions.Item label={t("reports.detail.type")}>{report.report_type}</Descriptions.Item>
          <Descriptions.Item label={t("reports.detail.status")}>{report.status}</Descriptions.Item>
          <Descriptions.Item label={t("reports.detail.createdAt")}>
            {formatDateTime(report.created_at)}
          </Descriptions.Item>
          <Descriptions.Item label={t("reports.detail.updatedAt")}>
            {formatDateTime(report.updated_at)}
          </Descriptions.Item>
        </Descriptions>

        <Card size="small" style={{ marginTop: 16 }}>
          <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{JSON.stringify(report.content, null, 2)}</pre>
        </Card>
      </Card>
    </Space>
  );
}
