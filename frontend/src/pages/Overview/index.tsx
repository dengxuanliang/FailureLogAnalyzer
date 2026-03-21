import { Alert, Button, Col, Empty, Row } from "antd";
import {
  AlertOutlined,
  AimOutlined,
  DollarOutlined,
  FileTextOutlined,
  RobotOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { useAnalysisSummary, useErrorDistribution } from "@/api/queries/analysis";
import { useTrends } from "@/api/queries/trends";
import StatCard from "@/components/StatCard";
import ErrorTypeDonut from "./components/ErrorTypeDonut";
import TrendChart from "./components/TrendChart";

export default function Overview() {
  const { t } = useTranslation();
  const summary = useAnalysisSummary();
  const distribution = useErrorDistribution("error_type");
  const trends = useTrends();

  const isError = summary.isError || distribution.isError || trends.isError;
  const isLoading = summary.isLoading;

  if (isError) {
    return (
      <Alert
        type="error"
        message={t("common.error")}
        action={
          <Button
            size="small"
            onClick={() => {
              void summary.refetch();
              void distribution.refetch();
              void trends.refetch();
            }}
          >
            {t("common.retry")}
          </Button>
        }
        showIcon
      />
    );
  }

  if (summary.data && summary.data.total_sessions === 0) {
    return <Empty description={t("overview.noData")} />;
  }

  const data = summary.data;

  return (
    <>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={8} lg={4} xl={4}>
          <StatCard
            title={t("overview.totalSessions")}
            value={data?.total_sessions ?? 0}
            icon={<FileTextOutlined />}
            loading={isLoading}
          />
        </Col>
        <Col xs={24} sm={12} md={8} lg={5} xl={5}>
          <StatCard
            title={t("overview.totalErrors")}
            value={data?.total_errors ?? 0}
            icon={<AlertOutlined />}
            loading={isLoading}
          />
        </Col>
        <Col xs={24} sm={12} md={8} lg={5} xl={5}>
          <StatCard
            title={t("overview.accuracy")}
            value={data ? +(data.accuracy * 100).toFixed(1) : 0}
            icon={<AimOutlined />}
            suffix="%"
            loading={isLoading}
          />
        </Col>
        <Col xs={24} sm={12} md={8} lg={5} xl={5}>
          <StatCard
            title={t("overview.llmAnalysed")}
            value={data?.llm_analysed_count ?? 0}
            icon={<RobotOutlined />}
            loading={isLoading}
          />
        </Col>
        <Col xs={24} sm={12} md={8} lg={5} xl={5}>
          <StatCard
            title={t("overview.llmCost")}
            value={data ? `$${data.llm_total_cost.toFixed(2)}` : "$0.00"}
            icon={<DollarOutlined />}
            loading={isLoading}
          />
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <TrendChart
            data={trends.data?.data_points ?? []}
            loading={trends.isLoading}
          />
        </Col>
        <Col xs={24} lg={12}>
          <ErrorTypeDonut
            data={distribution.data ?? []}
            loading={distribution.isLoading}
          />
        </Col>
      </Row>
    </>
  );
}
