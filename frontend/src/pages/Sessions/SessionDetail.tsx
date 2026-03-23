import { Alert, Button, Card, Descriptions, Empty, Space, Tag, Typography } from "antd";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { useDeleteSession, useRerunSessionRules, useSessionDetail } from "@/api/queries/sessions";

const { Text } = Typography;

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

export default function SessionDetail() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { sessionId } = useParams();
  const detailQuery = useSessionDetail(sessionId ?? null);
  const deleteMutation = useDeleteSession();
  const rerunMutation = useRerunSessionRules();

  const handleRerun = async () => {
    if (!sessionId) return;
    await rerunMutation.mutateAsync({ sessionId });
  };

  const handleDelete = async () => {
    if (!sessionId) return;
    await deleteMutation.mutateAsync(sessionId);
    navigate("/sessions");
  };

  if (detailQuery.isError) {
    return (
      <Alert
        type="error"
        message={t("common.error")}
        action={
          <Button size="small" onClick={() => void detailQuery.refetch()}>
            {t("common.retry")}
          </Button>
        }
        showIcon
      />
    );
  }

  if (detailQuery.isLoading && !detailQuery.data) {
    return <Text>{t("common.loading")}</Text>;
  }

  if (!detailQuery.data) {
    return <Empty />;
  }

  const session = detailQuery.data;

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Space>
        <Button onClick={() => navigate("/sessions")}>{t("sessions.actions.back")}</Button>
        <Button onClick={() => void handleRerun()}>{t("sessions.actions.rerun")}</Button>
        <Button danger onClick={() => void handleDelete()}>{t("sessions.actions.delete")}</Button>
      </Space>
      <Card title={t("sessions.detail.title")}>
        <Descriptions bordered column={1} size="small" styles={{ label: { width: 180 } }}>
          <Descriptions.Item label={t("sessions.detail.id")}>{session.id}</Descriptions.Item>
          <Descriptions.Item label={t("sessions.detail.model")}>{session.model}</Descriptions.Item>
          <Descriptions.Item label={t("sessions.detail.version")}>{session.model_version}</Descriptions.Item>
          <Descriptions.Item label={t("sessions.detail.benchmark")}>{session.benchmark}</Descriptions.Item>
          <Descriptions.Item label={t("sessions.detail.dataset")}>{session.dataset_name ?? "-"}</Descriptions.Item>
          <Descriptions.Item label={t("sessions.detail.total")}>{session.total_count}</Descriptions.Item>
          <Descriptions.Item label={t("sessions.detail.errors")}>{session.error_count}</Descriptions.Item>
          <Descriptions.Item label={t("sessions.detail.accuracy")}>{(session.accuracy * 100).toFixed(1)}%</Descriptions.Item>
          <Descriptions.Item label={t("sessions.detail.createdAt")}>{formatDateTime(session.created_at)}</Descriptions.Item>
          <Descriptions.Item label={t("sessions.detail.updatedAt")}>{formatDateTime(session.updated_at)}</Descriptions.Item>
          <Descriptions.Item label={t("sessions.columns.tags")}>
            <Space size={[4, 4]} wrap>
              {session.tags?.length ? session.tags.map((tag) => <Tag key={tag}>{tag}</Tag>) : "-"}
            </Space>
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </Space>
  );
}
