import { useCallback, useState } from "react";
import { Alert, Button, Empty, Space, Typography } from "antd";
import { useTranslation } from "react-i18next";
import {
  useErrorDistribution,
  useErrorRecords,
  useRecordDetail,
} from "../../api/queries/analysis";
import ErrorTable from "./components/ErrorTable";
import ErrorTreemap from "./components/ErrorTreemap";
import RecordDetail from "./components/RecordDetail";

const { Title } = Typography;

export default function Analysis() {
  const { t } = useTranslation();
  const [drillPath, setDrillPath] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [selectedRecordId, setSelectedRecordId] = useState<string | null>(null);

  const currentErrorType = drillPath.length > 0 ? drillPath.join(".") : undefined;
  const drillLevel = drillPath.length;

  const {
    data: distributionData,
    isLoading: distributionLoading,
    isError: distributionError,
    refetch: refetchDistribution,
  } = useErrorDistribution("error_type", currentErrorType);

  const {
    data: recordsData,
    isLoading: recordsLoading,
    isError: recordsError,
  } = useErrorRecords({ page, size: pageSize, errorType: currentErrorType });

  const { data: recordDetail } = useRecordDetail(selectedRecordId);

  const handleDrillDown = useCallback(
    (label: string) => {
      if (drillLevel >= 2) {
        return;
      }

      setDrillPath((previous) => [...previous, label]);
      setPage(1);
    },
    [drillLevel],
  );

  const handleBack = useCallback(() => {
    setDrillPath((previous) => previous.slice(0, -1));
    setPage(1);
  }, []);

  const handlePageChange = useCallback((nextPage: number, nextSize: number) => {
    setPage(nextPage);
    setPageSize(nextSize);
  }, []);

  const handleViewDetail = useCallback((recordId: string) => {
    setSelectedRecordId(recordId);
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedRecordId(null);
  }, []);

  if (distributionError || recordsError) {
    return (
      <Alert
        type="error"
        message={t("common.error")}
        action={
          <Button size="small" onClick={() => void refetchDistribution()}>
            {t("common.retry")}
          </Button>
        }
        showIcon
      />
    );
  }

  if (!distributionLoading && (!distributionData || distributionData.length === 0)) {
    return <Empty description={t("analysis.noErrors")} />;
  }

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Title level={4}>{t("analysis.title")}</Title>

      <ErrorTreemap
        data={distributionData ?? []}
        loading={distributionLoading}
        onDrillDown={handleDrillDown}
        drillLevel={drillLevel}
        breadcrumb={drillPath}
        onBack={handleBack}
      />

      <ErrorTable
        records={recordsData?.items ?? []}
        total={recordsData?.total ?? 0}
        page={page}
        size={pageSize}
        loading={recordsLoading}
        onPageChange={handlePageChange}
        onViewDetail={handleViewDetail}
      />

      <RecordDetail detail={recordDetail ?? null} open={Boolean(selectedRecordId)} onClose={handleCloseDetail} />
    </Space>
  );
}
