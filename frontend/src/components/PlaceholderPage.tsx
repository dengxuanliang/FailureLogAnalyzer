import { Result } from "antd";
import { useTranslation } from "react-i18next";

export default function PlaceholderPage() {
  const { t } = useTranslation();

  return <Result status="info" title={t("placeholder.comingSoon")} />;
}
