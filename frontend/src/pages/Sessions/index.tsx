import { useMemo, useState } from "react";
import { Alert, Button, Descriptions, Drawer, Empty, Space, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useTranslation } from "react-i18next";
import {
  useDeleteSession,
  useRerunSessionRules,
  useSessionDetail,
  useSessions,
} from "@/api/queries/sessions";
import type { EvalSession } from "@/types/api";

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

export default function Sessions() {
  const { t } = useTranslation();
  const sessionsQuery = useSessions();
  const deleteMutation = useDeleteSession();
  const rerunMutation = useRerunSessionRules();

  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [pendingActionSessionId, setPendingActionSessionId] = useState<string | null>(null);
  const [pendingActionType, setPendingActionType] = useState<"delete" | "rerun" | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const detailQuery = useSessionDetail(selectedSessionId);

  const handleRerunRules = async (sessionId: string) => {
    setPendingActionSessionId(sessionId);
    setPendingActionType("rerun");
    try {
      const response = await rerunMutation.mutateAsync({ sessionId });
      setActionMessage(response.message);
    } finally {
      setPendingActionSessionId(null);
      setPendingActionType(null);
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    setPendingActionSessionId(sessionId);
    setPendingActionType("delete");
    try {
      await deleteMutation.mutateAsync(sessionId);
      if (selectedSessionId === sessionId) {
        setSelectedSessionId(null);
      }
      setActionMessage(t("sessions.deleteSuccess"));
    } finally {
      setPendingActionSessionId(null);
      setPendingActionType(null);
    }
  };

  const columns: ColumnsType<EvalSession> = useMemo(
    () => [
      {
        title: t("sessions.columns.model"),
        dataIndex: "model",
        key: "model",
      },
      {
        title: t("sessions.columns.version"),
        dataIndex: "model_version",
        key: "model_version",
      },
      {
        title: t("sessions.columns.benchmark"),
        dataIndex: "benchmark",
        key: "benchmark",
      },
      {
        title: t("sessions.columns.errors"),
        dataIndex: "error_count",
        key: "error_count",
      },
      {
        title: t("sessions.columns.accuracy"),
        dataIndex: "accuracy",
        key: "accuracy",
        render: (value: number) => `${(value * 100).toFixed(1)}%`,
      },
      {
        title: t("sessions.columns.createdAt"),
        dataIndex: "created_at",
        key: "created_at",
        render: (value: string) => formatDateTime(value),
      },
      {
        title: t("sessions.columns.tags"),
        dataIndex: "tags",
        key: "tags",
        render: (tags: string[]) =>
          tags.length > 0 ? (
            <Space size={[4, 4]} wrap>
              {tags.map((tag) => (
                <Tag key={tag}>{tag}</Tag>
              ))}
            </Space>
          ) : (
            "-"
          ),
      },
      {
        title: t("sessions.columns.actions"),
        key: "actions",
        render: (_, record) => (
          <Space>
            <Button size="small" onClick={() => setSelectedSessionId(record.id)}>
              {t("sessions.actions.view")}
            </Button>
            <Button
              size="small"
              onClick={() => void handleRerunRules(record.id)}
              loading={
                pendingActionType === "rerun" &&
                pendingActionSessionId === record.id &&
                rerunMutation.isPending
              }
            >
              {t("sessions.actions.rerun")}
            </Button>
            <Button
              size="small"
              danger
              onClick={() => void handleDeleteSession(record.id)}
              loading={
                pendingActionType === "delete" &&
                pendingActionSessionId === record.id &&
                deleteMutation.isPending
              }
            >
              {t("sessions.actions.delete")}
            </Button>
          </Space>
        ),
      },
    ],
    [
      t,
      pendingActionSessionId,
      pendingActionType,
      rerunMutation.isPending,
      deleteMutation.isPending,
    ],
  );

  if (sessionsQuery.isError) {
    return (
      <Alert
        type="error"
        message={t("common.error")}
        action={
          <Button size="small" onClick={() => void sessionsQuery.refetch()}>
            {t("common.retry")}
          </Button>
        }
        showIcon
      />
    );
  }

  if (!sessionsQuery.isLoading && (!sessionsQuery.data || sessionsQuery.data.length === 0)) {
    return <Empty description={t("sessions.empty")} />;
  }

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Title level={4}>{t("sessions.title")}</Title>
      {actionMessage ? <Alert type="success" message={actionMessage} showIcon /> : null}
      <Table
        rowKey={(record) => record.id}
        columns={columns}
        dataSource={sessionsQuery.data ?? []}
        loading={sessionsQuery.isLoading}
        pagination={{ pageSize: 10 }}
      />

      <Drawer
        open={Boolean(selectedSessionId)}
        title={t("sessions.detail.title")}
        onClose={() => setSelectedSessionId(null)}
        width={640}
      >
        {detailQuery.isLoading ? <Text>{t("common.loading")}</Text> : null}
        {detailQuery.data ? (
          <Descriptions
            column={1}
            bordered
            size="small"
            styles={{ label: { width: 180 } }}
          >
            <Descriptions.Item label={t("sessions.detail.id")}>{detailQuery.data.id}</Descriptions.Item>
            <Descriptions.Item label={t("sessions.detail.model")}>{detailQuery.data.model}</Descriptions.Item>
            <Descriptions.Item label={t("sessions.detail.version")}>{detailQuery.data.model_version}</Descriptions.Item>
            <Descriptions.Item label={t("sessions.detail.benchmark")}>{detailQuery.data.benchmark}</Descriptions.Item>
            <Descriptions.Item label={t("sessions.detail.dataset")}>{detailQuery.data.dataset_name ?? "-"}</Descriptions.Item>
            <Descriptions.Item label={t("sessions.detail.total")}>{detailQuery.data.total_count}</Descriptions.Item>
            <Descriptions.Item label={t("sessions.detail.errors")}>{detailQuery.data.error_count}</Descriptions.Item>
            <Descriptions.Item label={t("sessions.detail.accuracy")}>
              {(detailQuery.data.accuracy * 100).toFixed(1)}%
            </Descriptions.Item>
            <Descriptions.Item label={t("sessions.detail.createdAt")}>
              {formatDateTime(detailQuery.data.created_at)}
            </Descriptions.Item>
            <Descriptions.Item label={t("sessions.detail.updatedAt")}>
              {formatDateTime(detailQuery.data.updated_at)}
            </Descriptions.Item>
          </Descriptions>
        ) : null}
      </Drawer>
    </Space>
  );
}
