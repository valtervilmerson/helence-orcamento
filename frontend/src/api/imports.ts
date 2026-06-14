import { fetchWithRetry } from './fetchWithRetry'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'

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
  const response = await fetchWithRetry(`${API_BASE_URL}${path}`, init)

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
  items_blocking_publication: number
  linked_price_table: PriceTableSummary | null
}

export interface ImportListOut {
  items: ImportListItem[]
  page: number
  page_size: number
  total: number
}

function normalizeImportListItem(
  item: Omit<ImportListItem, 'items_blocking_publication'> & {
    items_blocking_publication?: number
  },
): ImportListItem {
  return {
    ...item,
    items_blocking_publication: item.items_blocking_publication ?? item.items_pending_review ?? 0,
  }
}

export const uploadImport = (file: File, notes?: string) => {
  const formData = new FormData()
  formData.append('file', file)
  if (notes) {
    formData.append('notes', notes)
  }
  return request<ImportedFile>('/imports', { method: 'POST', body: formData })
}

export type FinishGroup = 'madeirado' | 'metalico' | 'pe_estrutura' | 'outro'

export interface ImportJsonPriceTableIn {
  code: string
  name?: string | null
  valid_from?: string | null
}

export interface ImportJsonSourceIn {
  description?: string | null
  generated_by?: string | null
  generated_at?: string | null
}

export interface ImportJsonItemIn {
  ref?: string | null
  family: string
  product_context: string
  component_type: string
  description?: string | null
  dimension: string
  finish: string
  finish_group?: FinishGroup | null
  sku: string
  price: number
  currency?: string
  confidence?: number | null
  notes?: string | null
}

export interface ImportJsonIn {
  contract_version: '1.0'
  price_table: ImportJsonPriceTableIn
  source?: ImportJsonSourceIn | null
  items: ImportJsonItemIn[]
}

export interface ImportJsonItemResult {
  ref?: string | null
  extracted_item_id: number
  review_status: 'aprovado' | 'pendente'
  reasons?: string[] | null
}

export interface ImportJsonOut {
  imported_file_id: number
  price_table: PriceTableSummary
  items_total: number
  items_published: number
  items_pending_review: number
  warnings_count: number
  items: ImportJsonItemResult[]
}

