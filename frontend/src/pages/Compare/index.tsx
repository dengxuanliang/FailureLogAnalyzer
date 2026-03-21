import { useCallback, useMemo, useState } from "react";
import { Col, Empty, Row, Space, Typography } from "antd";
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

  const { data: sessions } = useSessions();
  const versions = useMemo(() => {
    if (!sessions) {
      return [];
    }

    return Array.from(new Set(sessions.map((session) => session.model_version))).sort();
  }, [sessions]);

  const { data: comparison, isLoading: comparisonLoading } = useVersionComparison(versionA, versionB);
  const { data: diff, isLoading: diffLoading } = useVersionDiff(versionA, versionB);
  const { data: radarData, isLoading: radarLoading } = useRadarData(versionA, versionB);

  const handleCompare = useCallback(() => {
    // Queries react to version selection; button exists for explicit user intent.
  }, []);

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
