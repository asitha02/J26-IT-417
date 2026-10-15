import type { AxiosRequestConfig } from 'axios';
import { http } from '@/lib/axios';
import type { ApiResponse } from '@/types/api';

async function request<T>(config: AxiosRequestConfig): Promise<T> {
  const res = await http.request<ApiResponse<T>>(config);
  return res.data.data;
}

export const api = {
  get: <T>(url: string, config?: AxiosRequestConfig) => request<T>({ ...config, method: 'GET', url }),
  post: <T, B = unknown>(url: string, body?: B, config?: AxiosRequestConfig) =>
    request<T>({ ...config, method: 'POST', url, data: body }),
  put: <T, B = unknown>(url: string, body?: B, config?: AxiosRequestConfig) =>
    request<T>({ ...config, method: 'PUT', url, data: body }),
  delete: <T>(url: string, config?: AxiosRequestConfig) => request<T>({ ...config, method: 'DELETE', url }),
};
