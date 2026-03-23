import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

const proxyTarget = process.env.VITE_PROXY_TARGET || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  build: {
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) {
            return undefined;
          }

          if (id.includes("echarts") || id.includes("zrender")) {
            return "charts-vendor";
          }

          if (id.includes("antd") || id.includes("@ant-design") || id.includes("rc-")) {
            return "ui-vendor";
          }

          return "vendor";
        },
      },
    },
  },
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: proxyTarget,
        changeOrigin: true,
      },
    },
  },
});
