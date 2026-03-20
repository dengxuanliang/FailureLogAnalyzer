# Frontend Foundation & Overview Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up the React frontend project with build tooling, routing, authentication, i18n, global layout, and the Overview dashboard page with KPI cards and charts.

**Architecture:** Vite-based React 18 + TypeScript SPA. Ant Design provides the component library and layout system. TanStack Query manages server state with auto-refetching on filter changes. Global filters (benchmark, model version, time range) live in React Context and sync to URL query params. ECharts renders the trend line chart and error distribution donut chart.

**Tech Stack:** Vite 5, React 18, TypeScript 5, Ant Design 5, ECharts 5 (echarts-for-react), TanStack Query v5, React Router v6, Axios, react-i18next, Jest + React Testing Library

---

## File Structure

```
frontend/
  public/
  src/
    api/
      client.ts              # Axios instance: base URL, JWT interceptor, 401 redirect
      queries/
        analysis.ts          # useAnalysisSummary, useErrorDistribution hooks
        sessions.ts          # useSessions hook
        trends.ts            # useTrends hook
    components/
      StatCard.tsx           # Reusable KPI metric card
      StatCard.test.tsx
      FilterBar.tsx          # Global filter bar (benchmark, model version, time range)
      FilterBar.test.tsx
      EChartsWrapper.tsx     # Reusable ECharts container with auto-resize
      EChartsWrapper.test.tsx
      PlaceholderPage.tsx    # "Coming Soon" placeholder for unimplemented routes
    contexts/
      FilterContext.tsx      # Global filter state (benchmark, model_version, time_range)
      AuthContext.tsx        # JWT token, current user, login/logout
    hooks/
      useGlobalFilters.ts   # Convenience hook for FilterContext
    layouts/
      AppLayout.tsx          # Sidebar nav + top filter bar + content area
      AppLayout.test.tsx
    locales/
      zh.json                # Chinese translations
      en.json                # English translations
    pages/
      Login/
        index.tsx            # Login page
        Login.test.tsx
      Overview/
        index.tsx            # Overview dashboard page
        Overview.test.tsx
        components/
          TrendChart.tsx     # Error rate trend line chart (ECharts)
          ErrorTypeDonut.tsx # L1 error distribution donut chart (ECharts)
    types/
      api.ts                 # TypeScript interfaces matching backend API schemas
    App.tsx                  # Root component: providers + router
    main.tsx                 # Entry point
    router.tsx               # Route definitions with ProtectedRoute
    i18n.ts                  # i18next initialization
  .env.example               # VITE_API_BASE_URL=http://localhost:8000/api/v1
  index.html
  package.json
  tsconfig.json
  vite.config.ts
  jest.config.ts
  setupTests.ts
```

---

## Task 1: Project Scaffolding & Build Tooling

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/.env.example`
- Create: `frontend/jest.config.ts`
- Create: `frontend/setupTests.ts`

- [ ] **Step 1: Initialize frontend directory and package.json**

```bash
cd frontend
npm init -y
```

- [ ] **Step 2: Install core dependencies**

```bash
npm install react@18 react-dom@18 antd@5 @ant-design/icons echarts echarts-for-react \
  @tanstack/react-query@5 react-router-dom@6 axios react-i18next i18next i18next-browser-languagedetector
```

- [ ] **Step 3: Install dev dependencies**

```bash
npm install -D typescript@5 @types/react @types/react-dom vite@5 @vitejs/plugin-react \
  eslint prettier jest @jest/globals ts-jest @testing-library/react @testing-library/jest-dom \
  @testing-library/user-event jest-environment-jsdom @types/jest identity-obj-proxy
```

- [ ] **Step 4: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src"]
}
```

- [ ] **Step 5: Create vite.config.ts**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

- [ ] **Step 6: Create index.html**

```html
<!DOCTYPE html>
<html lang="zh">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>FailureLogAnalyzer</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 7: Create src/main.tsx entry point**

```typescript
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 8: Create src/App.tsx placeholder**

```typescript
const App: React.FC = () => {
  return <div>FailureLogAnalyzer</div>;
};

export default App;
```

- [ ] **Step 9: Create .env.example**

```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

- [ ] **Step 10: Create jest.config.ts**

```typescript
import type { Config } from "jest";

const config: Config = {
  testEnvironment: "jsdom",
  transform: {
    "^.+\\.tsx?$": [
      "ts-jest",
      {
        tsconfig: "tsconfig.json",
        jsx: "react-jsx",
      },
    ],
  },
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1",
    "\\.(css|less)$": "identity-obj-proxy",
  },
  setupFilesAfterEnv: ["<rootDir>/setupTests.ts"],
};

export default config;
```

- [ ] **Step 11: Create setupTests.ts**

```typescript
import "@testing-library/jest-dom";
```

- [ ] **Step 12: Add scripts to package.json**

Add these scripts to `package.json`:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "jest",
    "test:watch": "jest --watch",
    "lint": "eslint src --ext .ts,.tsx"
  }
}
```

- [ ] **Step 13: Verify build works**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 14: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): scaffold Vite + React + TypeScript project"
```

---

## Task 2: TypeScript API Types

**Files:**
- Create: `frontend/src/types/api.ts`

- [ ] **Step 1: Create TypeScript interfaces matching backend Pydantic schemas**

Create `frontend/src/types/api.ts`:

```typescript
// === Auth ===

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface JwtPayload {
  sub: string; // user UUID
  role: "admin" | "analyst" | "viewer";
  exp: number;
}

export interface ApiError {
  status: number;
  message: string;
  detail?: unknown;
}

// === Sessions ===

export interface EvalSession {
  id: string;
  model: string;
  model_version: string;
  benchmark: string;
  dataset_name: string | null;
  total_count: number;
  error_count: number;
  accuracy: number;
  tags: string[];
  created_at: string;
}

// === Analysis ===

