import { useState } from "react";
import { Button, Card, Popconfirm, Space, Switch, Table, Tag } from "antd";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/contexts/AuthContext";
import {
  type AnalysisRule,
  type AnalysisRuleCreate,
  useCreateRule,
  useDeleteRule,
  useRules,
  useUpdateRule,
} from "@/api/queries/config";
import RuleFormModal from "./RuleFormModal";

export default function RulesPanel() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const canWrite = user?.role !== "viewer";
  const { data = [], isLoading } = useRules();
  const createRule = useCreateRule();
  const updateRule = useUpdateRule();
  const deleteRule = useDeleteRule();
  const [editingRule, setEditingRule] = useState<AnalysisRule | null>(null);
  const [creating, setCreating] = useState(false);

  const submit = async (values: AnalysisRuleCreate) => {
    if (editingRule) {
      await updateRule.mutateAsync({ id: editingRule.id, data: values });
      setEditingRule(null);
      return;
    }

    await createRule.mutateAsync(values);
    setCreating(false);
  };

  return (
    <Card
      title={t("config.rules.title")}
      extra={
        <Button type="primary" disabled={!canWrite} onClick={() => setCreating(true)}>
          {t("config.rules.create")}
        </Button>
      }
    >
      <Table<AnalysisRule>
        rowKey="id"
        loading={isLoading}
        dataSource={data}
        pagination={false}
        columns={[
          { title: t("config.rules.columns.name"), dataIndex: "name", key: "name" },
          { title: t("config.rules.columns.field"), dataIndex: "field", key: "field" },
          {
            title: t("config.rules.columns.conditionType"),
            key: "condition",
            render: (_, record) => <Tag>{record.condition.type}</Tag>,
          },
          {
            title: t("config.rules.columns.tags"),
            key: "tags",
            render: (_, record) => (
              <Space wrap>
                {record.tags.map((tag) => (
                  <Tag key={tag}>{tag}</Tag>
                ))}
              </Space>
            ),
          },
          {
            title: t("config.rules.columns.confidence"),
            dataIndex: "confidence",
            key: "confidence",
          },
          {
            title: t("config.rules.columns.priority"),
            dataIndex: "priority",
            key: "priority",
          },
          {
            title: t("config.rules.columns.status"),
            key: "status",
            render: (_, record) => (
              <Switch
                disabled={!canWrite}
                checked={record.is_active}
                checkedChildren={t("config.rules.enabled")}
                unCheckedChildren={t("config.rules.disabled")}
                onChange={(checked) =>
                  void updateRule.mutateAsync({ id: record.id, data: { is_active: checked } })
                }
              />
            ),
          },
          {
            title: t("config.rules.columns.actions"),
            key: "actions",
            render: (_, record) => (
              <Space>
                <Button type="link" disabled={!canWrite} onClick={() => setEditingRule(record)}>
                  {t("common.edit")}
                </Button>
                <Popconfirm
                  title={t("config.rules.delete")}
                  onConfirm={() => void deleteRule.mutateAsync(record.id)}
                  disabled={!canWrite}
                >
                  <Button type="link" danger disabled={!canWrite}>
                    {t("config.rules.delete")}
                  </Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />
      <RuleFormModal
        open={creating || !!editingRule}
        rule={editingRule}
        onSubmit={submit}
        onCancel={() => {
          setCreating(false);
          setEditingRule(null);
        }}
        loading={createRule.isPending || updateRule.isPending}
      />
    </Card>
  );
}
