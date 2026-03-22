import { Button, Card, Select, Space } from "antd";
import { SwapOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";

interface VersionSelectorProps {
  versions: string[];
  versionA: string | null;
  versionB: string | null;
  onVersionAChange: (version: string) => void;
  onVersionBChange: (version: string) => void;
  onCompare: () => void;
  loading: boolean;
}

export default function VersionSelector({
  versions,
  versionA,
  versionB,
  onVersionAChange,
  onVersionBChange,
  onCompare,
  loading,
}: VersionSelectorProps) {
  const { t } = useTranslation();

  const options = versions.map((version) => ({
    label: version,
    value: version,
  }));

  return (
    <Card>
      <Space size="middle" wrap>
        <Select
          placeholder={t("compare.selectVersionA")}
          value={versionA}
          onChange={onVersionAChange}
          options={options}
          style={{ width: 200 }}
          showSearch
        />
        <Select
          placeholder={t("compare.selectVersionB")}
          value={versionB}
          onChange={onVersionBChange}
          options={options}
          style={{ width: 200 }}
          showSearch
        />
        <Button
          type="primary"
          icon={<SwapOutlined />}
          onClick={onCompare}
          disabled={!versionA || !versionB}
          loading={loading}
        >
          {t("compare.compare")}
        </Button>
      </Space>
    </Card>
  );
}
