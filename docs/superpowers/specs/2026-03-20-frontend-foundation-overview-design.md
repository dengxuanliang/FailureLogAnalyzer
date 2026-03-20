# Frontend Foundation & Overview Dashboard — Design Spec

> Date: 2026-03-20
> Status: Draft
> Scope: Plan 07 — Project scaffolding, global layout, API client, auth, i18n, and Overview page

## 1. Goal

Set up the React frontend project with all foundational infrastructure (build tooling, routing, state management, API client, authentication, i18n) and implement the first page — the Overview dashboard with KPI cards and charts.

This plan delivers a working, deployable frontend that connects to the backend APIs from Plans 01 and 05, and provides the shell layout for all subsequent pages (Plans 08–10).

## 2. Tech Stack

| Concern | Choice |
|---------|--------|
| Build tool | Vite 5 |
| UI framework | React 18 + TypeScript 5 |
| Component library | Ant Design 5 |
| Charting | ECharts 5 via `echarts-for-react` |
| Server state | TanStack Query v5 |
| Client state | React Context |
| Routing | React Router v6 |
| HTTP client | Axios |
| i18n | react-i18next (zh + en) |
| Code quality | ESLint + Prettier |
| Testing | Jest + React Testing Library |

## 3. Project Structure

```
frontend/
  public/
  src/
    api/
      client.ts              # Axios instance: base URL, JWT interceptor, error handling
      queries/
        analysis.ts          # useAnalysisSummary, useErrorDistribution hooks
        sessions.ts          # useSessions hook
        trends.ts            # useTrends hook
    components/
      StatCard.tsx           # Reusable KPI metric card
      FilterBar.tsx          # Global filter bar (benchmark, model version, time range)
      EChartsWrapper.tsx     # Reusable ECharts container with auto-resize
      PlaceholderPage.tsx    # "Coming Soon" placeholder for unimplemented routes
    contexts/
      FilterContext.tsx      # Global filter state (benchmark, model_version, time_range)
      AuthContext.tsx        # JWT token, current user, login/logout
    hooks/
      useGlobalFilters.ts   # Convenience hook for FilterContext
    layouts/
      AppLayout.tsx          # Sidebar nav + top filter bar + content area
    locales/
      zh.json                # Chinese translations
      en.json                # English translations
    pages/
      Login/
        index.tsx            # Login page
      Overview/
        index.tsx            # Overview dashboard page
        components/
          TrendChart.tsx     # Error rate trend line chart (ECharts)
          ErrorTypeDonut.tsx # L1 error distribution donut chart (ECharts)
    types/
      api.ts                 # TypeScript interfaces matching backend API schemas
    App.tsx                  # Root component: providers + router
    main.tsx                 # Entry point
    router.tsx               # Route definitions
    i18n.ts                  # i18next initialization
  .env                       # VITE_API_BASE_URL
  .env.example
  index.html
  package.json
  tsconfig.json
  vite.config.ts
```

## 4. Global Layout (AppLayout)

### 4.1 Left Sidebar

- Ant Design `Layout.Sider` with `collapsible` prop
- Navigation menu items:
  - Overview (`/overview`)
  - Error Analysis (`/analysis`) — placeholder
  - Version Compare (`/compare`) — placeholder
  - Cross-Benchmark (`/cross-benchmark`) — placeholder
  - Config (`/config`) — placeholder
- Bottom of sidebar: evaluation session selector (Ant Design `Select`) to pick active session context
- Selected menu item highlighted based on current route via `useLocation`

### 4.2 Top Filter Bar

- `FilterBar` component rendered inside the content header area
- Three filter controls:
  - **Benchmark**: `Select` dropdown, options fetched from `/api/v1/sessions` (distinct benchmarks)
  - **Model Version**: `Select` dropdown, options fetched similarly
  - **Time Range**: `DatePicker.RangePicker`
- Filter values stored in `FilterContext` and synced to URL query params via `useSearchParams`
- All API queries include filter values in their `queryKey`, so changing filters auto-refetches data

### 4.3 Content Area

- `Layout.Content` renders the active route page via `<Outlet />`
- Ant Design `Breadcrumb` for navigation context (optional)

### 4.4 Agent Chat Placeholder

- Bottom-right floating button (Ant Design `FloatButton`) placeholder
- Actual chat implementation deferred to a later plan

## 5. API Client & Authentication

### 5.1 Axios Client

- Base URL: `VITE_API_BASE_URL` env var (default `http://localhost:8000/api/v1`)
- Request interceptor: reads JWT from `localStorage`, attaches `Authorization: Bearer <token>` header
- Response interceptor: on HTTP 401, clears token from localStorage and redirects to `/login`
- Error wrapping: API errors normalized into `ApiError { status: number, message: string, detail?: any }`

### 5.2 AuthContext

- State: `token: string | null`, `user: { id, username, role } | null`, `loading: boolean`
- `login(username, password)`: calls `POST /api/v1/auth/login`, stores token in localStorage, decodes user info from JWT payload
- `logout()`: clears token from localStorage, resets state, redirects to `/login`
- On mount: checks localStorage for existing token, validates it (optional: `GET /api/v1/auth/me`)