export interface AnalysisSummary {
  total_sessions: number;
  total_records: number;
  total_errors: number;
  accuracy: number;
  llm_analysed_count: number;
  llm_total_cost: number;
}

export interface DistributionItem {
  label: string;
  count: number;
  percentage: number;
}

export interface ErrorRecordBrief {
  id: string;
  session_id: string;
  benchmark: string;
  task_category: string | null;
  question_id: string | null;
  question: string;
  is_correct: boolean;
  score: number | null;
  error_tags: string[];
  has_llm_analysis: boolean;
}

export interface PaginatedRecords {
  items: ErrorRecordBrief[];
  total: number;
  page: number;
  size: number;
}

export interface AnalysisResultDetail {
  id: string;
  analysis_type: string;
  error_types: string[];
  root_cause: string | null;
  severity: string | null;
  confidence: number | null;
  evidence: string | null;
  suggestion: string | null;
  llm_model: string | null;
  llm_cost: number | null;
  unmatched_tags: string[];
  created_at: string;
}

export interface RecordDetail {
  record: Record<string, unknown>;
  analysis_results: AnalysisResultDetail[];
  error_tags: Record<string, unknown>[];
}

// === Trends ===

export interface TrendPoint {
  period: string;
  error_rate: number;
  total: number;
  errors: number;
}

export interface ErrorTrends {
  data_points: TrendPoint[];
}

// === Compare ===

export interface VersionMetrics {
  total: number;
  errors: number;
  accuracy: number;
  error_type_distribution: Record<string, number>;
}

export interface VersionComparison {
  version_a: string;
  version_b: string;
  benchmark: string | null;
  metrics_a: VersionMetrics;
  metrics_b: VersionMetrics;
}

export interface DiffItem {
  question_id: string;
  benchmark: string;
  task_category: string | null;
  question: string;
}

export interface VersionDiff {
  regressed: DiffItem[];
  improved: DiffItem[];
  new_errors: string[];
  resolved_errors: string[];
}

export interface RadarData {
  dimensions: string[];
  scores_a: number[];
  scores_b: number[];
}

// === Cross-Benchmark ===

export interface BenchmarkMatrix {
  models: string[];
  benchmarks: string[];
  matrix: number[][];
}

export interface Weakness {
  error_type: string;
  benchmarks: string[];
  frequency: number;
}

export interface SystematicWeaknesses {
  weaknesses: Weakness[];
}

// === Global Filters ===

export interface GlobalFilters {
  benchmark: string | null;
  model_version: string | null;
  time_range_start: string | null;
  time_range_end: string | null;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/api.ts
git commit -m "feat(frontend): add TypeScript API types matching backend schemas"
```

---

## Task 3: Axios Client & Error Handling

**Files:**
- Create: `frontend/src/api/client.ts`

- [ ] **Step 1: Create the Axios client with JWT interceptor and 401 handling**

Create `frontend/src/api/client.ts`:

```typescript
import axios from "axios";
import type { ApiError } from "@/types/api";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error)) {
      if (error.response?.status === 401) {
        localStorage.removeItem("token");
        window.location.href = "/login";
        return Promise.reject(error);
      }
      const apiError: ApiError = {
        status: error.response?.status ?? 0,
        message:
          error.response?.data?.detail ??
          error.response?.data?.message ??
          error.message,
        detail: error.response?.data,
      };
      return Promise.reject(apiError);
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat(frontend): add Axios client with JWT interceptor and error handling"
```

---

## Task 4: i18n Setup

**Files:**
- Create: `frontend/src/i18n.ts`
- Create: `frontend/src/locales/zh.json`
- Create: `frontend/src/locales/en.json`

- [ ] **Step 1: Create i18n configuration**

Create `frontend/src/i18n.ts`:

```typescript
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import zh from "./locales/zh.json";
import en from "./locales/en.json";

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      zh: { translation: zh },
      en: { translation: en },
    },
    fallbackLng: "zh",
    interpolation: { escapeValue: false },
  });

export default i18n;
```

- [ ] **Step 2: Create Chinese locale file**

Create `frontend/src/locales/zh.json`:

```json
{
  "app.title": "评测日志错因分析",
  "nav.overview": "总览",
  "nav.analysis": "错因分析",
  "nav.compare": "版本对比",
  "nav.crossBenchmark": "横向分析",
  "nav.config": "分析配置",
  "nav.logout": "退出",
  "filter.benchmark": "Benchmark",
  "filter.modelVersion": "模型版本",
  "filter.timeRange": "时间范围",
  "overview.totalSessions": "总评测数",
  "overview.totalErrors": "错题总数",
  "overview.accuracy": "整体准确率",
  "overview.llmAnalysed": "LLM 已分析数",
  "overview.llmCost": "LLM 分析成本",
  "overview.trendChart": "错误率趋势",
  "overview.errorDistribution": "L1 错误类型分布",
  "overview.noData": "还没有评测数据，请先上传评测日志",
  "placeholder.comingSoon": "功能开发中，敬请期待",
  "login.title": "登录",
  "login.username": "用户名",
  "login.password": "密码",
  "login.submit": "登录",
  "login.failed": "用户名或密码错误",
  "common.retry": "重试",
  "common.loading": "加载中...",
  "common.error": "加载失败"
}
```

- [ ] **Step 3: Create English locale file**

Create `frontend/src/locales/en.json`:

```json
{
  "app.title": "Failure Log Analyzer",
  "nav.overview": "Overview",
  "nav.analysis": "Error Analysis",
  "nav.compare": "Version Compare",
  "nav.crossBenchmark": "Cross-Benchmark",
  "nav.config": "Configuration",
  "nav.logout": "Logout",
  "filter.benchmark": "Benchmark",
  "filter.modelVersion": "Model Version",
  "filter.timeRange": "Time Range",
  "overview.totalSessions": "Total Sessions",
  "overview.totalErrors": "Total Errors",
  "overview.accuracy": "Accuracy",
  "overview.llmAnalysed": "LLM Analysed",
  "overview.llmCost": "LLM Cost",
  "overview.trendChart": "Error Rate Trend",
  "overview.errorDistribution": "L1 Error Type Distribution",
  "overview.noData": "No evaluation data yet. Please upload evaluation logs first.",
  "placeholder.comingSoon": "Coming soon",
  "login.title": "Login",
  "login.username": "Username",
  "login.password": "Password",
  "login.submit": "Login",
  "login.failed": "Invalid username or password",
  "common.retry": "Retry",
  "common.loading": "Loading...",
  "common.error": "Failed to load"
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/i18n.ts frontend/src/locales/
git commit -m "feat(frontend): add i18n with Chinese and English locale files"
```

---

## Task 5: AuthContext & Login Page

**Files:**
- Create: `frontend/src/contexts/AuthContext.tsx`
- Create: `frontend/src/pages/Login/index.tsx`
- Create: `frontend/src/pages/Login/Login.test.tsx`

- [ ] **Step 1: Write the Login page test**

Create `frontend/src/pages/Login/Login.test.tsx`:

```typescript
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import Login from "./index";

// Mock i18n
jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "login.title": "登录",
        "login.username": "用户名",
        "login.password": "密码",
        "login.submit": "登录",
        "login.failed": "用户名或密码错误",
      };
      return map[key] ?? key;
    },
  }),
}));

