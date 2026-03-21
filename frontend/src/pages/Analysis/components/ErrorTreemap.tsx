import { ArrowLeftOutlined } from "@ant-design/icons";
import { Button, Card, Skeleton, Space } from "antd";
import { useTranslation } from "react-i18next";
import EChartsWrapper from "../../../components/EChartsWrapper";
import type { DistributionItem } from "../../../types/api";

interface ErrorTreemapProps {
  data: DistributionItem[];
  loading: boolean;
  onDrillDown: (label: string) => void;
  drillLevel?: number;
  breadcrumb?: string[];
  onBack?: () => void;
}

export default function ErrorTreemap({
  data,
  loading,
  onDrillDown,
  drillLevel = 0,
  breadcrumb = [],
  onBack,
}: ErrorTreemapProps) {
  const { t } = useTranslation();

  const option = {
    tooltip: {
      formatter: (params: { name: string; value: number }) =>
        `${params.name}<br/>${t("analysis.errorCount")}: ${params.value}`,
    },
    series: [
      {
        type: "treemap",
        data: data.map((item) => ({ name: item.label, value: item.count })),
        roam: false,
        nodeClick: false,
        breadcrumb: { show: false },
        label: {
          show: true,
          formatter: "{b}\n{c}",
          fontSize: 14,
        },
      },
    ],
  };

  const backLabel =
    drillLevel === 1
      ? t("analysis.backToL1")
      : drillLevel === 2
        ? t("analysis.backToL2")
        : "";

  return (
    <Card
      title={
        <Space>
          {drillLevel > 0 && onBack ? (
            <Button type="link" icon={<ArrowLeftOutlined />} onClick={onBack}>
              {backLabel}
            </Button>
          ) : null}
          <span>
            {t("analysis.treemapTitle")}
            {breadcrumb.length > 0 ? ` — ${breadcrumb.join(" > ")}` : ""}
          </span>
        </Space>
      }
    >
      {loading ? (
        <Skeleton active paragraph={{ rows: 8 }} />
      ) : (
        <EChartsWrapper
          option={option}
          height={400}
          onEvents={{
            click: (params: unknown) => {
              const name = (params as { name?: string }).name;
              if (name) {
                onDrillDown(name);
              }
            },
          }}
        />
      )}
    </Card>
  );
}
