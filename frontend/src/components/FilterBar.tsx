import { useMemo } from "react";
import { DatePicker, Select, Space, Typography } from "antd";
import dayjs from "dayjs";
import { useTranslation } from "react-i18next";
import { useSessions } from "@/api/queries/sessions";
import { useGlobalFilters } from "@/hooks/useGlobalFilters";

const { RangePicker } = DatePicker;
const { Text } = Typography;

export default function FilterBar() {
  const { t } = useTranslation();
  const { benchmark, model_version, time_range_start, time_range_end, setFilter } = useGlobalFilters();
  const { data: sessions, isLoading } = useSessions();

  const benchmarkOptions = useMemo(() => {
    if (!sessions) {
      return [];
    }

    return Array.from(new Set(sessions.map((session) => session.benchmark))).map((value) => ({
      label: value,
      value,
    }));
  }, [sessions]);

  const versionOptions = useMemo(() => {
    if (!sessions) {
      return [];
    }

    return Array.from(new Set(sessions.map((session) => session.model_version))).map((value) => ({
      label: value,
      value,
    }));
  }, [sessions]);

  const rangeValue = useMemo(() => {
    const start = time_range_start ? dayjs(time_range_start) : null;
    const end = time_range_end ? dayjs(time_range_end) : null;

    if (!start && !end) {
      return null;
    }

    return [start, end] as [dayjs.Dayjs | null, dayjs.Dayjs | null];
  }, [time_range_end, time_range_start]);

  return (
    <Space wrap size="middle">
      <Space>
        <Text>{t("filter.benchmark")}</Text>
        <Select
          data-testid="benchmark-select"
          allowClear
          showSearch
          placeholder={t("filter.benchmark")}
          value={benchmark}
          options={benchmarkOptions}
          loading={isLoading}
          onChange={(value) => setFilter("benchmark", value ?? null)}
          style={{ minWidth: 160 }}
        />
      </Space>

      <Space>
        <Text>{t("filter.modelVersion")}</Text>
        <Select
          data-testid="model-version-select"
          allowClear
          showSearch
          placeholder={t("filter.modelVersion")}
          value={model_version}
          options={versionOptions}
          loading={isLoading}
          onChange={(value) => setFilter("model_version", value ?? null)}
          style={{ minWidth: 160 }}
        />
      </Space>

      <Space>
        <Text>{t("filter.timeRange")}</Text>
        <RangePicker
          data-testid="time-range-picker"
          showTime
          value={rangeValue}
          onChange={(dates) => {
            setFilter("time_range_start", dates?.[0]?.toISOString() ?? null);
            setFilter("time_range_end", dates?.[1]?.toISOString() ?? null);
          }}
        />
      </Space>
    </Space>
  );
}
