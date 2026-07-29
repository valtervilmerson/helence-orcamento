import { useCallback, useEffect, useState } from 'react'
import { listDimensions, listFamilies, listFinishes, type Dimension, type Finish, type ProductFamily } from '../../../api/catalog'
import { getQuote, getReviewChecklist, getTotals, listItems, type Quote, type QuoteItem, type QuoteReviewChecklist, type QuoteTotals } from '../../../api/quotes'

export interface OrcamentoData {
  quoteId: number
  quote: Quote | null
  items: QuoteItem[]
  totals: QuoteTotals | null
  checklist: QuoteReviewChecklist | null
  families: ProductFamily[]
  finishes: Finish[]
  dimensions: Dimension[]
  loading: boolean
  error: string | null
  recarregar: () => Promise<void>
}

export function useOrcamento(quoteId: number): OrcamentoData {
  const [quote, setQuote] = useState<Quote | null>(null)
  const [items, setItems] = useState<QuoteItem[]>([])
  const [totals, setTotals] = useState<QuoteTotals | null>(null)
  const [checklist, setChecklist] = useState<QuoteReviewChecklist | null>(null)
  const [families, setFamilies] = useState<ProductFamily[]>([])
  const [finishes, setFinishes] = useState<Finish[]>([])
  const [dimensions, setDimensions] = useState<Dimension[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const recarregar = useCallback(async () => {
    if (!Number.isInteger(quoteId) || quoteId <= 0) { setError('Orçamento inválido.'); setLoading(false); return }
    setLoading(true)
    try {
      const [q, i, t, c, f, fi, d] = await Promise.all([
        getQuote(quoteId), listItems(quoteId), getTotals(quoteId), getReviewChecklist(quoteId),
        listFamilies(), listFinishes(), listDimensions(),
      ])
      setQuote(q); setItems(i); setTotals(t); setChecklist(c); setFamilies(f); setFinishes(fi); setDimensions(d); setError(null)
    } catch (err) { setError(err instanceof Error ? err.message : String(err)) }
    finally { setLoading(false) }
  }, [quoteId])

  useEffect(() => { void recarregar() }, [recarregar])
  return { quoteId, quote, items, totals, checklist, families, finishes, dimensions, loading, error, recarregar }
}
