import { useState } from "react";
import { Alert, Button, Card, Popconfirm, Space, Switch, Table, Tag } from "antd";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/contexts/AuthContext";
import {
  type AnalysisStrategy,
  type AnalysisStrategyCreate,
  useCreateStrategy,
  useDeleteStrategy,
  useStrategies,
  useUpdateStrategy,
} from "@/api/queries/config";
import StrategyFormModal from "./StrategyFormModal";

export default function StrategiesPanel() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const canWrite = user?.role !== "viewer";
  const { data = [], isLoading, error } = useStrategies();
  const createStrategy = useCreateStrategy();
  const updateStrategy = useUpdateStrategy();
  const deleteStrategy = useDeleteStrategy();
  const [editingStrategy, setEditingStrategy] = useState<AnalysisStrategy | null>(null);
  const [creating, setCreating] = useState(false);

  const submit = async (values: AnalysisStrategyCreate) => {
    if (editingStrategy) {
      await updateStrategy.mutateAsync({ id: editingStrategy.id, data: values });
      setEditingStrategy(null);
      return;
    }

    await createStrategy.mutateAsync(values);
    setCreating(false);
  };

  return (
    <Card
      title={t("config.strategies.title")}
      extra={
        <Button type="primary" disabled={!canWrite || !!error} onClick={() => setCreating(true)}>
          {t("config.strategies.create")}
        </Button>
      }
    >
      {error ? (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          message={t("config.strategies.loadError")}
          description={error.message}
        />
      ) : null}
      <Table<AnalysisStrategy>
        rowKey="id"
        loading={isLoading}
        dataSource={data}
        pagination={false}
        columns={[
          { title: t("config.strategies.columns.name"), dataIndex: "name", key: "name" },
          {
            title: t("config.strategies.columns.type"),
            key: "type",
            render: (_, record) => <Tag>{t(`config.strategies.type.${record.strategy_type}`)}</Tag>,
          },
          { title: t("config.strategies.columns.provider"), dataIndex: "llm_provider", key: "provider" },
          { title: t("config.strategies.columns.model"), dataIndex: "llm_model", key: "model" },
          {
            title: t("config.strategies.columns.maxConcurrent"),
            dataIndex: "max_concurrent",
            key: "maxConcurrent",
          },
          {
            title: t("config.strategies.columns.dailyBudget"),
            dataIndex: "daily_budget",
            key: "dailyBudget",
          },
          {
            title: t("config.strategies.columns.status"),
            key: "status",
            render: (_, record) => (
              <Switch
                disabled={!canWrite}
                checked={record.is_active}
                onChange={(checked) =>
                  void updateStrategy.mutateAsync({ id: record.id, data: { is_active: checked } })
                }
              />
            ),
          },
          {
            title: t("config.strategies.columns.actions"),
            key: "actions",
            render: (_, record) => (
              <Space>
                <Button type="link" disabled={!canWrite} onClick={() => setEditingStrategy(record)}>
                  {t("common.edit")}
                </Button>
                <Popconfirm
                  title={t("common.delete")}
                  onConfirm={() => void deleteStrategy.mutateAsync(record.id)}
                  disabled={!canWrite}
                >
                  <Button type="link" danger disabled={!canWrite}>
                    {t("common.delete")}
                  </Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />
      <StrategyFormModal
        open={creating || !!editingStrategy}
        strategy={editingStrategy}
        onSubmit={submit}
        onCancel={() => {
          setCreating(false);
          setEditingStrategy(null);
        }}
        loading={createStrategy.isPending || updateStrategy.isPending}
      />
    </Card>
  );
}
