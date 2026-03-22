import { App, Layout, Menu } from "antd";
import {
  BarChartOutlined,
  BugOutlined,
  DashboardOutlined,
  LogoutOutlined,
  SettingOutlined,
  SwapOutlined,
} from "@ant-design/icons";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import AgentChatWindow from "@/components/AgentChatWindow";
import FilterBar from "@/components/FilterBar";
import { useAuth } from "@/contexts/AuthContext";
import { FilterProvider } from "@/contexts/FilterContext";

const { Content, Header, Sider } = Layout;

const menuItems = [
  { key: "/overview", icon: <DashboardOutlined />, labelKey: "nav.overview" },
  { key: "/analysis", icon: <BugOutlined />, labelKey: "nav.analysis" },
  { key: "/compare", icon: <SwapOutlined />, labelKey: "nav.compare" },
  {
    key: "/cross-benchmark",
    icon: <BarChartOutlined />,
    labelKey: "nav.crossBenchmark",
  },
  { key: "/config", icon: <SettingOutlined />, labelKey: "nav.config" },
] as const;

export default function AppLayout() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { logout } = useAuth();

  const items = [
    ...menuItems.map((item) => ({
      key: item.key,
      icon: item.icon,
      label: t(item.labelKey),
    })),
    {
      key: "logout",
      icon: <LogoutOutlined />,
      label: t("nav.logout"),
    },
  ];

  const handleMenuClick = ({ key }: { key: string }) => {
    if (key === "logout") {
      logout();
      navigate("/login", { replace: true });
      return;
    }

    navigate(key);
  };

  return (
    <App>
      <Layout style={{ minHeight: "100vh" }}>
        <Sider collapsible breakpoint="lg">
          <div
            style={{
              height: 48,
              margin: 12,
              color: "#fff",
              fontWeight: 600,
              fontSize: 14,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              whiteSpace: "nowrap",
              overflow: "hidden",
            }}
          >
            {t("app.title")}
          </div>
          <Menu
            theme="dark"
            mode="inline"
            selectedKeys={[location.pathname]}
            items={items}
            onClick={handleMenuClick}
          />
        </Sider>
        <FilterProvider>
          <Layout>
            <Header
              style={{
                background: "#fff",
                padding: "0 24px",
                display: "flex",
                alignItems: "center",
              }}
            >
              <FilterBar />
            </Header>
            <Content style={{ margin: 24 }}>
              <Outlet />
            </Content>
          </Layout>
          <AgentChatWindow />
        </FilterProvider>
      </Layout>
    </App>
  );
}
