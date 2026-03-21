import type { EChartsOption } from "echarts";
import { Skeleton } from "antd";
import ReactECharts from "echarts-for-react";

interface EChartsWrapperProps {
  option: EChartsOption;
  height?: number;
  loading?: boolean;
  onEvents?: Record<string, (params: unknown) => void>;
}

export default function EChartsWrapper({
  option,
  height = 400,
  loading,
  onEvents,
}: EChartsWrapperProps) {
  if (loading) {
    return <Skeleton active paragraph={{ rows: 6 }} />;
  }

  return (
    <ReactECharts
      option={option}
      style={{ height }}
      opts={{ renderer: "canvas" }}
      onEvents={onEvents}
      notMerge
    />
  );
}
