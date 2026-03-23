import { Alert, Card, Space, Table, Tag, Typography } from "antd";
import { useTranslation } from "react-i18next";
import { type BenchmarkAdapter, useAdapters } from "@/api/queries/config";

export default function AdaptersPanel() {
  const { t } = useTranslation();
  const { data = [], isLoading, error } = useAdapters();

  return (
    <Card
      title={t("config.adapters.title")}
      extra={<Typography.Text type="secondary">{t("config.adapters.description")}</Typography.Text>}
    >
      {error ? (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          message={t("config.adapters.loadError")}
          description={error.message}
        />
      ) : null}
      <Table<BenchmarkAdapter>
        rowKey="name"
        loading={isLoading}
        dataSource={data}
        pagination={false}
        columns={[
          { title: t("config.adapters.columns.name"), dataIndex: "name", key: "name" },
          { title: t("config.adapters.columns.description"), dataIndex: "description", key: "description" },
          {
            title: t("config.adapters.columns.fields"),
            key: "fields",
            render: (_, record) => (
              <Space wrap>
                {record.detected_fields.map((field) => (
                  <Tag key={field}>{field}</Tag>
                ))}
              </Space>
            ),
          },
          {
            title: t("config.adapters.columns.builtin"),
            key: "builtin",
            render: (_, record) => (
              <Tag>{record.is_builtin ? t("config.adapters.builtin") : t("config.adapters.custom")}</Tag>
            ),
          },
        ]}
      />
    </Card>
  );
}
