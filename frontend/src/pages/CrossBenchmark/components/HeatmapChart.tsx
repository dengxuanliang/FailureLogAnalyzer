import { Card, Empty, Skeleton } from "antd";
import type { EChartsOption } from "echarts";
import { useTranslation } from "react-i18next";
import EChartsWrapper from "@/components/EChartsWrapper";
import type { CrossBenchmarkMatrix } from "@/api/queries/cross-benchmark";

export interface HeatmapCellClickPayload {
  benchmark: string;
  model_version: string;
  error_rate: number;
}

interface HeatmapChartProps {
  matrix: CrossBenchmarkMatrix | null;
  loading: boolean;
  onCellClick: (payload: HeatmapCellClickPayload) => void;
}

export default function HeatmapChart({
  matrix,
  loading,
  onCellClick,
}: HeatmapChartProps) {
  const { t } = useTranslation();

  if (loading || !matrix) {
    return (
      <Card title={t("cross.heatmap.title")}>
        <Skeleton active paragraph={{ rows: 8 }} />
      </Card>
    );
  }

  if (matrix.cells.length === 0) {
    return (
      <Card title={t("cross.heatmap.title")}>
        <Empty description={t("cross.heatmap.noData")} />
      </Card>
    );
  }

  const seriesData = matrix.cells.map((cell) => [
    matrix.benchmarks.indexOf(cell.benchmark),
    matrix.model_versions.indexOf(cell.model_version),
    cell.error_rate,
  ]);

  const option: EChartsOption = {
    tooltip: {
      formatter: (params) => {
        const tuple = ((params as { value?: unknown }).value ?? []) as number[];
        if (tuple.length < 3) {
          return "";
        }

        const [benchmarkIndex, versionIndex, rate] = tuple;

        return [
          `${t("cross.heatmap.yAxisLabel")}: ${matrix.model_versions[versionIndex]}`,
          `${t("cross.heatmap.xAxisLabel")}: ${matrix.benchmarks[benchmarkIndex]}`,
          `${t("cross.heatmap.tooltip")}: ${(rate * 100).toFixed(1)}%`,
        ].join("<br/>");
      },
    },
    grid: { top: 24, left: 80, right: 24, bottom: 60 },
    xAxis: {
      type: "category",
      data: matrix.benchmarks,
      name: t("cross.heatmap.xAxisLabel"),
      axisLabel: { rotate: 30 },
    },
    yAxis: {
      type: "category",
      data: matrix.model_versions,
      name: t("cross.heatmap.yAxisLabel"),
    },
    visualMap: {
      min: 0,
      max: 1,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      calculable: true,
      inRange: {
        color: ["#fff5f0", "#fc8d59", "#d73027"],
      },
    },
    series: [
      {
        type: "heatmap",
        data: seriesData,
        label: {
          show: true,
          formatter: (params) => {
            const tuple = ((params as { value?: unknown }).value ?? []) as number[];
            const rate = tuple[2] ?? 0;
            return `${(rate * 100).toFixed(0)}%`;
          },
        },
      },
    ],
  };

  const handleCellClick = (params: { value?: unknown }) => {
    const tuple = (params.value ?? []) as number[];
    if (tuple.length < 3) {
      return;
    }

    const [benchmarkIndex, versionIndex, error_rate] = tuple;

    onCellClick({
      benchmark: matrix.benchmarks[benchmarkIndex],
      model_version: matrix.model_versions[versionIndex],
      error_rate,
    });
  };

  return (
    <Card title={t("cross.heatmap.title")}>
      <EChartsWrapper
        option={option}
        height={Math.max(320, matrix.model_versions.length * 60 + 80)}
        onEvents={{ click: handleCellClick as (params: unknown) => void }}
      />
    </Card>
  );
}
