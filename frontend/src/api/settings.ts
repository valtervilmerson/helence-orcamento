import { fetchWithRetry } from './fetchWithRetry'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'

import { QuotesApiError, type ApiError } from './quotes'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetchWithRetry(`${API_BASE_URL}${path}`, {
    ...init,
    headers: init?.body ? { 'Content-Type': 'application/json', ...init.headers } : init?.headers,
  })

  if (response.status === 204) return undefined as T

  const body = await response.json()
  if (!response.ok) throw new QuotesApiError(body as ApiError)
  return body as T
}

export interface AppSettings {
  global_markup_percent: number
  discount_limit_percent: number
  default_validity_days: number
}

export const getSettings = () => request<AppSettings>('/settings')
export const updateSettings = (data: Partial<AppSettings>) =>
  request<AppSettings>('/settings', { method: 'PATCH', body: JSON.stringify(data) })