### 5.3 Protected Routes

- `ProtectedRoute` wrapper component: if no token, redirect to `/login`
- All routes except `/login` are protected

### 5.4 TanStack Query Configuration

- `QueryClient` defaults: `staleTime: 30_000` (30s), `retry: 1`, `refetchOnWindowFocus: false`
- All query hooks accept global filter params and include them in `queryKey`
- Query hooks return `{ data, isLoading, isError, error }` for consistent loading/error UI

## 6. Internationalization (i18n)

- `react-i18next` with `i18next` backend
- Two locale files: `zh.json` (primary), `en.json`
- Default language: `zh`
- Language switcher in the sidebar footer or top header area
- Translation keys organized by page/component:
  ```json
  {
    "nav.overview": "总览",
    "nav.analysis": "错因分析",
    "overview.totalSessions": "总评测数",
    "overview.totalErrors": "错题总数",
    ...
  }
  ```

## 7. Overview Page

### 7.1 Stat Cards (5 KPI metrics)

Displayed in a responsive grid row at the top of the page.

| Card title | API field | Format | Ant Design icon |
|-----------|-----------|--------|-----------------|
| 总评测数 | `total_sessions` | integer | `FileTextOutlined` |
| 错题总数 | `total_errors` | integer | `AlertOutlined` |
| 整体准确率 | `accuracy` | percentage (e.g. 70.5%) | `AimOutlined` |
| LLM 已分析数 | `llm_analysed_count` | integer | `RobotOutlined` |
| LLM 分析成本 | `llm_total_cost` | currency (e.g. $1.23) | `DollarOutlined` |

API: `GET /api/v1/analysis/summary?benchmark=&model_version=&time_range=`

`StatCard` is a reusable component:
```typescript
interface StatCardProps {
  title: string;
  value: number | string;
  icon: React.ReactNode;
  prefix?: string;    // e.g. "$"
  suffix?: string;    // e.g. "%"
  loading?: boolean;
}
```

### 7.2 Error Rate Trend Chart (Line Chart)

- X-axis: model version (categorical)
- Y-axis: error rate (%)
- Multiple lines if multiple benchmarks present
- ECharts line chart via `EChartsWrapper`
- Tooltip on hover showing exact values
- API: `GET /api/v1/trends`

### 7.3 L1 Error Type Distribution (Donut Chart)

- ECharts pie chart with inner radius (donut)
- Shows 6 L1 categories: Format, Extraction, Knowledge, Reasoning, Comprehension, Generation
- Legend at the bottom
- Tooltip with count and percentage
- API: `GET /api/v1/analysis/error-distribution?group_by=error_type`

### 7.4 Responsive Layout

- **Desktop (≥1200px)**: 5-column stat card grid; charts side-by-side (50/50)
- **Tablet (768–1199px)**: 2+3 stat card grid; charts stacked
- **Mobile (<768px)**: stacked stat cards; stacked charts

Using Ant Design `Row` / `Col` with responsive breakpoints (`xs`, `sm`, `md`, `lg`, `xl`).

### 7.5 Loading & Empty States

- **Loading**: Ant Design `Skeleton` components matching the card/chart shapes
- **Empty**: illustration + message when no evaluation data exists ("还没有评测数据，请先上传评测日志")
- **Error**: Ant Design `Alert` with retry button

## 8. Routing Table

| Path | Component | Auth | Status |
|------|-----------|------|--------|
| `/login` | `Login` | No | Plan 07 |
| `/` | Redirect → `/overview` | Yes | Plan 07 |
| `/overview` | `Overview` | Yes | Plan 07 |
| `/analysis` | `PlaceholderPage` | Yes | Plan 08 |
| `/compare` | `PlaceholderPage` | Yes | Plan 08 |
| `/cross-benchmark` | `PlaceholderPage` | Yes | Plan 09 |
| `/config` | `PlaceholderPage` | Yes | Plan 09 |

## 9. Backend API Dependencies

This plan consumes these existing backend endpoints (from Plans 01 and 05):

| Endpoint | Plan | Used by |
|----------|------|---------|
| `POST /api/v1/auth/login` | 01 | AuthContext |
| `GET /api/v1/sessions` | 05 | FilterBar (benchmark/version options) |
| `GET /api/v1/analysis/summary` | 05 | Overview stat cards |
| `GET /api/v1/analysis/error-distribution` | 05 | Overview donut chart |
| `GET /api/v1/trends` | 05 | Overview trend chart |

## 10. Testing Strategy

- **Unit tests**: Jest + React Testing Library for components (`StatCard`, `FilterBar`, `EChartsWrapper`)
- **Hook tests**: `renderHook` for TanStack Query hooks with `QueryClientProvider` wrapper
- **Integration tests**: Page-level tests for Overview page with mocked API responses (MSW or manual mocking)
- **Snapshot tests**: For layout components to catch unintended visual regressions

## 11. Non-Functional Requirements

- First meaningful paint < 3s (as per design spec)
- Bundle size: lazy-load ECharts and page components via `React.lazy` + `Suspense`
- Ant Design CSS tree-shaking via Vite plugin
- Dev proxy: Vite `server.proxy` to forward `/api` to backend during development
