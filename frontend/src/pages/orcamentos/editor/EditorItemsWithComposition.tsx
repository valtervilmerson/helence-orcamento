import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import type { QuoteItem } from '../../../api/quotes'
import type { OrcamentoData } from './useOrcamento'
import { CompositionDrawer } from './CompositionDrawer'
import { EditorItemsPage } from './EditorPage'

type DrawerState =
  | { mode: 'closed' }
  | { mode: 'create' }
  | { mode: 'edit'; item: QuoteItem }

export function EditorItemsWithComposition() {
  const data = useOutletContext<OrcamentoData>()
  const [drawer, setDrawer] = useState<DrawerState>({ mode: 'closed' })

  if (!data.quote) return null

  const closeDrawer = () => setDrawer({ mode: 'closed' })

  return (
    <>
      <EditorItemsPage
        onEditComposition={(item) => setDrawer({ mode: 'edit', item })}
        onAddReadyProduct={() => setDrawer({ mode: 'create' })}
      />
      {drawer.mode !== 'closed' && (
        <CompositionDrawer
          quoteId={data.quoteId}
          item={drawer.mode === 'edit' ? drawer.item : null}
          onClose={closeDrawer}
          onChanged={data.recarregar}
        />
      )}
    </>
  )
}
