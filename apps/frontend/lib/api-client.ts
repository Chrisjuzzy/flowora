"use client";

import axios from "axios";
import { useAuthStore } from "@/store/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error?.response?.data?.message ||
      error?.response?.data?.detail ||
      error?.message ||
      "Request failed";
    if (typeof window !== "undefined") {
      // Surface API failures in console for debugging
      // eslint-disable-next-line no-console
      console.error("Flowora API error:", {
        url: error?.config?.url,
        method: error?.config?.method,
        status: error?.response?.status,
        message,
      });
    }
    return Promise.reject(new Error(message));
  }
);
