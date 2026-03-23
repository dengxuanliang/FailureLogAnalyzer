import { Tabs, Typography } from "antd";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/contexts/AuthContext";
import AdaptersPanel from "./components/AdaptersPanel";
import RulesPanel from "./components/RulesPanel";
import StrategiesPanel from "./components/StrategiesPanel";
import TemplatesPanel from "./components/TemplatesPanel";
import UsersPanel from "./components/UsersPanel";
import ProviderSecretsPanel from "./components/ProviderSecretsPanel";

const { Title } = Typography;

export default function Config() {
  const { t } = useTranslation();
  const { user } = useAuth();

  const items = [
    {
      key: "rules",
      label: t("config.tabs.rules"),
      children: <RulesPanel />,
    },
    {
      key: "strategies",
      label: t("config.tabs.strategies"),
      children: <StrategiesPanel />,
    },
    {
      key: "templates",
      label: t("config.tabs.templates"),
      children: <TemplatesPanel />,
    },
    {
      key: "adapters",
      label: t("config.tabs.adapters"),
      children: <AdaptersPanel />,
    },
    ...(user?.role === "admin"
      ? [
          {
            key: "users",
            label: t("config.tabs.users"),
            children: <UsersPanel />,
          },
          {
            key: "provider-secrets",
            label: t("config.tabs.providerSecrets"),
            children: <ProviderSecretsPanel />,
          },
        ]
      : []),
  ];

  return (
    <>
      <Title level={4}>{t("config.title")}</Title>
      <Tabs defaultActiveKey="rules" items={items} destroyOnHidden />
    </>
  );
}
