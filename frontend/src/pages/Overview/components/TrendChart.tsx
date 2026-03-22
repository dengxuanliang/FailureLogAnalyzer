import { Card } from "antd";
import type { EChartsOption } from "echarts";
import { useTranslation } from "react-i18next";
import EChartsWrapper from "@/components/EChartsWrapper";
import type { TrendPoint } from "@/types/api";

interface TrendChartProps {
  data: TrendPoint[];
  loading?: boolean;
}

export default function TrendChart({ data, loading }: TrendChartProps) {
  const { t } = useTranslation();

  const option: EChartsOption = {
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "category",
      data: data.map((point) => point.period),
    },
    yAxis: {
      type: "value",
      name: "%",
      axisLabel: { formatter: "{value}%" },
    },
    series: [
      {
        type: "line",
        data: data.map((point) => +(point.error_rate * 100).toFixed(2)),
        smooth: true,
        areaStyle: { opacity: 0.1 },
      },
    ],
  };

  return (
    <Card title={t("overview.trendChart")}>
      <EChartsWrapper option={option} height={350} loading={loading} />
    </Card>
  );
}
