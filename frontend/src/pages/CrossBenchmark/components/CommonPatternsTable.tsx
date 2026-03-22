import { Card, Empty, Space, Table, Tag } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useTranslation } from "react-i18next";
import type { CommonErrorPattern } from "@/api/queries/cross-benchmark";

interface CommonPatternsTableProps {
  patterns: CommonErrorPattern[];
  loading: boolean;
}

export default function CommonPatternsTable({
  patterns,
  loading,
}: CommonPatternsTableProps) {
  const { t } = useTranslation();

  const columns: ColumnsType<CommonErrorPattern> = [
    {
      title: t("cross.patterns.columns.errorType"),
      dataIndex: "error_type",
      key: "error_type",
    },
    {
      title: t("cross.patterns.columns.benchmarks"),
      dataIndex: "affected_benchmarks",
      key: "affected_benchmarks",
      render: (benchmarks: string[]) => (
        <Space wrap size={[4, 4]}>
          {benchmarks.map((benchmark) => (
            <Tag color="blue" key={benchmark}>
              {benchmark}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: t("cross.patterns.columns.avgErrorRate"),
      dataIndex: "avg_error_rate",
      key: "avg_error_rate",
      align: "right",
      render: (value: number) => `${(value * 100).toFixed(1)}%`,
    },
    {
      title: t("cross.patterns.columns.recordCount"),
      dataIndex: "record_count",
      key: "record_count",
      align: "right",
    },
  ];

  return (
    <Card title={t("cross.patterns.title")}>
      {patterns.length === 0 && !loading ? (
        <Empty description={t("cross.patterns.noData")} />
      ) : (
        <Table<CommonErrorPattern>
          columns={columns}
          dataSource={patterns}
          loading={loading}
          pagination={{ pageSize: 10, hideOnSinglePage: true }}
          rowKey="error_type"
          size="small"
        />
      )}
    </Card>
  );
}
