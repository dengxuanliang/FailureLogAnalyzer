import { Card, Descriptions, Empty, Space, Table, Tag, Typography, Skeleton } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useTranslation } from "react-i18next";
import type {
  DiffItem,
  VersionComparison,
  VersionDiff,
} from "../../../types/api";

interface DiffSummaryProps {
  comparison: VersionComparison | null;
  diff: VersionDiff | null;
  loading: boolean;
}

const buildColumns = (t: (key: string) => string): ColumnsType<DiffItem> => [
  {
    title: t("compare.diff.questionId"),
    dataIndex: "question_id",
    key: "question_id",
  },
  {
    title: t("compare.diff.benchmark"),
    dataIndex: "benchmark",
    key: "benchmark",
  },
  {
    title: t("compare.diff.category"),
    dataIndex: "task_category",
    key: "task_category",
    render: (value: DiffItem["task_category"]) => value ?? "-",
  },
];

const renderMetricValue = (from: number | string, to: number | string) => `${from} → ${to}`;

export default function DiffSummary({
  comparison,
  diff,
  loading,
}: DiffSummaryProps) {
  const { t } = useTranslation();

  if (loading || !comparison || !diff) {
    return (
      <Card title={t("compare.diff.title")}>
        <Skeleton active paragraph={{ rows: 6 }} />
      </Card>
    );
  }

  const hasChanges =
    diff.regressed.length > 0 ||
    diff.improved.length > 0 ||
    diff.new_errors.length > 0 ||
    diff.resolved_errors.length > 0;

  const columns = buildColumns(t);

  return (
    <Card title={t("compare.diff.title")}>
      <Descriptions bordered size="small" column={3} style={{ marginBottom: 16 }}>
        <Descriptions.Item label={t("compare.metrics.total")}>
          {renderMetricValue(comparison.metrics_a.total, comparison.metrics_b.total)}
        </Descriptions.Item>
        <Descriptions.Item label={t("compare.metrics.errors")}>
          {renderMetricValue(comparison.metrics_a.errors, comparison.metrics_b.errors)}
        </Descriptions.Item>
        <Descriptions.Item label={t("compare.metrics.accuracy")}>
          {renderMetricValue(
            `${(comparison.metrics_a.accuracy * 100).toFixed(1)}%`,
            `${(comparison.metrics_b.accuracy * 100).toFixed(1)}%`,
          )}
        </Descriptions.Item>
      </Descriptions>

      {hasChanges ? (
        <Space direction="vertical" size="large" style={{ width: "100%" }}>
          <section>
            <Typography.Title level={5}>{t("compare.diff.regressed")}</Typography.Title>
            <Table<DiffItem>
              columns={columns}
              dataSource={diff.regressed}
              rowKey="question_id"
              size="small"
              pagination={false}
            />
          </section>

          <section>
            <Typography.Title level={5}>{t("compare.diff.improved")}</Typography.Title>
            <Table<DiffItem>
              columns={columns}
              dataSource={diff.improved}
              rowKey="question_id"
              size="small"
              pagination={false}
            />
          </section>

          <section>
            <Typography.Title level={5}>{t("compare.diff.newErrors")}</Typography.Title>
            <Space wrap>
              {diff.new_errors.map((errorType) => (
                <Tag color="red" key={errorType}>
                  {errorType}
                </Tag>
              ))}
            </Space>
          </section>

          <section>
            <Typography.Title level={5}>{t("compare.diff.resolvedErrors")}</Typography.Title>
            <Space wrap>
              {diff.resolved_errors.map((errorType) => (
                <Tag color="green" key={errorType}>
                  {errorType}
                </Tag>
              ))}
            </Space>
          </section>
        </Space>
      ) : (
        <Empty description={t("compare.diff.noChanges")} />
      )}
    </Card>
  );
}
