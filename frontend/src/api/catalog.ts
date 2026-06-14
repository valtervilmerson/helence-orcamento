import { fetchWithRetry } from './fetchWithRetry'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'

export interface ApiError {
  error: { code: string; message: string; details?: Record<string, unknown> }
}

export class CatalogApiError extends Error {
  code: string
  details?: Record<string, unknown>

  constructor(body: ApiError) {
    super(body.error.message)
    this.code = body.error.code
    this.details = body.error.details
  }
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
    throw new CatalogApiError(body as ApiError)
  }

  return body as T
}

// ---------------------------------------------------------------------------
// Famílias
// ---------------------------------------------------------------------------

export interface ProductFamily {
  id: number
  name: string
  description: string | null
}

export const listFamilies = () => request<ProductFamily[]>('/catalog/families')
export const createFamily = (data: { name: string; description?: string | null }) =>
  request<ProductFamily>('/catalog/families', { method: 'POST', body: JSON.stringify(data) })
export const deleteFamily = (id: number) =>
  request<void>(`/catalog/families/${id}`, { method: 'DELETE' })

// ---------------------------------------------------------------------------
// Dimensões
// ---------------------------------------------------------------------------

export interface Dimension {
  id: number
  width_mm: number | null
  depth_mm: number | null
  diameter_mm: number | null
  height_mm: number | null
  raw_label: string | null
}

export const listDimensions = () => request<Dimension[]>('/catalog/dimensions')
export const createDimension = (data: Omit<Dimension, 'id'>) =>
  request<Dimension>('/catalog/dimensions', { method: 'POST', body: JSON.stringify(data) })
export const deleteDimension = (id: number) =>
  request<void>(`/catalog/dimensions/${id}`, { method: 'DELETE' })

// ---------------------------------------------------------------------------
// Acabamentos
// ---------------------------------------------------------------------------

export type FinishGroup = 'madeirado' | 'metalico' | 'pe_estrutura' | 'outro'

export interface Finish {
  id: number
  name: string
  finish_group: FinishGroup | null
  description: string | null
}

export const listFinishes = () => request<Finish[]>('/catalog/finishes')
export const createFinish = (data: {
  name: string
  finish_group?: FinishGroup | null
  description?: string | null
}) => request<Finish>('/catalog/finishes', { method: 'POST', body: JSON.stringify(data) })
export const deleteFinish = (id: number) =>
  request<void>(`/catalog/finishes/${id}`, { method: 'DELETE' })

// ---------------------------------------------------------------------------
// Tipos de componente
// ---------------------------------------------------------------------------

export interface ProductComponentType {
  id: number
  name: string
  description: string | null
  finish_group: FinishGroup | null
}

export const listComponentTypes = () =>
  request<ProductComponentType[]>('/catalog/component-types')
export const createComponentType = (data: {
  name: string
  description?: string | null
  finish_group?: FinishGroup | null
}) =>
  request<ProductComponentType>('/catalog/component-types', {
    method: 'POST',
    body: JSON.stringify(data),
  })
export const deleteComponentType = (id: number) =>
  request<void>(`/catalog/component-types/${id}`, { method: 'DELETE' })

// ---------------------------------------------------------------------------
// Produtos-base
// ---------------------------------------------------------------------------

export interface Product {
  id: number
  family_id: number
  name: string
  dimension_id: number | null
}

export const listProducts = () => request<Product[]>('/catalog/products')
export const createProduct = (data: { family_id: number; name: string; dimension_id?: number | null }) =>
  request<Product>('/catalog/products', { method: 'POST', body: JSON.stringify(data) })
export const deleteProduct = (id: number) =>
  request<void>(`/catalog/products/${id}`, { method: 'DELETE' })

// ---------------------------------------------------------------------------
// Variações vendáveis (component_variants + sku + price)
// ---------------------------------------------------------------------------

export interface ComponentVariantDimension {
  width_mm: number | null
  depth_mm: number | null
  diameter_mm: number | null
  height_mm: number | null
  raw_label: string | null
}

export interface ComponentVariantPrice {
  amount: number
  currency: string
}

export interface ComponentVariant {
  component_variant_id: number
  family: string | null
  family_id: number | null
  product: string | null
  component: string
  descriptor: string | null
  description: string | null
  dimension: ComponentVariantDimension | null
  finish: string | null
  finish_group: FinishGroup | null
  sku: string | null
  price: ComponentVariantPrice | null
  source: string
}

export interface ComponentVariantSearchResult {
  items: ComponentVariant[]
  page: number
  page_size: number
  total: number
}

export const searchComponents = (params: Record<string, string | number | undefined> = {}) => {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') {
      query.set(key, String(value))
    }
  }
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return request<ComponentVariantSearchResult>(`/components${suffix}`)
}

export interface ComponentVariantInput {
  product_id?: number | null
  component_id: number
  dimension_id?: number | null
  finish_id?: number | null
  descriptor?: string | null
  description?: string | null
  sku?: { code: string; notes?: string | null } | null
  price?: { amount: number; currency: string } | null
}

export const createComponent = (data: ComponentVariantInput) =>
  request<ComponentVariant>('/components', { method: 'POST', body: JSON.stringify(data) })
export const getComponent = (id: number) => request<ComponentVariant>(`/components/${id}`)
export const deleteComponent = (id: number) =>
  request<void>(`/components/${id}`, { method: 'DELETE' })
