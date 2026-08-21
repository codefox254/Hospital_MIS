import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

import { useAuthStore } from "./auth-store";
import type { ApiErrorBody, TokenPair } from "../types/auth";

// 10.0.2.2 is the Android emulator's alias for the host machine's
// localhost — the backend runs on the host (docker-compose), not inside
// the emulator's own network namespace.
export const API_BASE_URL = "http://10.0.2.2:8011/api/v1";

export const api = axios.create({ baseURL: API_BASE_URL });

api.interceptors.request.use((config) => {
  const { access } = useAuthStore.getState();
  if (access) {
    config.headers.Authorization = `Bearer ${access}`;
  }
  return config;
});

interface RetriableConfig extends InternalAxiosRequestConfig {
  _retried?: boolean;
}

const refreshClient = axios.create({ baseURL: API_BASE_URL });

let refreshInFlight: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const { refresh, setTokens, logout } = useAuthStore.getState();
  if (!refresh) {
    logout();
    throw new Error("No refresh token available.");
  }
  if (!refreshInFlight) {
    refreshInFlight = refreshClient
      .post<TokenPair>("/auth/token/refresh/", { refresh })
      .then(({ data }) => {
        setTokens({ access: data.access, refresh: data.refresh ?? refresh });
        return data.access;
      })
      .catch((err) => {
        logout();
        throw err;
      })
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiErrorBody>) => {
    const config = error.config as RetriableConfig | undefined;
    if (error.response?.status === 401 && config && !config._retried) {
      config._retried = true;
      try {
        const access = await refreshAccessToken();
        config.headers.Authorization = `Bearer ${access}`;
        return api(config);
      } catch {
        // Falls through — the caller sees the original 401 and the
        // navigator switches back to Login once the store's user clears.
      }
    }
    return Promise.reject(error);
  },
);

export function apiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const body = error.response?.data as ApiErrorBody | undefined;
    if (body?.error?.message) return body.error.message;
  }
  return "Something went wrong. Please try again.";
}
