import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import { RouterProvider } from "react-router-dom";
import { AgentChatProvider } from "@/contexts/AgentChatContext";
import { AuthProvider } from "@/contexts/AuthContext";
import { router } from "@/router";
import "@/i18n";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <AgentChatProvider>
            <RouterProvider router={router} />
          </AgentChatProvider>
        </AuthProvider>
      </QueryClientProvider>
    </ConfigProvider>
  );
}