// Mock axios client
jest.mock("@/api/client", () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
  },
}));

import apiClient from "@/api/client";
const mockPost = apiClient.post as jest.Mock;

const renderLogin = () =>
  render(
    <MemoryRouter>
      <AuthProvider>
        <Login />
      </AuthProvider>
    </MemoryRouter>
  );

describe("Login page", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  it("renders login form", () => {
    renderLogin();
    expect(screen.getByText("登录")).toBeInTheDocument();
    expect(screen.getByLabelText("用户名")).toBeInTheDocument();
    expect(screen.getByLabelText("密码")).toBeInTheDocument();
  });

  it("shows error on failed login", async () => {
    mockPost.mockRejectedValueOnce({ status: 401, message: "Unauthorized" });
    renderLogin();

    await userEvent.type(screen.getByLabelText("用户名"), "bad");
    await userEvent.type(screen.getByLabelText("密码"), "bad");
    await userEvent.click(screen.getByRole("button", { name: "登录" }));

    await waitFor(() => {
      expect(screen.getByText("用户名或密码错误")).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/pages/Login/Login.test.tsx --no-cache`
Expected: FAIL — modules not found

- [ ] **Step 3: Create AuthContext**

Create `frontend/src/contexts/AuthContext.tsx`:

```typescript
import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import apiClient from "@/api/client";
import type { JwtPayload } from "@/types/api";

interface User {
  id: string;
  role: "admin" | "analyst" | "viewer";
}

interface AuthState {
  token: string | null;
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

function decodeJwtPayload(token: string): JwtPayload {
  const base64 = token.split(".")[1];
  const json = atob(base64);
  return JSON.parse(json);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem("token");
    if (stored) {
      try {
        const payload = decodeJwtPayload(stored);
        if (payload.exp * 1000 > Date.now()) {
          setToken(stored);
          setUser({ id: payload.sub, role: payload.role });
        } else {
          localStorage.removeItem("token");
        }
      } catch {
        localStorage.removeItem("token");
      }
    }
    setLoading(false);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const form = new URLSearchParams();
    form.append("username", username);
    form.append("password", password);
    const { data } = await apiClient.post("/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    const accessToken: string = data.access_token;
    localStorage.setItem("token", accessToken);
    const payload = decodeJwtPayload(accessToken);
    setToken(accessToken);
    setUser({ id: payload.sub, role: payload.role });
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ token, user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
```

- [ ] **Step 4: Create Login page**

Create `frontend/src/pages/Login/index.tsx`:

```typescript
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Form, Input, Button, Card, Typography, Alert, Space } from "antd";
import { UserOutlined, LockOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/contexts/AuthContext";

const { Title } = Typography;

export default function Login() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onFinish = async (values: { username: string; password: string }) => {
    setError(null);
    setSubmitting(true);
    try {
      await login(values.username, values.password);
      navigate("/overview", { replace: true });
    } catch {
      setError(t("login.failed"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "100vh",
        background: "#f0f2f5",
      }}
    >
      <Card style={{ width: 400 }}>
        <Space direction="vertical" size="large" style={{ width: "100%" }}>
          <Title level={3} style={{ textAlign: "center", marginBottom: 0 }}>
            {t("login.title")}
          </Title>
          {error && <Alert type="error" message={error} showIcon />}
          <Form onFinish={onFinish} autoComplete="off">
            <Form.Item
              name="username"
              label={t("login.username")}
              rules={[{ required: true }]}
            >
              <Input prefix={<UserOutlined />} />
            </Form.Item>
            <Form.Item
              name="password"
              label={t("login.password")}
              rules={[{ required: true }]}
            >
              <Input.Password prefix={<LockOutlined />} />
            </Form.Item>
            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                loading={submitting}
                block
              >
                {t("login.submit")}
              </Button>
            </Form.Item>
          </Form>
        </Space>
      </Card>
    </div>
  );
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontend && npx jest src/pages/Login/Login.test.tsx --no-cache`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/contexts/AuthContext.tsx frontend/src/pages/Login/
git commit -m "feat(frontend): add AuthContext with JWT handling and Login page"
```

---

## Task 6: FilterContext & Global Filters Hook

**Files:**
- Create: `frontend/src/contexts/FilterContext.tsx`
- Create: `frontend/src/hooks/useGlobalFilters.ts`

- [ ] **Step 1: Create FilterContext**

Create `frontend/src/contexts/FilterContext.tsx`:

```typescript
import {
  createContext,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from "react";
import { useSearchParams } from "react-router-dom";
import type { GlobalFilters } from "@/types/api";

interface FilterState extends GlobalFilters {
  setFilter: <K extends keyof GlobalFilters>(
    key: K,
    value: GlobalFilters[K]
  ) => void;
  resetFilters: () => void;
}

const defaults: GlobalFilters = {
  benchmark: null,
  model_version: null,
  time_range_start: null,
  time_range_end: null,
};

export const FilterContext = createContext<FilterState>({
  ...defaults,
  setFilter: () => {},
  resetFilters: () => {},
});

export function FilterProvider({ children }: { children: ReactNode }) {
  const [searchParams, setSearchParams] = useSearchParams();

  const [filters, setFilters] = useState<GlobalFilters>(() => ({
    benchmark: searchParams.get("benchmark"),
    model_version: searchParams.get("model_version"),
    time_range_start: searchParams.get("time_range_start"),
    time_range_end: searchParams.get("time_range_end"),
  }));

  // Sync filters → URL query params
  useEffect(() => {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) {
      if (value) params.set(key, value);
    }
    setSearchParams(params, { replace: true });
  }, [filters, setSearchParams]);

  const setFilter = useCallback(
    <K extends keyof GlobalFilters>(key: K, value: GlobalFilters[K]) => {
      setFilters((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  const resetFilters = useCallback(() => {
    setFilters(defaults);
  }, []);

  return (
    <FilterContext.Provider value={{ ...filters, setFilter, resetFilters }}>
      {children}
    </FilterContext.Provider>
  );
}
```

- [ ] **Step 2: Create useGlobalFilters hook**

Create `frontend/src/hooks/useGlobalFilters.ts`:

```typescript
import { useContext } from "react";
import { FilterContext } from "@/contexts/FilterContext";

export function useGlobalFilters() {
  return useContext(FilterContext);
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/contexts/FilterContext.tsx frontend/src/hooks/useGlobalFilters.ts
git commit -m "feat(frontend): add FilterContext with URL query param sync"
```

---

## Task 7: TanStack Query Hooks

**Files:**
- Create: `frontend/src/api/queries/sessions.ts`
- Create: `frontend/src/api/queries/analysis.ts`
- Create: `frontend/src/api/queries/trends.ts`

- [ ] **Step 1: Create sessions query hook**

Create `frontend/src/api/queries/sessions.ts`:

```typescript
import { useQuery } from "@tanstack/react-query";
import apiClient from "@/api/client";
import type { EvalSession } from "@/types/api";

export function useSessions() {
  return useQuery({
    queryKey: ["sessions"],
    queryFn: async () => {
      const { data } = await apiClient.get<EvalSession[]>("/sessions");
      return data;
    },
  });
}
```

- [ ] **Step 2: Create analysis query hooks**

Create `frontend/src/api/queries/analysis.ts`:

```typescript
import { useQuery } from "@tanstack/react-query";
import apiClient from "@/api/client";
import type {
  AnalysisSummary,
  DistributionItem,
  GlobalFilters,
} from "@/types/api";
import { useGlobalFilters } from "@/hooks/useGlobalFilters";

function filterParams(filters: GlobalFilters): Record<string, string> {
  const params: Record<string, string> = {};
  if (filters.benchmark) params.benchmark = filters.benchmark;
  if (filters.model_version) params.model_version = filters.model_version;
  if (filters.time_range_start)
    params.time_range_start = filters.time_range_start;
  if (filters.time_range_end) params.time_range_end = filters.time_range_end;
  return params;
}

export function useAnalysisSummary() {
  const filters = useGlobalFilters();
  return useQuery({
    queryKey: [
      "analysisSummary",
      filters.benchmark,
      filters.model_version,
      filters.time_range_start,
      filters.time_range_end,
    ],
    queryFn: async () => {
      const { data } = await apiClient.get<AnalysisSummary>(
        "/analysis/summary",
        { params: filterParams(filters) }
      );
      return data;
    },
  });
}

export function useErrorDistribution(
  groupBy: "error_type" | "category" | "severity"
) {
  const filters = useGlobalFilters();
  return useQuery({
    queryKey: [
      "errorDistribution",
      groupBy,
      filters.benchmark,
      filters.model_version,
    ],
    queryFn: async () => {
      const { data } = await apiClient.get<DistributionItem[]>(
        "/analysis/error-distribution",
        { params: { group_by: groupBy, ...filterParams(filters) } }
      );
      return data;
    },
  });
}
```

- [ ] **Step 3: Create trends query hook**

Create `frontend/src/api/queries/trends.ts`:

```typescript
import { useQuery } from "@tanstack/react-query";
import apiClient from "@/api/client";
import type { ErrorTrends, GlobalFilters } from "@/types/api";
import { useGlobalFilters } from "@/hooks/useGlobalFilters";

export function useTrends() {
  const filters = useGlobalFilters();
  const params: Record<string, string> = {};
  if (filters.benchmark) params.benchmark = filters.benchmark;
  if (filters.model_version) params.model_version = filters.model_version;

  return useQuery({
    queryKey: ["trends", filters.benchmark, filters.model_version],
    queryFn: async () => {
      const { data } = await apiClient.get<ErrorTrends>("/trends", { params });
      return data;
    },
  });
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/queries/
git commit -m "feat(frontend): add TanStack Query hooks for sessions, analysis, trends"
```

---

## Task 8: Reusable Components — StatCard, EChartsWrapper, PlaceholderPage

**Files:**
- Create: `frontend/src/components/StatCard.tsx`
- Create: `frontend/src/components/StatCard.test.tsx`
- Create: `frontend/src/components/EChartsWrapper.tsx`
- Create: `frontend/src/components/EChartsWrapper.test.tsx`
- Create: `frontend/src/components/PlaceholderPage.tsx`

- [ ] **Step 1: Write StatCard test**

Create `frontend/src/components/StatCard.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import StatCard from "./StatCard";
import { AimOutlined } from "@ant-design/icons";

describe("StatCard", () => {
  it("renders title and value", () => {
    render(
      <StatCard
        title="总评测数"
        value={42}
        icon={<AimOutlined />}
      />
    );
    expect(screen.getByText("总评测数")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders prefix and suffix", () => {
    render(
      <StatCard
        title="准确率"
        value={70.5}
        icon={<AimOutlined />}
        suffix="%"
      />
    );
    expect(screen.getByText("%")).toBeInTheDocument();
  });

  it("shows skeleton when loading", () => {
    const { container } = render(
      <StatCard
        title="总评测数"
        value={0}
        icon={<AimOutlined />}
        loading
      />
    );
    expect(container.querySelector(".ant-skeleton")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/components/StatCard.test.tsx --no-cache`
Expected: FAIL — module not found

- [ ] **Step 3: Implement StatCard**

Create `frontend/src/components/StatCard.tsx`:

```typescript
import type { ReactNode } from "react";
import { Card, Statistic, Skeleton } from "antd";

interface StatCardProps {
  title: string;
  value: number | string;
  icon: ReactNode;
  prefix?: string;
  suffix?: string;
  loading?: boolean;
}

export default function StatCard({
  title,
  value,
  icon,
  prefix,
  suffix,
  loading,
}: StatCardProps) {
  if (loading) {
    return (
      <Card>
        <Skeleton active paragraph={{ rows: 1 }} />
      </Card>
    );
  }

  return (
    <Card>
      <Statistic
        title={title}
        value={value}
        prefix={
          <>
            {icon}
            {prefix && <span style={{ marginLeft: 4 }}>{prefix}</span>}
          </>
        }
        suffix={suffix}
      />
    </Card>
  );
}
```

- [ ] **Step 4: Run StatCard test to verify it passes**

Run: `cd frontend && npx jest src/components/StatCard.test.tsx --no-cache`
Expected: PASS

- [ ] **Step 5: Write EChartsWrapper test**

Create `frontend/src/components/EChartsWrapper.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import EChartsWrapper from "./EChartsWrapper";

// Mock echarts-for-react
jest.mock("echarts-for-react", () => {
  return function MockECharts(props: { option: unknown }) {
    return <div data-testid="echarts-mock">{JSON.stringify(props.option)}</div>;
  };
});

describe("EChartsWrapper", () => {
  it("renders chart with provided options", () => {
    const option = { title: { text: "Test" } };
    render(<EChartsWrapper option={option} height={300} />);
    expect(screen.getByTestId("echarts-mock")).toBeInTheDocument();
  });

  it("shows skeleton when loading", () => {
    const { container } = render(
      <EChartsWrapper option={{}} height={300} loading />
    );
    expect(container.querySelector(".ant-skeleton")).toBeInTheDocument();
  });
});
```

- [ ] **Step 6: Implement EChartsWrapper**

Create `frontend/src/components/EChartsWrapper.tsx`:

```typescript
import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import { Skeleton } from "antd";

interface EChartsWrapperProps {
  option: EChartsOption;
  height?: number;
  loading?: boolean;
}

export default function EChartsWrapper({
  option,
  height = 400,
  loading,
}: EChartsWrapperProps) {
  if (loading) {
    return <Skeleton active paragraph={{ rows: 6 }} />;
  }

  return (
    <ReactECharts
      option={option}
      style={{ height }}
      opts={{ renderer: "canvas" }}
      notMerge
    />
  );
}
```

- [ ] **Step 7: Run EChartsWrapper test**

Run: `cd frontend && npx jest src/components/EChartsWrapper.test.tsx --no-cache`
Expected: PASS

- [ ] **Step 8: Create PlaceholderPage**

Create `frontend/src/components/PlaceholderPage.tsx`:

```typescript
import { Result } from "antd";
import { useTranslation } from "react-i18next";

export default function PlaceholderPage() {
  const { t } = useTranslation();
  return (
    <Result
      status="info"
      title={t("placeholder.comingSoon")}
    />
  );
}
```

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/
git commit -m "feat(frontend): add StatCard, EChartsWrapper, PlaceholderPage components"
```

---

## Task 9: FilterBar Component

**Files:**
- Create: `frontend/src/components/FilterBar.tsx`
- Create: `frontend/src/components/FilterBar.test.tsx`

- [ ] **Step 1: Write FilterBar test**

Create `frontend/src/components/FilterBar.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { FilterProvider } from "@/contexts/FilterContext";
import FilterBar from "./FilterBar";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "filter.benchmark": "Benchmark",
        "filter.modelVersion": "模型版本",
        "filter.timeRange": "时间范围",
      };
      return map[key] ?? key;
    },
  }),
}));

jest.mock("@/api/queries/sessions", () => ({
  useSessions: () => ({ data: [], isLoading: false }),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const renderFilterBar = () =>
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <FilterProvider>
          <FilterBar />
        </FilterProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );

describe("FilterBar", () => {
  it("renders three filter controls", () => {
    renderFilterBar();
    expect(screen.getByText("Benchmark")).toBeInTheDocument();
    expect(screen.getByText("模型版本")).toBeInTheDocument();
    expect(screen.getByText("时间范围")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/components/FilterBar.test.tsx --no-cache`
Expected: FAIL — module not found

- [ ] **Step 3: Implement FilterBar**

Create `frontend/src/components/FilterBar.tsx`:

```typescript
import { useMemo } from "react";
import { Space, Select, DatePicker, Typography } from "antd";
import { useTranslation } from "react-i18next";
import { useGlobalFilters } from "@/hooks/useGlobalFilters";
import { useSessions } from "@/api/queries/sessions";

const { RangePicker } = DatePicker;
const { Text } = Typography;

export default function FilterBar() {
  const { t } = useTranslation();
  const { benchmark, model_version, setFilter } = useGlobalFilters();
  const { data: sessions } = useSessions();

  const benchmarkOptions = useMemo(() => {
    if (!sessions) return [];
    const unique = [...new Set(sessions.map((s) => s.benchmark))];
    return unique.map((b) => ({ label: b, value: b }));
  }, [sessions]);

  const versionOptions = useMemo(() => {
    if (!sessions) return [];
    const unique = [...new Set(sessions.map((s) => s.model_version))];
    return unique.map((v) => ({ label: v, value: v }));
  }, [sessions]);

  return (
    <Space wrap size="middle">
      <Space>
        <Text>{t("filter.benchmark")}</Text>
        <Select
          allowClear
          placeholder={t("filter.benchmark")}
          value={benchmark}
          onChange={(v) => setFilter("benchmark", v ?? null)}
          options={benchmarkOptions}
          style={{ minWidth: 160 }}
        />
      </Space>
      <Space>
        <Text>{t("filter.modelVersion")}</Text>
        <Select
          allowClear
          placeholder={t("filter.modelVersion")}
          value={model_version}
          onChange={(v) => setFilter("model_version", v ?? null)}
          options={versionOptions}
          style={{ minWidth: 160 }}
        />
      </Space>
      <Space>
        <Text>{t("filter.timeRange")}</Text>
        <RangePicker
          onChange={(dates) => {
            setFilter(
              "time_range_start",
              dates?.[0]?.toISOString() ?? null
            );
            setFilter(
              "time_range_end",
              dates?.[1]?.toISOString() ?? null
            );
          }}
        />
      </Space>
    </Space>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx jest src/components/FilterBar.test.tsx --no-cache`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/FilterBar.tsx frontend/src/components/FilterBar.test.tsx
git commit -m "feat(frontend): add FilterBar component with benchmark/version/time filters"
```

---

## Task 10: AppLayout with Sidebar Navigation

**Files:**
- Create: `frontend/src/layouts/AppLayout.tsx`
- Create: `frontend/src/layouts/AppLayout.test.tsx`

- [ ] **Step 1: Write AppLayout test**

Create `frontend/src/layouts/AppLayout.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { FilterProvider } from "@/contexts/FilterContext";
import { AuthProvider } from "@/contexts/AuthContext";
import AppLayout from "./AppLayout";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "app.title": "评测日志错因分析",
        "nav.overview": "总览",
        "nav.analysis": "错因分析",
        "nav.compare": "版本对比",
        "nav.crossBenchmark": "横向分析",
        "nav.config": "分析配置",
        "nav.logout": "退出",
      };
      return map[key] ?? key;
    },
  }),
}));

jest.mock("@/api/queries/sessions", () => ({
  useSessions: () => ({ data: [], isLoading: false }),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

describe("AppLayout", () => {
  it("renders sidebar with navigation items", () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AuthProvider>
            <FilterProvider>
              <AppLayout />
            </FilterProvider>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(screen.getByText("总览")).toBeInTheDocument();
    expect(screen.getByText("错因分析")).toBeInTheDocument();
    expect(screen.getByText("版本对比")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/layouts/AppLayout.test.tsx --no-cache`
Expected: FAIL — module not found

- [ ] **Step 3: Implement AppLayout**

Create `frontend/src/layouts/AppLayout.tsx`:

```typescript
import { Layout, Menu, FloatButton } from "antd";
import {
  DashboardOutlined,
  BugOutlined,
  SwapOutlined,
  BarChartOutlined,
  SettingOutlined,
  CommentOutlined,
  LogoutOutlined,
} from "@ant-design/icons";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/contexts/AuthContext";
import FilterBar from "@/components/FilterBar";

const { Sider, Content, Header } = Layout;

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
];

export default function AppLayout() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { logout } = useAuth();

  const items = menuItems.map((m) => ({
    key: m.key,
    icon: m.icon,
    label: t(m.labelKey),
  }));

  items.push({
    key: "logout",
    icon: <LogoutOutlined />,
    label: t("nav.logout"),
  });

  const onClick = ({ key }: { key: string }) => {
    if (key === "logout") {
      logout();
      navigate("/login", { replace: true });
    } else {
      navigate(key);
    }
  };

  return (
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
          onClick={onClick}
        />
      </Sider>
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
      <FloatButton icon={<CommentOutlined />} tooltip="Agent Chat" />
    </Layout>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx jest src/layouts/AppLayout.test.tsx --no-cache`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/layouts/
git commit -m "feat(frontend): add AppLayout with collapsible sidebar and filter bar"
```

---

## Task 11: Router & App Root Wiring

**Files:**
- Create: `frontend/src/router.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create router with ProtectedRoute**

Create `frontend/src/router.tsx`:

```typescript
import { lazy, Suspense } from "react";
import {
  createBrowserRouter,
  Navigate,
  Outlet,
  type RouteObject,
} from "react-router-dom";
import { Spin } from "antd";
import { useAuth } from "@/contexts/AuthContext";
import AppLayout from "@/layouts/AppLayout";
import PlaceholderPage from "@/components/PlaceholderPage";
import Login from "@/pages/Login";

const Overview = lazy(() => import("@/pages/Overview"));

function LazyFallback() {
  return (
    <div style={{ padding: 48, textAlign: "center" }}>
      <Spin size="large" />
    </div>
  );
}

function ProtectedRoute() {
  const { token, loading } = useAuth();
  if (loading) return <LazyFallback />;
  if (!token) return <Navigate to="/login" replace />;
  return <Outlet />;
}

const protectedChildren: RouteObject[] = [
  { index: true, element: <Navigate to="/overview" replace /> },
  {
    path: "overview",
    element: (
      <Suspense fallback={<LazyFallback />}>
        <Overview />
      </Suspense>
    ),
  },
  { path: "analysis", element: <PlaceholderPage /> },
  { path: "compare", element: <PlaceholderPage /> },
  { path: "cross-benchmark", element: <PlaceholderPage /> },
  { path: "config", element: <PlaceholderPage /> },
];

export const router = createBrowserRouter([
  { path: "/login", element: <Login /> },
  {
    path: "/",
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: protectedChildren,
      },
    ],
  },
  { path: "*", element: <Navigate to="/overview" replace /> },
]);
```

- [ ] **Step 2: Wire up App.tsx with all providers**

Replace `frontend/src/App.tsx`:

```typescript
import { RouterProvider } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import { AuthProvider } from "@/contexts/AuthContext";
import { router } from "@/router";
import "./i18n";

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
          <RouterProvider router={router} />
        </AuthProvider>
      </QueryClientProvider>
    </ConfigProvider>
  );
}
```

Note: `FilterProvider` is not wrapped in `App.tsx` because it uses `useSearchParams` which requires a router context. Instead, `AppLayout` wraps its content with `FilterProvider`. Replace the full `frontend/src/layouts/AppLayout.tsx` with this updated version that adds the `FilterProvider` wrapper:

```typescript
import { Layout, Menu, FloatButton } from "antd";
import {
  DashboardOutlined,
  BugOutlined,
  SwapOutlined,
  BarChartOutlined,
  SettingOutlined,
  CommentOutlined,
  LogoutOutlined,
} from "@ant-design/icons";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/contexts/AuthContext";
import { FilterProvider } from "@/contexts/FilterContext";
import FilterBar from "@/components/FilterBar";

const { Sider, Content, Header } = Layout;

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
];

export default function AppLayout() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { logout } = useAuth();

  const items = menuItems.map((m) => ({
    key: m.key,
    icon: m.icon,
    label: t(m.labelKey),
  }));

  items.push({
    key: "logout",
    icon: <LogoutOutlined />,
    label: t("nav.logout"),
  });

  const onClick = ({ key }: { key: string }) => {
    if (key === "logout") {
      logout();
      navigate("/login", { replace: true });
    } else {
      navigate(key);
    }
  };

  return (
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
          onClick={onClick}
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
      </FilterProvider>
      <FloatButton icon={<CommentOutlined />} tooltip="Agent Chat" />
    </Layout>
  );
}
```

- [ ] **Step 3: Verify build compiles**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
git add frontend/src/router.tsx frontend/src/App.tsx frontend/src/layouts/AppLayout.tsx
git commit -m "feat(frontend): wire router, providers, and protected routes"
```

---

## Task 12: Overview Page — TrendChart & ErrorTypeDonut

**Files:**
- Create: `frontend/src/pages/Overview/components/TrendChart.tsx`
- Create: `frontend/src/pages/Overview/components/ErrorTypeDonut.tsx`

- [ ] **Step 1: Create TrendChart component**

Create `frontend/src/pages/Overview/components/TrendChart.tsx`:

```typescript
import { Card } from "antd";
import { useTranslation } from "react-i18next";
import EChartsWrapper from "@/components/EChartsWrapper";
import type { TrendPoint } from "@/types/api";
import type { EChartsOption } from "echarts";

interface TrendChartProps {
  data: TrendPoint[];
  loading?: boolean;
}

export default function TrendChart({ data, loading }: TrendChartProps) {
  const { t } = useTranslation();

  const option: EChartsOption = {
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "category",
      data: data.map((d) => d.period),
    },
    yAxis: {
      type: "value",
      name: "%",
      axisLabel: { formatter: "{value}%" },
    },
    series: [
      {
        type: "line",
        data: data.map((d) => +(d.error_rate * 100).toFixed(2)),
        smooth: true,
        areaStyle: { opacity: 0.1 },
      },
    ],
  };

  return (
    <Card title={t("overview.trendChart")}>
      <EChartsWrapper option={option} height={350} loading={loading} />
    </Card>
  );
}
```

- [ ] **Step 2: Create ErrorTypeDonut component**

Create `frontend/src/pages/Overview/components/ErrorTypeDonut.tsx`:

```typescript
import { Card } from "antd";
import { useTranslation } from "react-i18next";
import EChartsWrapper from "@/components/EChartsWrapper";
import type { DistributionItem } from "@/types/api";
import type { EChartsOption } from "echarts";

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
        data: data.map((d) => ({ name: d.label, value: d.count })),
      },
    ],
  };

  return (
    <Card title={t("overview.errorDistribution")}>
      <EChartsWrapper option={option} height={350} loading={loading} />
    </Card>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Overview/components/
git commit -m "feat(frontend): add TrendChart and ErrorTypeDonut chart components"
```

---

## Task 13: Overview Page — Assembly & Test

**Files:**
- Create: `frontend/src/pages/Overview/index.tsx`
- Create: `frontend/src/pages/Overview/Overview.test.tsx`

- [ ] **Step 1: Write Overview page test**

Create `frontend/src/pages/Overview/Overview.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { FilterProvider } from "@/contexts/FilterContext";
import Overview from "./index";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "overview.totalSessions": "总评测数",
        "overview.totalErrors": "错题总数",
        "overview.accuracy": "整体准确率",
        "overview.llmAnalysed": "LLM 已分析数",
        "overview.llmCost": "LLM 分析成本",
        "overview.trendChart": "错误率趋势",
        "overview.errorDistribution": "L1 错误类型分布",
        "overview.noData": "还没有评测数据，请先上传评测日志",
        "common.error": "加载失败",
        "common.retry": "重试",
      };
      return map[key] ?? key;
    },
  }),
}));

jest.mock("@/api/queries/analysis", () => ({
  useAnalysisSummary: () => ({
    data: {
      total_sessions: 5,
      total_records: 1000,
      total_errors: 300,
      accuracy: 0.7,
      llm_analysed_count: 150,
      llm_total_cost: 1.23,
    },
    isLoading: false,
    isError: false,
  }),
  useErrorDistribution: () => ({
    data: [
      { label: "格式与规范错误", count: 50, percentage: 16.7 },
      { label: "推理性错误", count: 100, percentage: 33.3 },
    ],
    isLoading: false,
    isError: false,
  }),
}));

jest.mock("@/api/queries/trends", () => ({
  useTrends: () => ({
    data: {
      data_points: [
        { period: "v1.0", error_rate: 0.35, total: 500, errors: 175 },
        { period: "v2.0", error_rate: 0.3, total: 500, errors: 150 },
      ],
    },
    isLoading: false,
    isError: false,
  }),
}));

// Mock echarts-for-react
jest.mock("echarts-for-react", () => {
  return function MockECharts() {
    return <div data-testid="echarts-mock" />;
  };
});

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const renderOverview = () =>
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <FilterProvider>
          <Overview />
        </FilterProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );

