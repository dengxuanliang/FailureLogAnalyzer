import { lazy, Suspense } from "react";
import { createBrowserRouter, Navigate, Outlet, type RouteObject } from "react-router-dom";
import { Spin } from "antd";
import { useAuth } from "@/contexts/AuthContext";
import AppLayout from "@/layouts/AppLayout";
import Login from "@/pages/Login";

const Overview = lazy(() => import("@/pages/Overview"));
const Analysis = lazy(() => import("@/pages/Analysis"));
const Compare = lazy(() => import("@/pages/Compare"));
const CrossBenchmark = lazy(() => import("@/pages/CrossBenchmark"));
const Config = lazy(() => import("@/pages/Config"));
const Sessions = lazy(() => import("@/pages/Sessions"));
const Reports = lazy(() => import("@/pages/Reports"));
const Operations = lazy(() => import("@/pages/Operations"));
const SessionDetail = lazy(() => import("@/pages/Sessions/SessionDetail"));
const ReportDetail = lazy(() => import("@/pages/Reports/ReportDetail"));

function LazyFallback() {
  return (
    <div style={{ padding: 48, textAlign: "center" }}>
      <Spin size="large" />
    </div>
  );
}

function ProtectedRoute() {
  const { token, loading } = useAuth();

  if (loading) {
    return <LazyFallback />;
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

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
  {
    path: "analysis",
    element: (
      <Suspense fallback={<LazyFallback />}>
        <Analysis />
      </Suspense>
    ),
  },
  {
    path: "sessions",
    element: (
      <Suspense fallback={<LazyFallback />}>
        <Sessions />
      </Suspense>
    ),
  },
  {
    path: "sessions/:sessionId",
    element: (
      <Suspense fallback={<LazyFallback />}>
        <SessionDetail />
      </Suspense>
    ),
  },
  {
    path: "compare",
    element: (
      <Suspense fallback={<LazyFallback />}>
        <Compare />
      </Suspense>
    ),
  },
  {
    path: "reports",
    element: (
      <Suspense fallback={<LazyFallback />}>
        <Reports />
      </Suspense>
    ),
  },
  {
    path: "reports/:reportId",
    element: (
      <Suspense fallback={<LazyFallback />}>
        <ReportDetail />
      </Suspense>
    ),
  },
  {
    path: "cross-benchmark",
    element: (
      <Suspense fallback={<LazyFallback />}>
        <CrossBenchmark />
      </Suspense>
    ),
  },
  {
    path: "config",
    element: (
      <Suspense fallback={<LazyFallback />}>
        <Config />
      </Suspense>
    ),
  },
  {
    path: "operations",
    element: (
      <Suspense fallback={<LazyFallback />}>
        <Operations />
      </Suspense>
    ),
  },
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
