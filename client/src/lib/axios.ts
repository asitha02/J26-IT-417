import axios, { AxiosError } from 'axios';
import { env } from '@/config/env';
import type { ApiError } from '@/types/api';

export const http = axios.create({
  baseURL: env.apiUrl,
  timeout: 10_000,
  headers: { 'Content-Type': 'application/json' },
});

http.interceptors.response.use(
  (res) => res,
  (error: AxiosError<ApiError>) =>
    Promise.reject(new Error(error.response?.data?.message ?? error.message))
);
