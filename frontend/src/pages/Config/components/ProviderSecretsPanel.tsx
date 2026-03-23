import { useState } from "react";
import { Alert, Button, Card, Popconfirm, Space, Table, Tag } from "antd";
import { useTranslation } from "react-i18next";
import {
  type ProviderSecret,
  type ProviderSecretCreate,
  type ProviderSecretUpdate,
  useCreateProviderSecret,
  useDeleteProviderSecret,
  useProviderSecrets,
  useUpdateProviderSecret,
} from "@/api/queries/config";
import ProviderSecretFormModal, { type ProviderSecretFormValues } from "./ProviderSecretFormModal";

export default function ProviderSecretsPanel() {
  const { t } = useTranslation();
  const { data = [], isLoading, error } = useProviderSecrets();
  const createMutation = useCreateProviderSecret();
  const updateMutation = useUpdateProviderSecret();
  const deleteMutation = useDeleteProviderSecret();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<ProviderSecret | null>(null);

  const handleCreate = async (values: ProviderSecretFormValues) => {
    const payload: ProviderSecretCreate = {
      provider: values.provider,
      name: values.name,
      secret: values.secret ?? "",
      is_active: values.is_active,
      is_default: values.is_default,
    };
    await createMutation.mutateAsync(payload);
    setCreating(false);
  };

  const handleEdit = async (values: ProviderSecretFormValues) => {
    if (!values.id) {
      return;
    }
    const payload: ProviderSecretUpdate = {
      provider: values.provider,
      name: values.name,
      is_active: values.is_active,
      is_default: values.is_default,
    };
    if (values.secret) {
      payload.secret = values.secret;
    }
    await updateMutation.mutateAsync({ id: values.id, data: payload });
    setEditing(null);
  };

  return (
    <Card
      title={t("config.providerSecrets.title")}
      extra={
        <Button type="primary" onClick={() => setCreating(true)} disabled={!!error}>
          {t("config.providerSecrets.create")}
        </Button>
      }
    >
      {error ? (
        <Alert
          type="error"
          showIcon
          message={t("config.providerSecrets.loadError")}
          description={error.message}
          style={{ marginBottom: 16 }}
        />
      ) : null}
      <Table<ProviderSecret>
        rowKey="id"
        loading={isLoading}
        dataSource={data}
        pagination={false}
        columns={[
          { title: t("config.providerSecrets.columns.provider"), dataIndex: "provider" },
          { title: t("config.providerSecrets.columns.name"), dataIndex: "name" },
          { title: t("config.providerSecrets.columns.mask"), dataIndex: "secret_mask" },
          {
            title: t("config.providerSecrets.columns.status"),
            key: "status",
            render: (_, row) => (
              <Tag color={row.is_active ? "green" : "default"}>
                {row.is_active ? t("config.providerSecrets.active") : t("config.providerSecrets.inactive")}
              </Tag>
            ),
          },
          {
            title: t("config.providerSecrets.columns.default"),
            key: "is_default",
            render: (_, row) =>
              row.is_default ? <Tag color="blue">{t("config.providerSecrets.defaultTag")}</Tag> : null,
          },
          {
            title: t("config.providerSecrets.columns.actions"),
            key: "actions",
            render: (_, row) => (
              <Space>
                <Button type="link" onClick={() => setEditing(row)}>
                  {t("common.edit")}
                </Button>
                {!row.is_default ? (
                  <Button
                    type="link"
                    onClick={() =>
                      void updateMutation.mutateAsync({
                        id: row.id,
                        data: { is_default: true, is_active: true },
                      })
                    }
                  >
                    {t("config.providerSecrets.makeDefault")}
                  </Button>
                ) : null}
                <Button
                  type="link"
                  onClick={() =>
                    void updateMutation.mutateAsync({
                      id: row.id,
                      data: { is_active: !row.is_active },
                    })
                  }
                >
                  {row.is_active ? t("config.providerSecrets.deactivate") : t("config.providerSecrets.activate")}
                </Button>
                <Popconfirm
                  title={t("config.providerSecrets.deleteConfirm")}
                  onConfirm={() => deleteMutation.mutateAsync(row.id)}
                >
                  <Button type="link" danger>
                    {t("common.delete")}
                  </Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />
      <ProviderSecretFormModal
        open={creating}
        onCancel={() => setCreating(false)}
        onSubmit={handleCreate}
        loading={createMutation.isPending}
      />
      <ProviderSecretFormModal
        open={!!editing}
        onCancel={() => setEditing(null)}
        onSubmit={handleEdit}
        loading={updateMutation.isPending}
        initialValues={
          editing
            ? {
                id: editing.id,
                provider: editing.provider,
                name: editing.name,
                is_active: editing.is_active,
                is_default: editing.is_default,
              }
            : undefined
        }
      />
    </Card>
  );
}
