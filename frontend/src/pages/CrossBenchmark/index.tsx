import { useCallback } from "react";
import { Alert, Button, Space, Typography } from "antd";
import { useTranslation } from "react-i18next";
import { useCrossBenchmarkMatrix, useWeaknessReport } from "@/api/queries/cross-benchmark";
import { useGlobalFilters } from "@/hooks/useGlobalFilters";
import CommonPatternsTable from "./components/CommonPatternsTable";
import HeatmapChart, { type HeatmapCellClickPayload } from "./components/HeatmapChart";
import WeaknessReport from "./components/WeaknessReport";

const { Title } = Typography;

export default function CrossBenchmark() {
  const { t } = useTranslation();
  const { setFilter } = useGlobalFilters();
  const matrix = useCrossBenchmarkMatrix();
  const report = useWeaknessReport();

  const handleCellClick = useCallback(
    ({ benchmark, model_version }: HeatmapCellClickPayload) => {
      setFilter("benchmark", benchmark);
      setFilter("model_version", model_version);
    },
    [setFilter],
  );

  if (matrix.isError || report.isError) {
    return (
      <Alert
        type="error"
        message={t("common.error")}
        action={
          <Button
            size="small"
            onClick={() => {
              if (matrix.isError) {
                void matrix.refetch();
              }

              if (report.isError) {
                void report.refetch();
              }
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
      <Title level={4}>{t("cross.title")}</Title>

      <HeatmapChart
        matrix={matrix.data ?? null}
        loading={matrix.isLoading}
        onCellClick={handleCellClick}
      />

      <WeaknessReport report={report.data ?? null} loading={report.isLoading} />

      <CommonPatternsTable
        patterns={report.data?.common_patterns ?? []}
        loading={report.isLoading}
      />
    </Space>
  );
}
