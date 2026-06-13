const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export interface ApiError {
  error: { code: string; message: string; details?: Record<string, unknown> }
}

export class QuotesApiError extends Error {
  code: string
  details?: Record<string, unknown>

  constructor(body: ApiError) {
    super(body.error.message)
    this.code = body.error.code
    this.details = body.error.details
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })

  if (response.status === 204) {
    return undefined as T
  }

  const body = await response.json()

  if (!response.ok) {
    throw new QuotesApiError(body as ApiError)
  }

  return body as T
}

// ---------------------------------------------------------------------------
// Clientes
// ---------------------------------------------------------------------------

export interface Customer {
  id: number
  name: string
}

export const listCustomers = () => request<Customer[]>('/customers')

// ---------------------------------------------------------------------------
// Orçamentos — 14.10
// ---------------------------------------------------------------------------

export type QuoteStatus = 'rascunho' | 'enviado' | 'aprovado' | 'rejeitado' | 'expirado'

export interface PriceTableSummary {
  id: number
  code: string
  status: string
}

export interface UserSummary {
  id: number
  name: string
}

export interface Quote {
  id: number
  quote_number: string
  status: QuoteStatus
  customer: Customer
  price_table: PriceTableSummary
  created_by: UserSummary | null
  created_at: string
  valid_until: string | null
  notes: string | null
  source_quote_id: number | null
}

export const listQuotes = () => request<Quote[]>('/quotes')
export const getQuote = (id: number) => request<Quote>(`/quotes/${id}`)
export const createQuote = (data: { customer_id: number; valid_until?: string | null; notes?: string | null }) =>
  request<Quote>('/quotes', { method: 'POST', body: JSON.stringify(data) })
export const updateQuoteStatus = (id: number, status: QuoteStatus) =>
  request<Quote>(`/quotes/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) })
export const duplicateQuote = (id: number) =>
  request<Quote>(`/quotes/${id}/duplicate`, { method: 'POST' })

// ---------------------------------------------------------------------------
// Itens — 14.11/14.12 (um único componente por item)
// ---------------------------------------------------------------------------

export interface QuoteItemComponent {
  id: number
  component_variant_id: number
  sku: string
  frozen_unit_price: number
  frozen_currency: string
  frozen_at: string
}

export interface QuoteItem {
  id: number
  quote_id: number
  label: string
  quantity: number
  discount_percent: number | null
  discount_amount: number | null
  discount_reason: string | null
  notes: string | null
  composition_justification: string | null
  missing_required_components: string[]
  pricing_pendencias: string[]
  components: QuoteItemComponent[]
  line_subtotal: number
}

export const listItems = (quoteId: number) => request<QuoteItem[]>(`/quotes/${quoteId}/items`)

export const addItem = (
  quoteId: number,
  data: {
    label: string
    quantity?: number
    product_id?: number | null
    notes?: string | null
    // Forma simplificada (um único componente) ou composição completa
    // (`components`) — exatamente uma das duas.
    component_variant_id?: number
    components?: { component_variant_id: number }[]
  },
) => request<QuoteItem>(`/quotes/${quoteId}/items`, { method: 'POST', body: JSON.stringify(data) })

export const updateItem = (
  quoteId: number,
  itemId: number,
  data: Partial<{
    quantity: number
    discount_percent: number | null
    discount_amount: number | null
    discount_reason: string | null
    notes: string | null
    composition_justification: string | null
  }>,
) =>
  request<QuoteItem>(`/quotes/${quoteId}/items/${itemId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })

export const removeItem = (quoteId: number, itemId: number) =>
  request<void>(`/quotes/${quoteId}/items/${itemId}`, { method: 'DELETE' })

// ---------------------------------------------------------------------------
// Componentes de um item — composição (14.11/14.12)
// ---------------------------------------------------------------------------

export const addComponent = (quoteId: number, itemId: number, data: { component_variant_id: number }) =>
  request<QuoteItem>(`/quotes/${quoteId}/items/${itemId}/components`, {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const removeComponent = (quoteId: number, itemId: number, componentId: number) =>
  request<QuoteItem>(`/quotes/${quoteId}/items/${itemId}/components/${componentId}`, {
    method: 'DELETE',
  })

export interface QuoteItemComponentSwap {
  id: number
  component_variant_id: number
  sku: string
  previous_frozen_unit_price: number
  frozen_unit_price: number
  frozen_currency: string
  frozen_at: string
  price_changed: boolean
}

export const swapComponent = (
  quoteId: number,
  itemId: number,
  componentId: number,
  data: { component_variant_id: number },
) =>
  request<QuoteItemComponentSwap>(`/quotes/${quoteId}/items/${itemId}/components/${componentId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })

// ---------------------------------------------------------------------------
// Totais — 14.13
// ---------------------------------------------------------------------------

export interface QuoteTotalWarning {
  code: string
  message: string
}

export interface QuoteTotals {
  quote_id: number
  subtotal: number
  discount_percent: number
  discount_amount: number
  tax_amount: number
  freight_amount: number
  total: number
  currency: string
  is_snapshot: boolean
  calculated_at: string
  warnings: QuoteTotalWarning[]
}

export const getTotals = (quoteId: number) => request<QuoteTotals>(`/quotes/${quoteId}/totals`)
export const freezeTotals = (quoteId: number) =>
  request<QuoteTotals>(`/quotes/${quoteId}/totals/freeze`, { method: 'POST' })
