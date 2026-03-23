import { useCallback, useMemo, useState } from "react";
import { Alert, Button, Col, Empty, Row, Space, Typography } from "antd";
import { useTranslation } from "react-i18next";
import { useVersionComparison, useVersionDiff, useRadarData } from "../../api/queries/compare";
import { useSessions } from "../../api/queries/sessions";
import DiffSummary from "./components/DiffSummary";
import RadarChart from "./components/RadarChart";
import VersionSelector from "./components/VersionSelector";

const { Title } = Typography;

export default function Compare() {
  const { t } = useTranslation();
  const [versionA, setVersionA] = useState<string | null>(null);
  const [versionB, setVersionB] = useState<string | null>(null);

  const sessionsQuery = useSessions();
  const comparisonQuery = useVersionComparison(versionA, versionB);
  const diffQuery = useVersionDiff(versionA, versionB);
  const radarQuery = useRadarData(versionA, versionB);
  const { data: sessions } = sessionsQuery;
  const versions = useMemo(() => {
    if (!sessions) {
      return [];
    }

    return Array.from(new Set(sessions.map((session) => session.model_version))).sort();
  }, [sessions]);

  const { data: comparison, isLoading: comparisonLoading } = comparisonQuery;
  const { data: diff, isLoading: diffLoading } = diffQuery;
  const { data: radarData, isLoading: radarLoading } = radarQuery;

  const handleCompare = useCallback(() => {
    // Queries react to version selection; button exists for explicit user intent.
  }, []);

  if (
    sessionsQuery.isError ||
    comparisonQuery.isError ||
    diffQuery.isError ||
    radarQuery.isError
  ) {
    return (
      <Alert
        type="error"
        message={t("compare.loadError")}
        action={
          <Button
            size="small"
            onClick={() => {
              if (sessionsQuery.isError) void sessionsQuery.refetch();
              if (comparisonQuery.isError) void comparisonQuery.refetch();
              if (diffQuery.isError) void diffQuery.refetch();
              if (radarQuery.isError) void radarQuery.refetch();
            }}
          >
            {t("common.retry")}
          </Button>
        }
        showIcon
      />
    );
  }

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Title level={4}>{t("compare.title")}</Title>

      <VersionSelector
        versions={versions}
        versionA={versionA}
        versionB={versionB}
        onVersionAChange={setVersionA}
        onVersionBChange={setVersionB}
        onCompare={handleCompare}
        loading={comparisonLoading}
      />

      {!comparison && !comparisonLoading ? <Empty description={t("compare.noVersions")} /> : null}

      {comparison ? (
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <RadarChart
              data={radarData ?? null}
              versionA={versionA ?? comparison.version_a}
              versionB={versionB ?? comparison.version_b}
              loading={radarLoading}
            />
          </Col>
          <Col xs={24} lg={12}>
            <DiffSummary comparison={comparison} diff={diff ?? null} loading={diffLoading} />
          </Col>
        </Row>
      ) : null}
    </Space>
  );
}
