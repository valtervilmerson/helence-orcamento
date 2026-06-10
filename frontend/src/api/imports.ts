const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export interface ApiError {
  error: { code: string; message: string; details?: Record<string, unknown> }
}

export class ImportsApiError extends Error {
  code: string
  details?: Record<string, unknown>

  constructor(body: ApiError) {
    super(body.error.message)
    this.code = body.error.code
    this.details = body.error.details
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init)

  if (response.status === 204) {
    return undefined as T
  }

  const body = await response.json()

  if (!response.ok) {
    throw new ImportsApiError(body as ApiError)
  }

  return body as T
}

// ---------------------------------------------------------------------------
// Importações — 14.1/14.2 (Fase 4: receber e guardar, sem processar)
// ---------------------------------------------------------------------------

export type ImportStatus = 'recebido' | 'processando' | 'concluido' | 'erro'

export interface UserSummary {
  id: number
  name: string
}

export interface ImportedFile {
  id: number
  original_filename: string | null
  file_hash: string | null
  page_count: number | null
  status: ImportStatus
  imported_at: string
  imported_by: UserSummary | null
  notes: string | null
}

export interface PriceTableSummary {
  id: number
  code: string
  status: string
}

export interface ImportListItem {
  id: number
  original_filename: string | null
  status: ImportStatus
  page_count: number | null
  imported_at: string
  items_extracted: number
  items_pending_review: number
  linked_price_table: PriceTableSummary | null
}

export interface ImportListOut {
  items: ImportListItem[]
  page: number
  page_size: number
  total: number
}

export const uploadImport = (file: File, notes?: string) => {
  const formData = new FormData()
  formData.append('file', file)
  if (notes) {
    formData.append('notes', notes)
  }
  return request<ImportedFile>('/imports', { method: 'POST', body: formData })
}

export const listImports = (params?: { status?: ImportStatus; page?: number; page_size?: number }) => {
  const query = new URLSearchParams()
  if (params?.status) query.set('status', params.status)
  if (params?.page) query.set('page', String(params.page))
  if (params?.page_size) query.set('page_size', String(params.page_size))
  const qs = query.toString()
  return request<ImportListOut>(`/imports${qs ? `?${qs}` : ''}`)
}

// ---------------------------------------------------------------------------
// Processamento — 14.3/14.4 (Fase 5: extração em segundo plano)
// ---------------------------------------------------------------------------

export interface ProcessImportOut {
  id: number
  status: ImportStatus
  started_at: string | null
}

export interface ImportStatusOut {
  id: number
  status: ImportStatus
  progress: { pages_total: number | null; pages_processed: number | null }
  started_at: string | null
  finished_at: string | null
  summary: { items_extracted: number; warnings: number }
  error: { code: string; message: string } | null
}

export const processImport = (importId: number, strategy?: string) =>
  request<ProcessImportOut>(`/imports/${importId}/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(strategy ? { strategy } : {}),
  })

export const getImportStatus = (importId: number) =>
  request<ImportStatusOut>(`/imports/${importId}/status`)
