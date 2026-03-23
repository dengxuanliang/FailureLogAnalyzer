import { useMemo, useState } from "react";
import { Alert, Button, Card, Descriptions, Drawer, Empty, Form, Input, Space, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useTranslation } from "react-i18next";
import { useGenerateReport, useReportDetail, useReportExport, useReports } from "@/api/queries/reports";
import type { ReportDetail, ReportGeneratePayload, ReportListItem } from "@/types/api";

const { Title, Text } = Typography;

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

const statusColor = (status: string) => {
  if (status === "done") {
    return "success";
  }
  if (status === "failed") {
    return "error";
  }
  if (status === "generating" || status === "pending") {
    return "processing";
  }
  return "default";
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

const renderContentPreview = (detail: ReportDetail) => {
  if (detail.content && typeof detail.content === "object") {
    return JSON.stringify(detail.content, null, 2);
  }
  return "{}";
};

export default function Reports() {
  const { t } = useTranslation();
  const [form] = Form.useForm<ReportGeneratePayload>();
  const reportsQuery = useReports();
  const detailReportExport = useReportExport();
  const generateReport = useGenerateReport();

  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const detailQuery = useReportDetail(selectedReportId);

  const handleExport = async (reportId: string, format: "json" | "markdown") => {
    const payload = await detailReportExport.mutateAsync({ reportId, format });
    triggerDownload(payload);
    setActionMessage(t("reports.exportSuccess"));
  };

  const handleGenerate = async (values: ReportGeneratePayload) => {
    const payload: ReportGeneratePayload = {
      title: values.title.trim(),
      report_type: values.report_type ?? "summary",
      benchmark: values.benchmark?.trim() || undefined,
      model_version: values.model_version?.trim() || undefined,
    };

    const response = await generateReport.mutateAsync(payload);
    setActionMessage(response.message);
    form.resetFields(["title", "benchmark", "model_version"]);
  };

  const columns: ColumnsType<ReportListItem> = useMemo(
    () => [
      {
        title: t("reports.columns.title"),
        dataIndex: "title",
        key: "title",
      },
      {
        title: t("reports.columns.type"),
        dataIndex: "report_type",
        key: "report_type",
      },
      {
        title: t("reports.columns.status"),
        dataIndex: "status",
        key: "status",
        render: (status: string) => <Tag color={statusColor(status)}>{status}</Tag>,
      },
      {
        title: t("reports.columns.benchmark"),
        dataIndex: "benchmark",
        key: "benchmark",
        render: (value: string | null) => value ?? "-",
      },
      {
        title: t("reports.columns.modelVersion"),
        dataIndex: "model_version",
        key: "model_version",
        render: (value: string | null) => value ?? "-",
      },
      {
        title: t("reports.columns.createdAt"),
        dataIndex: "created_at",
        key: "created_at",
        render: (value: string) => formatDateTime(value),
      },
      {
        title: t("reports.columns.actions"),
        key: "actions",
        render: (_, record) => (
          <Space>
            <Button size="small" onClick={() => setSelectedReportId(record.id)}>
              {t("reports.actions.view")}
            </Button>
            <Button size="small" onClick={() => void handleExport(record.id, "json")}> 
              {t("reports.actions.exportJson")}
            </Button>
            <Button size="small" onClick={() => void handleExport(record.id, "markdown")}> 
              {t("reports.actions.exportMarkdown")}
            </Button>
          </Space>
        ),
      },
    ],
    [t],
  );

  if (reportsQuery.isError) {
    return (
      <Alert
        type="error"
        message={t("common.error")}
        action={
          <Button size="small" onClick={() => void reportsQuery.refetch()}>
            {t("common.retry")}
          </Button>
        }
        showIcon
      />
    );
  }

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Title level={4}>{t("reports.title")}</Title>
      {actionMessage ? <Alert type="success" message={actionMessage} showIcon /> : null}

      <Card title={t("reports.form.heading")}>
        <Form
          form={form}
          layout="vertical"
          initialValues={{ report_type: "summary" }}
          onFinish={(values) => void handleGenerate(values)}
        >
          <Form.Item
            label={t("reports.form.title")}
            name="title"
            rules={[{ required: true, message: t("reports.form.titleRequired") }]}
          >
            <Input aria-label={t("reports.form.title")} />
          </Form.Item>
          <Form.Item label={t("reports.form.benchmark")} name="benchmark">
            <Input aria-label={t("reports.form.benchmark")} />
          </Form.Item>
          <Form.Item label={t("reports.form.modelVersion")} name="model_version">
            <Input aria-label={t("reports.form.modelVersion")} />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={generateReport.isPending}>
            {t("reports.actions.generate")}
          </Button>
        </Form>
      </Card>

      {!reportsQuery.isLoading && (!reportsQuery.data || reportsQuery.data.length === 0) ? (
        <Empty description={t("reports.empty")} />
      ) : (
        <Table
          rowKey={(record) => record.id}
          columns={columns}
          dataSource={reportsQuery.data ?? []}
          loading={reportsQuery.isLoading}
          pagination={{ pageSize: 10 }}
        />
      )}

      <Drawer
        open={Boolean(selectedReportId)}
        title={t("reports.detail.title")}
        onClose={() => setSelectedReportId(null)}
        width={720}
      >
        {detailQuery.isLoading ? <Text>{t("common.loading")}</Text> : null}
        {detailQuery.data ? (
          <Space direction="vertical" size="middle" style={{ width: "100%" }}>
            <Descriptions
              bordered
              column={1}
              size="small"
              styles={{ label: { width: 180 } }}
            >
              <Descriptions.Item label={t("reports.detail.id")}>{detailQuery.data.id}</Descriptions.Item>
              <Descriptions.Item label={t("reports.detail.titleLabel")}>{detailQuery.data.title}</Descriptions.Item>
              <Descriptions.Item label={t("reports.detail.type")}>{detailQuery.data.report_type}</Descriptions.Item>
              <Descriptions.Item label={t("reports.detail.status")}>{detailQuery.data.status}</Descriptions.Item>
              <Descriptions.Item label={t("reports.detail.createdAt")}>
                {formatDateTime(detailQuery.data.created_at)}
              </Descriptions.Item>
              <Descriptions.Item label={t("reports.detail.updatedAt")}>
                {formatDateTime(detailQuery.data.updated_at)}
              </Descriptions.Item>
            </Descriptions>

            <Text strong>{t("reports.detail.content")}</Text>
            <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{renderContentPreview(detailQuery.data)}</pre>
          </Space>
        ) : null}
      </Drawer>
    </Space>
  );
}
