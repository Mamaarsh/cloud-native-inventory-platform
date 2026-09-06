import axios, { type InternalAxiosRequestConfig } from "axios";
import { tokenStorage } from "@/auth/token-storage";
import type { TokenRefreshResponse } from "@/types";

const apiBaseUrl = import.meta.env.VITE_API_URL?.replace(/\/+$/, "");

if (!apiBaseUrl) {
  throw new Error("VITE_API_URL is required. Copy .env.example to .env and configure it.");
}

export const AUTH_LOGOUT_EVENT = "inventory:auth-logout";

export const apiClient = axios.create({
  baseURL: apiBaseUrl,
  timeout: 15_000,
});

const refreshClient = axios.create({
  baseURL: apiBaseUrl,
  timeout: 15_000,
  headers: { "Content-Type": "application/json" },
});

interface RetryableRequest extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

let refreshPromise: Promise<string> | null = null;

function forceLogout(): void {
  tokenStorage.clear();
  window.dispatchEvent(new Event(AUTH_LOGOUT_EVENT));
  if (window.location.pathname !== "/login") {
    window.location.assign("/login");
  }
}

async function refreshAccessToken(): Promise<string> {
  const refresh = tokenStorage.getRefresh();
  if (!refresh) throw new Error("No refresh token is available.");

  const { data } = await refreshClient.post<TokenRefreshResponse>(
    "/auth/token/refresh/",
    { refresh },
  );
  tokenStorage.setAccess(data.access);
  return data.access;
}

apiClient.interceptors.request.use((config) => {
  const accessToken = tokenStorage.getAccess();
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (!axios.isAxiosError(error) || error.response?.status !== 401 || !error.config) {
      return Promise.reject(error instanceof Error ? error : new Error("API request failed."));
    }

    const originalRequest = error.config as RetryableRequest;
    const isTokenRequest = originalRequest.url?.includes("/auth/token/") ?? false;
    if (originalRequest._retry || isTokenRequest) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;
    try {
      refreshPromise ??= refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
      const accessToken = await refreshPromise;
      originalRequest.headers.Authorization = `Bearer ${accessToken}`;
      return apiClient(originalRequest);
    } catch (refreshError: unknown) {
      forceLogout();
      return Promise.reject(
        refreshError instanceof Error ? refreshError : new Error("Token refresh failed."),
      );
    }
  },
);
