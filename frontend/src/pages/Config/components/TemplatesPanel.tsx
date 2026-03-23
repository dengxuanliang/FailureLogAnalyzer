import { useState } from "react";
import { Alert, Button, Card, Popconfirm, Space, Switch, Table } from "antd";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/contexts/AuthContext";
import {
  type PromptTemplate,
  type PromptTemplateCreate,
  useCreateTemplate,
  useDeleteTemplate,
  useTemplates,
  useUpdateTemplate,
} from "@/api/queries/config";
import TemplateFormModal from "./TemplateFormModal";

export default function TemplatesPanel() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const canWrite = user?.role !== "viewer";
  const { data = [], isLoading, error } = useTemplates();
  const createTemplate = useCreateTemplate();
  const updateTemplate = useUpdateTemplate();
  const deleteTemplate = useDeleteTemplate();
  const [editingTemplate, setEditingTemplate] = useState<PromptTemplate | null>(null);
  const [creating, setCreating] = useState(false);

  const submit = async (values: PromptTemplateCreate) => {
    if (editingTemplate) {
      await updateTemplate.mutateAsync({ id: editingTemplate.id, data: values });
      setEditingTemplate(null);
      return;
    }

    await createTemplate.mutateAsync(values);
    setCreating(false);
  };

  return (
    <Card
      title={t("config.templates.title")}
      extra={
        <Button type="primary" disabled={!canWrite || !!error} onClick={() => setCreating(true)}>
          {t("config.templates.create")}
        </Button>
      }
    >
      {error ? (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          message={t("config.templates.loadError")}
          description={error.message}
        />
      ) : null}
      <Table<PromptTemplate>
        rowKey="id"
        loading={isLoading}
        dataSource={data}
        pagination={false}
        columns={[
          { title: t("config.templates.columns.name"), dataIndex: "name", key: "name" },
          {
            title: t("config.templates.columns.benchmark"),
            key: "benchmark",
            render: (_, record) => record.benchmark ?? t("config.templates.generic"),
          },
          { title: t("config.templates.columns.version"), dataIndex: "version", key: "version" },
          {
            title: t("config.templates.columns.status"),
            key: "status",
            render: (_, record) => (
              <Switch
                disabled={!canWrite}
                checked={record.is_active}
                onChange={(checked) =>
                  void updateTemplate.mutateAsync({ id: record.id, data: { is_active: checked } })
                }
              />
            ),
          },
          {
            title: t("config.templates.columns.actions"),
            key: "actions",
            render: (_, record) => (
              <Space>
                <Button type="link" disabled={!canWrite} onClick={() => setEditingTemplate(record)}>
                  {t("common.edit")}
                </Button>
                <Popconfirm
                  title={t("common.delete")}
                  onConfirm={() => void deleteTemplate.mutateAsync(record.id)}
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
      <TemplateFormModal
        open={creating || !!editingTemplate}
        template={editingTemplate}
        onSubmit={submit}
        onCancel={() => {
          setCreating(false);
          setEditingTemplate(null);
        }}
        loading={createTemplate.isPending || updateTemplate.isPending}
      />
    </Card>
  );
}
