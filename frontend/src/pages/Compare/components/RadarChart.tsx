import { Card, Skeleton } from "antd";
import type { EChartsOption } from "echarts";
import { useTranslation } from "react-i18next";
import EChartsWrapper from "../../../components/EChartsWrapper";
import type { RadarData } from "../../../types/api";

interface RadarChartProps {
  data: RadarData | null;
  versionA: string;
  versionB: string;
  loading: boolean;
}

export default function RadarChart({
  data,
  versionA,
  versionB,
  loading,
}: RadarChartProps) {
  const { t } = useTranslation();

  if (loading || !data) {
    return (
      <Card title={t("compare.radar.title")}>
        <Skeleton active paragraph={{ rows: 8 }} />
      </Card>
    );
  }

  const option: EChartsOption = {
    tooltip: {},
    legend: {
      data: [versionA, versionB],
      bottom: 0,
    },
    radar: {
      indicator: data.dimensions.map((dimension) => ({
        name: dimension,
        max: 1,
      })),
    },
    series: [
      {
        type: "radar",
        data: [
          {
            value: data.scores_a,
            name: versionA,
            areaStyle: { opacity: 0.2 },
          },
          {
            value: data.scores_b,
            name: versionB,
            areaStyle: { opacity: 0.2 },
          },
        ],
      },
    ],
  };

  return (
    <Card title={t("compare.radar.title")}>
      <EChartsWrapper option={option} height={400} />
    </Card>
  );
}
