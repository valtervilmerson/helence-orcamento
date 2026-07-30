import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import type { QuoteItem } from '../../../api/quotes'
import type { OrcamentoData } from './useOrcamento'
import { EditorItemsPage } from './EditorPage'
import { CompositionDrawer } from './CompositionDrawer'

export function EditorItemsWithComposition() {
  const data = useOutletContext<OrcamentoData>()
  const [item, setItem] = useState<QuoteItem | null>(null)
  if (!data.quote) return null
  return <><EditorItemsPage /><div className="composition-launcher" aria-label="Editar composição"><span>Composição</span>{data.items.map((current) => <button key={current.id} disabled={data.quote?.status !== 'rascunho'} onClick={() => setItem(current)}>{current.label}</button>)}</div><CompositionDrawer quoteId={data.quoteId} item={item} onClose={() => setItem(null)} onChanged={data.recarregar} /></>
}
