/* eslint-env browser */

import axios, {
  AxiosHeaders,
  type AxiosError,
  type InternalAxiosRequestConfig,
} from "axios";
import type { ApiError } from "@/types/api";

const env = (import.meta.env ?? {}) as Partial<ImportMetaEnv>;

const apiClient = axios.create({
  baseURL: env.VITE_API_BASE_URL || "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

const requestInterceptor = (
  config: InternalAxiosRequestConfig<unknown>,
): InternalAxiosRequestConfig<unknown> => {
  const token = localStorage.getItem("token");
  if (token) {
    const headers = new AxiosHeaders(config.headers);
    headers.set("Authorization", `Bearer ${token}`);
    headers.set("Content-Type", "application/json");
    config.headers = headers;
  }
  return config;
};

export const redirectToLogin = () => {
  navigation.assign("/login");
};

export const navigation = {
  assign: (href: string) => {
    if (typeof window === "undefined") {
      return;
    }

    if (window.location?.assign) {
      window.location.assign(href);
    } else if (window.location) {
      window.location.href = href;
    }
  },
};

const responseErrorInterceptor = (error: AxiosError) => {
  const status = error.response?.status ?? 0;
  if (status === 401) {
    localStorage.removeItem("token");
    redirectToLogin();
    return Promise.reject(error);
  }

  const data = error.response?.data as { detail?: unknown; message?: unknown };
  const messageSource = data?.detail ?? data?.message ?? error.message;
  const message =
    typeof messageSource === "string"
      ? messageSource
      : String(messageSource ?? error.message ?? "An unexpected error occurred");

  const apiError: ApiError = {
    status,
    message,
    detail: error.response?.data,
  };

  return Promise.reject<ApiError>(apiError);
};

apiClient.interceptors.request.use(requestInterceptor);
apiClient.interceptors.response.use((response) => response, responseErrorInterceptor);

export default apiClient;
