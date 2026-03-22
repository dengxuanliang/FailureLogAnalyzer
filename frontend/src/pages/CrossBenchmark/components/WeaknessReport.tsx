import { Card, Descriptions, Empty, Skeleton, Typography } from "antd";
import { useTranslation } from "react-i18next";
import type { CrossBenchmarkWeaknessReport } from "@/api/queries/cross-benchmark";

const { Text } = Typography;

interface WeaknessReportProps {
  report: CrossBenchmarkWeaknessReport | null | undefined;
  loading: boolean;
}

export default function WeaknessReport({ report, loading }: WeaknessReportProps) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <Card title={t("cross.weakness.title")}>
        <Skeleton active paragraph={{ rows: 6 }} />
      </Card>
    );
  }

  if (!report) {
    return (
      <Card title={t("cross.weakness.title")}>
        <Empty description={t("cross.weakness.noReport")} />
      </Card>
    );
  }

  return (
    <Card title={t("cross.weakness.title")}>
      <Descriptions size="small" column={1} style={{ marginBottom: 16 }}>
        <Descriptions.Item label={t("cross.weakness.generatedAt")}>
          <Text type="secondary">{new Date(report.generated_at).toLocaleString()}</Text>
        </Descriptions.Item>
      </Descriptions>
      <pre
        style={{
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          fontFamily: "inherit",
          margin: 0,
          fontSize: 14,
          lineHeight: 1.7,
        }}
      >
        {report.summary}
      </pre>
    </Card>
  );
}