describe("Overview page", () => {
  it("renders 5 KPI stat cards", () => {
    renderOverview();
    expect(screen.getByText("总评测数")).toBeInTheDocument();
    expect(screen.getByText("错题总数")).toBeInTheDocument();
    expect(screen.getByText("整体准确率")).toBeInTheDocument();
    expect(screen.getByText("LLM 已分析数")).toBeInTheDocument();
    expect(screen.getByText("LLM 分析成本")).toBeInTheDocument();
  });

  it("renders stat values", () => {
    renderOverview();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("300")).toBeInTheDocument();
  });

  it("renders chart titles", () => {
    renderOverview();
    expect(screen.getByText("错误率趋势")).toBeInTheDocument();
    expect(screen.getByText("L1 错误类型分布")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/pages/Overview/Overview.test.tsx --no-cache`
Expected: FAIL — module not found

- [ ] **Step 3: Implement Overview page**

Create `frontend/src/pages/Overview/index.tsx`:

```typescript
import { Row, Col, Alert, Button, Empty } from "antd";
import {
  FileTextOutlined,
  AlertOutlined,
  AimOutlined,
  RobotOutlined,
  DollarOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import StatCard from "@/components/StatCard";
import TrendChart from "./components/TrendChart";
import ErrorTypeDonut from "./components/ErrorTypeDonut";
import { useAnalysisSummary, useErrorDistribution } from "@/api/queries/analysis";
import { useTrends } from "@/api/queries/trends";

export default function Overview() {
  const { t } = useTranslation();
  const summary = useAnalysisSummary();
  const distribution = useErrorDistribution("error_type");
  const trends = useTrends();

  const isError = summary.isError || distribution.isError || trends.isError;
  const isLoading = summary.isLoading;

  if (isError) {
    return (
      <Alert
        type="error"
        message={t("common.error")}
        action={
          <Button
            size="small"
            onClick={() => {
              summary.refetch();
              distribution.refetch();
              trends.refetch();
            }}
          >
            {t("common.retry")}
          </Button>
        }
        showIcon
      />
    );
  }

  const noData = summary.data && summary.data.total_sessions === 0;
  if (noData) {
    return <Empty description={t("overview.noData")} />;
  }

  const s = summary.data;

  return (
    <>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={8} lg={4} xl={4}>
          <StatCard
            title={t("overview.totalSessions")}
            value={s?.total_sessions ?? 0}
            icon={<FileTextOutlined />}
            loading={isLoading}
          />
        </Col>
        <Col xs={24} sm={12} md={8} lg={5} xl={5}>
          <StatCard
            title={t("overview.totalErrors")}
            value={s?.total_errors ?? 0}
            icon={<AlertOutlined />}
            loading={isLoading}
          />
        </Col>
        <Col xs={24} sm={12} md={8} lg={5} xl={5}>
          <StatCard
            title={t("overview.accuracy")}
            value={s ? +(s.accuracy * 100).toFixed(1) : 0}
            icon={<AimOutlined />}
            suffix="%"
            loading={isLoading}
          />
        </Col>
        <Col xs={24} sm={12} md={8} lg={5} xl={5}>
          <StatCard
            title={t("overview.llmAnalysed")}
            value={s?.llm_analysed_count ?? 0}
            icon={<RobotOutlined />}
            loading={isLoading}
          />
        </Col>
        <Col xs={24} sm={12} md={8} lg={5} xl={5}>
          <StatCard
            title={t("overview.llmCost")}
            value={s ? `$${s.llm_total_cost.toFixed(2)}` : "$0.00"}
            icon={<DollarOutlined />}
            loading={isLoading}
          />
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <TrendChart
            data={trends.data?.data_points ?? []}
            loading={trends.isLoading}
          />
        </Col>
        <Col xs={24} lg={12}>
          <ErrorTypeDonut
            data={distribution.data ?? []}
            loading={distribution.isLoading}
          />
        </Col>
      </Row>
    </>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx jest src/pages/Overview/Overview.test.tsx --no-cache`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Overview/
git commit -m "feat(frontend): implement Overview dashboard with KPI cards and charts"
```

---

## Task 14: Full Integration — Build & Smoke Test

**Files:**
- Modify: `frontend/src/main.tsx` (import i18n)

- [ ] **Step 1: Ensure i18n is imported in main.tsx**

`frontend/src/main.tsx` should already import `App` which imports `./i18n`. Verify the import chain is correct.

- [ ] **Step 2: Run full test suite**

Run: `cd frontend && npm test -- --passWithNoTests`
Expected: All tests pass

- [ ] **Step 3: Run production build**

Run: `cd frontend && npm run build`
Expected: Build succeeds, output in `frontend/dist/`

- [ ] **Step 4: Verify dev server starts**

Run: `cd frontend && npm run dev` (manually verify in browser, then Ctrl+C)
Expected: Vite dev server starts on http://localhost:3000, shows login page

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): complete Plan 07 — frontend foundation & overview dashboard"
```
