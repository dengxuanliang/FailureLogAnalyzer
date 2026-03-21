import { Card } from "antd";
import type { EChartsOption } from "echarts";
import { useTranslation } from "react-i18next";
import EChartsWrapper from "@/components/EChartsWrapper";
import type { DistributionItem } from "@/types/api";

interface ErrorTypeDonutProps {
  data: DistributionItem[];
  loading?: boolean;
}

export default function ErrorTypeDonut({
  data,
  loading,
}: ErrorTypeDonutProps) {
  const { t } = useTranslation();

  const option: EChartsOption = {
    tooltip: {
      trigger: "item",
      formatter: "{b}: {c} ({d}%)",
    },
    legend: {
      bottom: 0,
      type: "scroll",
    },
    series: [
      {
        type: "pie",
        radius: ["40%", "70%"],
        avoidLabelOverlap: true,
        label: { show: true, formatter: "{b}" },
        data: data.map((item) => ({ name: item.label, value: item.count })),
      },
    ],
  };

  return (
    <Card title={t("overview.errorDistribution")}>
      <EChartsWrapper option={option} height={350} loading={loading} />
    </Card>
  );
}
