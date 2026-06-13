import { fetchWithRetry } from './fetchWithRetry'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'

export interface HealthResponse {
  status: string
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetchWithRetry(`${API_BASE_URL}/health`)

  if (!response.ok) {
    throw new Error(`Health check falhou com status ${response.status}`)
  }

  return (await response.json()) as HealthResponse
}
