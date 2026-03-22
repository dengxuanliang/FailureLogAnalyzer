import { useState } from "react";
import { Button, Card, Popconfirm, Space, Table, Tag } from "antd";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/contexts/AuthContext";
import {
  type UserCreate,
  type UserInfo,
  type UserUpdate,
  useCreateUser,
  useUpdateUser,
  useUsers,
} from "@/api/queries/config";
import UserFormModal from "./UserFormModal";

export default function UsersPanel() {
  const { t } = useTranslation();
  const { user: currentUser } = useAuth();
  const { data = [], isLoading } = useUsers();
  const createUser = useCreateUser();
  const updateUser = useUpdateUser();
  const [creating, setCreating] = useState(false);
  const [editingUser, setEditingUser] = useState<UserInfo | null>(null);

  const handleCreate = async (values: UserCreate) => {
    await createUser.mutateAsync(values);
    setCreating(false);
  };

  const handleUpdate = async (values: UserUpdate & { id: string }) => {
    await updateUser.mutateAsync(values);
    setEditingUser(null);
  };

  return (
    <Card
      title={t("config.users.title")}
      extra={
        <Button type="primary" onClick={() => setCreating(true)}>
          {t("config.users.create")}
        </Button>
      }
    >
      <Table<UserInfo>
        rowKey="id"
        loading={isLoading}
        dataSource={data}
        pagination={false}
        columns={[
          { title: t("config.users.columns.username"), dataIndex: "username", key: "username" },
          { title: t("config.users.columns.email"), dataIndex: "email", key: "email" },
          {
            title: t("config.users.columns.role"),
            key: "role",
            render: (_, record) => <Tag>{t(`config.users.role.${record.role}`)}</Tag>,
          },
          {
            title: t("config.users.columns.status"),
            key: "status",
            render: (_, record) => (
              <Tag>{record.is_active ? t("config.users.active") : t("config.users.inactive")}</Tag>
            ),
          },
          {
            title: t("config.users.columns.createdAt"),
            dataIndex: "created_at",
            key: "createdAt",
          },
          {
            title: t("config.users.columns.actions"),
            key: "actions",
            render: (_, record) => (
              <Space>
                <Button type="link" onClick={() => setEditingUser(record)}>
                  {t("common.edit")}
                </Button>
                <Popconfirm
                  title={record.is_active ? t("config.users.deactivate") : t("config.users.activate")}
                  onConfirm={() =>
                    void updateUser.mutateAsync({
                      id: record.id,
                      is_active: !record.is_active,
                    })
                  }
                  disabled={record.id === currentUser?.id}
                >
                  <Button type="link" disabled={record.id === currentUser?.id}>
                    {record.is_active ? t("config.users.deactivate") : t("config.users.activate")}
                  </Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />
      <UserFormModal
        open={creating}
        onSubmit={handleCreate}
        onCancel={() => setCreating(false)}
        loading={createUser.isPending}
      />
      <UserFormModal
        open={!!editingUser}
        onSubmit={handleUpdate}
        onCancel={() => setEditingUser(null)}
        initialValues={
          editingUser
            ? {
                id: editingUser.id,
                username: editingUser.username,
                email: editingUser.email,
                role: editingUser.role,
              }
            : undefined
        }
        loading={updateUser.isPending}
      />
    </Card>
  );
}