export const uploadImportJson = (payload: ImportJsonIn, originalFilename?: string) => {
  const query = new URLSearchParams()
  if (originalFilename) {
    query.set('original_filename', originalFilename)
  }
  const qs = query.toString()
  return request<ImportJsonOut>(`/imports/json${qs ? `?${qs}` : ''}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export const listImports = (params?: { status?: ImportStatus; page?: number; page_size?: number }) => {
  const query = new URLSearchParams()
  if (params?.status) query.set('status', params.status)
  if (params?.page) query.set('page', String(params.page))
  if (params?.page_size) query.set('page_size', String(params.page_size))
  const qs = query.toString()
  return request<ImportListOut>(`/imports${qs ? `?${qs}` : ''}`).then((result) => ({
    ...result,
    items: result.items.map((item) => normalizeImportListItem(item)),
  }))
}

export const getImportSummary = async (importId: number) => {
  try {
    const item = await request<ImportListItem>(`/imports/${importId}`)
    return normalizeImportListItem(item)
  } catch (err) {
    if (!(err instanceof ImportsApiError) || err.code !== 'HTTP_404') {
      throw err
    }

    const fallback = await listImports({ page_size: 200 })
    const item = fallback.items.find((entry) => entry.id === importId)
    if (!item) {
      throw err
    }
    return normalizeImportListItem(item)
  }
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

// ---------------------------------------------------------------------------
// Itens extraídos e revisão — 14.5/14.6 (Fase 6)
// ---------------------------------------------------------------------------

export type ReviewStatus = 'pendente' | 'revisado' | 'aprovado' | 'rejeitado' | 'corrigido'
export type ConfidenceLevel = 'alta' | 'media' | 'baixa'
export type ReviewDecisionType = 'aprovado' | 'rejeitado' | 'corrigido'

export interface ExtractedItem {
  id: number
  imported_page_id: number
  page_number: number
  family_raw: string | null
  product_context_raw: string | null
  component_type_raw: string | null
  description_raw: string | null
  dimension_raw: string | null
  finish_raw: string | null
  sku_raw: string | null
  price_raw: string | null
  confidence: number | null
  confidence_level: ConfidenceLevel | null
  review_status: ReviewStatus
  source_text: string | null
}

export interface ExtractedItemsListOut {
  items: ExtractedItem[]
  page: number
  page_size: number
  total: number
}

export interface ExtractedItemsFilters {
  review_status?: ReviewStatus
  confidence_level?: ConfidenceLevel
  page_number?: number
  search?: string
  page?: number
  page_size?: number
}

export const getImportItems = (importId: number, filters?: ExtractedItemsFilters) => {
  const query = new URLSearchParams()
  if (filters?.review_status) query.set('review_status', filters.review_status)
  if (filters?.confidence_level) query.set('confidence_level', filters.confidence_level)
  if (filters?.page_number) query.set('page_number', String(filters.page_number))
  if (filters?.search) query.set('search', filters.search)
  if (filters?.page) query.set('page', String(filters.page))
  if (filters?.page_size) query.set('page_size', String(filters.page_size))
  const qs = query.toString()
  return request<ExtractedItemsListOut>(`/imports/${importId}/items${qs ? `?${qs}` : ''}`)
}

export interface ReviewItemIn {
  decision: ReviewDecisionType
  notes?: string
  field?: string
  previous_value?: string | null
  corrected_value?: string
  new_finish_name?: string
  new_finish_group?: FinishGroup
}

export interface ReviewDecisionOut {
  id: number
  decision: ReviewDecisionType
  field_corrected: string | null
  previous_value: string | null
  corrected_value: string | null
  reviewed_by: UserSummary | null
  reviewed_at: string
}

export interface ReviewItemOut {
  id: number
  review_status: ReviewStatus
  decision: ReviewDecisionOut
}

export const reviewExtractedItem = (itemId: number, body: ReviewItemIn) =>
  request<ReviewItemOut>(`/extracted-items/${itemId}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

// ---------------------------------------------------------------------------
// Correção em lote — docs/04 §4 (Fase 6)
// ---------------------------------------------------------------------------

export type BatchCorrectionScope = 'page' | 'page_profile' | 'import'

export interface BatchCorrectionCandidate {
  id: number
  page_number: number
  confidence_level: ConfidenceLevel | null
  previous_value: string | null
  corrected_value: string
}

export interface BatchCorrectionPreviewOut {
  field: string
  previous_value: string | null
  corrected_value: string
  scope: BatchCorrectionScope
  eligible_count: number
  already_decided_count: number
  already_decided_item_ids: number[]
  candidates: BatchCorrectionCandidate[]
}

export interface BatchCorrectionApplyOut {
  field: string
  previous_value: string | null
  corrected_value: string
  scope: BatchCorrectionScope
  applied_count: number
  applied_item_ids: number[]
  skipped_item_ids: number[]
}

export const previewBatchCorrection = (
  itemId: number,
  field: string,
  scope: BatchCorrectionScope,
) => {
  const query = new URLSearchParams({ field, scope })
  return request<BatchCorrectionPreviewOut>(
    `/extracted-items/${itemId}/batch-correction/preview?${query.toString()}`,
  )
}

export const applyBatchCorrection = (
  itemId: number,
  field: string,
  scope: BatchCorrectionScope,
  notes?: string,
) =>
  request<BatchCorrectionApplyOut>(`/extracted-items/${itemId}/batch-correction/apply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ field, scope, notes: notes || undefined }),
  })

// ---------------------------------------------------------------------------
// Aprovação/rejeição em lote — docs/04 §3 (Fase 6)
// ---------------------------------------------------------------------------

export type BatchReviewDecision = 'aprovado' | 'rejeitado'

export interface BatchReviewResultItem {
  item_id: number
  success: boolean
  error_code: string | null
  error_message: string | null
}

export interface BatchReviewOut {
  decision: BatchReviewDecision
  requested_count: number
  succeeded_count: number
  failed_count: number
  results: BatchReviewResultItem[]
}

export const batchReviewExtractedItems = (
  itemIds: number[],
  decision: BatchReviewDecision,
  notes?: string,
) =>
  request<BatchReviewOut>('/extracted-items/batch-review', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ item_ids: itemIds, decision, notes: notes || undefined }),
  })
