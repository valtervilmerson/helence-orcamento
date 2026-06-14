import { fetchWithRetry } from './fetchWithRetry'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'

export interface ApiError {
  error: { code: string; message: string; details?: Record<string, unknown> }
}

export class AuthApiError extends Error {
  code: string
  details?: Record<string, unknown>

  constructor(body: ApiError) {
    super(body.error.message)
    this.code = body.error.code
    this.details = body.error.details
  }
}

export type UserRole = 'admin' | 'importador' | 'revisor' | 'vendedor' | 'colaborador'

export interface AuthUser {
  id: number
  name: string
  email: string
  role: UserRole
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetchWithRetry(`${API_BASE_URL}${path}`, {
    ...init,
    headers: init?.body ? { 'Content-Type': 'application/json', ...init.headers } : init?.headers,
  })

  if (response.status === 204) {
    return undefined as T
  }

  const body = await response.json()

  if (!response.ok) {
    throw new AuthApiError(body as ApiError)
  }

  return body as T
}

export const login = (email: string, password: string) =>
  request<AuthUser>('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) })

export const logout = () => request<void>('/auth/logout', { method: 'POST' })

export const getCurrentUser = () => request<AuthUser>('/auth/me')
