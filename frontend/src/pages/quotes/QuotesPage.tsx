import { useEffect, useState } from 'react'
import {
  listFamilies,
  searchComponents,
  type ComponentVariant,
  type FinishGroup,
  type ProductFamily,
} from '../../api/catalog'
import {
  QuotesApiError,
  addComponent,
  addItem,
  createQuote,
  duplicateQuote,
  exportQuotePdf,
  freezeTotals,
  getReviewChecklist,
  getTotals,
  listCustomers,
  listItems,
  listQuotes,
  removeComponent,
  removeItem,
  swapComponent,
  updateItem,
  updateQuoteStatus,
  type Customer,
  type Quote,
  type QuoteItem,
  type QuoteItemComponentSwap,
  type QuoteReviewChecklist,
  type QuoteStatus,
  type QuoteTotals,
} from '../../api/quotes'

const STATUS_TRANSITIONS: Record<QuoteStatus, QuoteStatus[]> = {
  rascunho: ['enviado', 'rejeitado', 'expirado'],
  enviado: ['aprovado', 'rejeitado', 'expirado'],
  aprovado: ['expirado'],
  rejeitado: [],
  expirado: [],
}

function ErrorMessage({ error }: { error: string | null }) {
  if (!error) return null
  return <p style={{ color: 'crimson' }}>{error}</p>
}

function describeError(err: unknown): string {
  if (err instanceof QuotesApiError) {
    return `${err.code}: ${err.message}`
  }
  return String(err)
}

function describeVariant(variant: ComponentVariant): string {
  const price = variant.price ? `${variant.price.currency} ${variant.price.amount.toFixed(2)}` : 'sem preço'
  return `${variant.product ?? variant.component} — ${variant.component} — ${variant.descriptor ?? ''} — ${variant.finish ?? '—'} — ${variant.sku ?? 'sem SKU'} — ${price}`
}

function NewQuoteForm({ customers, onCreated }: { customers: Customer[]; onCreated: (quote: Quote) => void }) {
  const [customerId, setCustomerId] = useState('')
  const [validUntil, setValidUntil] = useState('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      const quote = await createQuote({
        customer_id: Number(customerId),
        valid_until: validUntil || null,
        notes: notes || null,
      })
      setNotes('')
      setValidUntil('')
      onCreated(quote)
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <section>
      <h2>Novo orçamento</h2>
      <form onSubmit={handleCreate}>
        <select value={customerId} onChange={(e) => setCustomerId(e.target.value)} required>
          <option value="">(cliente)</option>
          {customers.map((customer) => (
            <option key={customer.id} value={customer.id}>
              {customer.name}
            </option>
          ))}
        </select>
        <input
          type="date"
          placeholder="Válido até"
          value={validUntil}
          onChange={(e) => setValidUntil(e.target.value)}
        />
        <input placeholder="Observações" value={notes} onChange={(e) => setNotes(e.target.value)} />
        <button type="submit">Criar orçamento</button>
      </form>
      <ErrorMessage error={error} />
    </section>
  )
}

// ---------------------------------------------------------------------------
// Buscador de catálogo reutilizável (Tela 7/8): filtra por família e permite
// escolher uma variação para adicionar/trocar num componente da composição.
// ---------------------------------------------------------------------------

function ComponentPicker({
  families,
  onPick,
  pickLabel = 'Adicionar',
  dimensionFilter,
  finishGroupFilter,
}: {
  families: ProductFamily[]
  onPick: (variant: ComponentVariant) => void
  pickLabel?: string
  // RN-03: restringe os resultados à dimensão já escolhida para a linha.
  dimensionFilter?: string | null
  // RN-05 (camada 1): restringe os resultados ao finish_group compatível
  // com o tipo de componente sendo selecionado.
  finishGroupFilter?: FinishGroup | null
}) {
  const [familyFilter, setFamilyFilter] = useState('')
  const [results, setResults] = useState<ComponentVariant[]>([])
  const [variantId, setVariantId] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function runSearch() {
      try {
        const result = await searchComponents({
          family: familyFilter || undefined,
          dimension: dimensionFilter || undefined,
          finish_group: finishGroupFilter || undefined,
        })
        setResults(result.items)
        setError(null)
      } catch (err) {
        setError(describeError(err))
      }
    }
    void runSearch()
  }, [familyFilter, dimensionFilter, finishGroupFilter])

  function handlePick() {
    const variant = results.find((item) => item.component_variant_id === Number(variantId))
    if (!variant) return
    onPick(variant)
    setVariantId('')
  }

  return (
    <div style={{ display: 'flex', gap: '0.25rem', alignItems: 'center', flexWrap: 'wrap' }}>
      <select value={familyFilter} onChange={(e) => setFamilyFilter(e.target.value)}>
        <option value="">(todas as famílias)</option>
        {families.map((family) => (
          <option key={family.id} value={family.name}>
            {family.name}
          </option>
        ))}
      </select>
      <select value={variantId} onChange={(e) => setVariantId(e.target.value)}>
        <option value="">(selecione uma variação)</option>
        {results.map((item) => (
          <option key={item.component_variant_id} value={item.component_variant_id}>
            {describeVariant(item)}
          </option>
        ))}
      </select>
      <button type="button" onClick={handlePick} disabled={!variantId}>
        {pickLabel}
      </button>
      <ErrorMessage error={error} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tela 7 — montagem: adicionar item com composição (1+ componentes)
// ---------------------------------------------------------------------------

function NewItemForm({
  quoteId,
  families,
  onAdded,
}: {
  quoteId: number
  families: ProductFamily[]
  onAdded: () => void
}) {
  const [label, setLabel] = useState('')
  const [quantity, setQuantity] = useState('1')
  const [pending, setPending] = useState<ComponentVariant[]>([])
  const [error, setError] = useState<string | null>(null)

  function handlePick(variant: ComponentVariant) {
    setPending((prev) => [...prev, variant])
  }

  function handleRemovePending(index: number) {
    setPending((prev) => prev.filter((_, i) => i !== index))
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    if (pending.length === 0) {
      setError('Adicione ao menos um componente à composição.')
      return
    }
    try {
      await addItem(quoteId, {
        label,
        quantity: Number(quantity) || 1,
        components: pending.map((variant) => ({ component_variant_id: variant.component_variant_id })),
      })
      setLabel('')
      setQuantity('1')
      setPending([])
      onAdded()
    } catch (err) {
      setError(describeError(err))
    }
  }

  const pendingTotal = pending.reduce((sum, variant) => sum + (variant.price?.amount ?? 0), 0)

  // RN-03: depois do primeiro componente escolhido, restringe os próximos à
  // mesma dimensão (ex.: tampo e estrutura de uma mesma mesa).
  const dimensionFilter = pending[0]?.dimension?.raw_label ?? null

  return (
    <section>
      <h3>Adicionar item</h3>
      <ComponentPicker
        families={families}
        onPick={handlePick}
        pickLabel="+ componente"
        dimensionFilter={dimensionFilter}
      />
      {pending.length > 0 && (
        <ul>
          {pending.map((variant, index) => (
            <li key={`${variant.component_variant_id}-${index}`}>
              {describeVariant(variant)}{' '}
              <button type="button" onClick={() => handleRemovePending(index)}>
                remover
              </button>
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '0.25rem', alignItems: 'center' }}>
        <input placeholder="Descrição do item" value={label} onChange={(e) => setLabel(e.target.value)} required />
        <input
          type="number"
          min="1"
          placeholder="Quantidade"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
        />
        <button type="submit">Adicionar item (composição: {pendingTotal.toFixed(2)})</button>
      </form>
      <ErrorMessage error={error} />
    </section>
  )
}

// ---------------------------------------------------------------------------
// Tela 8 — edição de item: trocar/adicionar/remover componentes da composição
// ---------------------------------------------------------------------------

function EditItemPanel({
  item,
  quoteId,
  families,
  onChanged,
}: {
  item: QuoteItem
  quoteId: number
  families: ProductFamily[]
  onChanged: () => void
}) {
  const [error, setError] = useState<string | null>(null)
  const [swapResults, setSwapResults] = useState<Record<number, QuoteItemComponentSwap>>({})
  const [justification, setJustification] = useState(item.composition_justification ?? '')

  async function handleSaveJustification(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await updateItem(quoteId, item.id, { composition_justification: justification || null })
      onChanged()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function handleSwap(componentId: number, variant: ComponentVariant) {
    setError(null)
    try {
      const result = await swapComponent(quoteId, item.id, componentId, {
        component_variant_id: variant.component_variant_id,
      })
      setSwapResults((prev) => ({ ...prev, [componentId]: result }))
      onChanged()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function handleRemoveComponent(componentId: number) {
    setError(null)
    try {
      await removeComponent(quoteId, item.id, componentId)
      onChanged()
    } catch (err) {
      if (err instanceof QuotesApiError && err.code === 'ULTIMO_COMPONENTE_DA_LINHA') {
        if (window.confirm('Este é o único componente da linha. Remover a linha inteira?')) {
          await removeItem(quoteId, item.id)
          onChanged()
        }
        return
      }
      setError(describeError(err))
    }
  }

  async function handleAddComponent(variant: ComponentVariant) {
    setError(null)
    try {
      await addComponent(quoteId, item.id, { component_variant_id: variant.component_variant_id })
      onChanged()
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <tr>
      <td colSpan={5} style={{ background: '#f7f7f7' }}>
        <strong>Editar composição — {item.label}</strong>
        {item.missing_required_components.length > 0 && (
          <div style={{ color: 'crimson', marginTop: '0.25rem' }}>
            <p>
              Pendências: faltam componente(s) obrigatório(s) —{' '}
              {item.missing_required_components.join(', ')}.
            </p>
            <form onSubmit={handleSaveJustification} style={{ display: 'flex', gap: '0.25rem', alignItems: 'center' }}>
              <textarea
                placeholder="Justificativa para linha incompleta"
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
                rows={2}
                style={{ flex: 1 }}
              />
              <button type="submit">salvar justificativa</button>
            </form>
          </div>
        )}
        <ul>
          {item.components.map((component) => {
            const swap = swapResults[component.id]
            return (
              <li key={component.id} style={{ marginBottom: '0.5rem' }}>
                <div>
                  {component.sku} — {component.frozen_currency} {component.frozen_unit_price.toFixed(2)}{' '}
                  <button type="button" onClick={() => handleRemoveComponent(component.id)}>
                    remover componente
                  </button>
                </div>
                {swap && swap.price_changed && (
                  <p style={{ color: 'darkorange' }}>
                    Preço atualizado de {swap.frozen_currency} {swap.previous_frozen_unit_price.toFixed(2)} para{' '}
                    {swap.frozen_currency} {swap.frozen_unit_price.toFixed(2)}.
                  </p>
                )}
                <ComponentPicker
                  families={families}
                  pickLabel="Trocar variação"
                  onPick={(variant) => handleSwap(component.id, variant)}
                />
              </li>
            )
          })}
        </ul>
        <div>
          <strong>+ componente</strong>
          <ComponentPicker families={families} pickLabel="Adicionar componente" onPick={handleAddComponent} />
        </div>
        <ErrorMessage error={error} />
      </td>
    </tr>
  )
}

function ItemRow({
  item,
  quoteId,
  families,
  onChanged,
}: {
  item: QuoteItem
  quoteId: number
  families: ProductFamily[]
  onChanged: () => void
}) {
  const [quantity, setQuantity] = useState(String(item.quantity))
  const [discountPercent, setDiscountPercent] = useState(item.discount_percent?.toString() ?? '')
  const [discountReason, setDiscountReason] = useState(item.discount_reason ?? '')
  const [editing, setEditing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSave(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await updateItem(quoteId, item.id, {
        quantity: Number(quantity) || 1,
        discount_percent: discountPercent ? Number(discountPercent) : null,
        discount_reason: discountReason || null,
      })
      onChanged()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function handleRemoveItem() {
    if (!window.confirm(`Remover a linha "${item.label}"?`)) return
    setError(null)
    try {
      await removeItem(quoteId, item.id)
      onChanged()
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <>
      <tr>
        <td>{item.id}</td>
        <td>{item.label}</td>
        <td>
          {item.components.map((c) => (
            <div key={c.id}>
              {c.sku} — {c.frozen_currency} {c.frozen_unit_price.toFixed(2)}
            </div>
          ))}
          {item.pricing_pendencias.length > 0 && (
            <div style={{ color: 'crimson', marginTop: '0.25rem' }}>
              {item.pricing_pendencias.map((pendencia, index) => (
                <p key={index}>{pendencia}</p>
              ))}
            </div>
          )}
        </td>
        <td>
          <form onSubmit={handleSave} style={{ display: 'flex', gap: '0.25rem', alignItems: 'center' }}>
            <input
              type="number"
              min="1"
              style={{ width: '4rem' }}
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
            />
            <input
              type="number"
              min="0"
              max="100"
              placeholder="% desc."
              style={{ width: '5rem' }}
              value={discountPercent}
              onChange={(e) => setDiscountPercent(e.target.value)}
            />
            <input
              placeholder="Justificativa"
              style={{ width: '8rem' }}
              value={discountReason}
              onChange={(e) => setDiscountReason(e.target.value)}
            />
            <button type="submit">salvar</button>
          </form>
          <div style={{ marginTop: '0.25rem' }}>
            <button type="button" onClick={() => setEditing((prev) => !prev)}>
              {editing ? 'fechar composição' : 'editar composição'}
            </button>{' '}
            <button type="button" onClick={() => void handleRemoveItem()}>
              remover linha
            </button>
          </div>
          <ErrorMessage error={error} />
        </td>
        <td>{item.line_subtotal.toFixed(2)}</td>
      </tr>
      {editing && <EditItemPanel item={item} quoteId={quoteId} families={families} onChanged={onChanged} />}
    </>
  )
}

function QuoteDetail({
  quote,
  onChanged,
  onDuplicated,
}: {
  quote: Quote
  onChanged: () => void
  onDuplicated: (quote: Quote) => void
}) {
  const [items, setItems] = useState<QuoteItem[]>([])
  const [families, setFamilies] = useState<ProductFamily[]>([])
  const [totals, setTotals] = useState<QuoteTotals | null>(null)
  const [checklist, setChecklist] = useState<QuoteReviewChecklist | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function reload() {
    try {
      const [itemsData, familiesData, totalsData, checklistData] = await Promise.all([
        listItems(quote.id),
        listFamilies(),
        getTotals(quote.id),
        getReviewChecklist(quote.id),
      ])
      setItems(itemsData)
      setFamilies(familiesData)
      setTotals(totalsData)
      setChecklist(checklistData)
      setError(null)
    } catch (err) {
      setError(describeError(err))
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- carga dos itens/totais ao trocar de orçamento
    void reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quote.id])

  async function handleFreeze() {
    setError(null)
    try {
      const frozen = await freezeTotals(quote.id)
      setTotals(frozen)
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function handleStatusChange(status: QuoteStatus) {
    setError(null)
    try {
      await updateQuoteStatus(quote.id, status)
      onChanged()
    } catch (err) {
      setError(describeError(err))
    }
  }

  function handleItemChanged() {
    void reload()
  }

  async function handleExportPdf() {
    setError(null)
    try {
      const blob = await exportQuotePdf(quote.id)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${quote.quote_number}.pdf`
      link.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function handleDuplicate() {
    setError(null)
    const confirmed = window.confirm(
      `Este orçamento será duplicado com os preços da tabela vigente atual. ` +
        `Os valores podem ser diferentes dos deste orçamento (tabela ${quote.price_table.code}). Continuar?`,
    )
    if (!confirmed) return

    try {
      const duplicated = await duplicateQuote(quote.id)
      onDuplicated(duplicated)
    } catch (err) {
      setError(describeError(err))
    }
  }

  const transitions = STATUS_TRANSITIONS[quote.status] ?? []

  return (
    <section>
      <h2>
        {quote.quote_number} — {quote.customer.name}
      </h2>
      <p>
        Status: <strong>{quote.status}</strong> | Tabela de preço: {quote.price_table.code} (
        {quote.price_table.status})
      </p>
      {quote.source_quote_id !== null && <p>Duplicado do orçamento #{quote.source_quote_id}.</p>}
      <p>
        <button type="button" onClick={() => void handleDuplicate()}>
          Duplicar orçamento
        </button>
      </p>
      {transitions.length > 0 && (
        <p>
          Mudar status para:{' '}
          {transitions.map((status) => (
            <button key={status} onClick={() => handleStatusChange(status)} style={{ marginRight: '0.5rem' }}>
              {status}
            </button>
          ))}
        </p>
      )}

      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Item</th>
            <th>Componentes</th>
            <th>Quantidade / desconto / ações</th>
            <th>Subtotal</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <ItemRow key={item.id} item={item} quoteId={quote.id} families={families} onChanged={handleItemChanged} />
          ))}
        </tbody>
      </table>

      {quote.status === 'rascunho' && (
        <NewItemForm quoteId={quote.id} families={families} onAdded={() => void reload()} />
      )}

      {checklist && (
        <section>
          <h3>Checklist de revisão final (RN-18)</h3>
          <ul>
            {checklist.items.map((checkItem) => (
              <li key={checkItem.code} style={{ color: checkItem.ok ? 'inherit' : 'crimson' }}>
                {checkItem.ok ? '✓' : '✗'} {checkItem.label}
                {!checkItem.ok && (
                  <ul>
                    {checkItem.pendencias.map((pendencia, index) => (
                      <li key={index}>{pendencia}</li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {totals && (
        <section>
          <h3>Totais{totals.is_snapshot ? ' (congelado)' : ' (ao vivo)'}</h3>
          <p>
            Subtotal: {totals.currency} {totals.subtotal.toFixed(2)} | Desconto: {totals.currency}{' '}
            {totals.discount_amount.toFixed(2)} ({totals.discount_percent.toFixed(2)}%) | Total:{' '}
            {totals.currency} {totals.total.toFixed(2)}
          </p>
          {totals.warnings.map((warning) => (
            <p key={warning.code} style={{ color: 'darkorange' }}>
              {warning.message}
            </p>
          ))}
          <button onClick={handleFreeze} disabled={!checklist?.ready}>
            Congelar total
          </button>
          <button onClick={() => void handleExportPdf()} disabled={!totals.is_snapshot} style={{ marginLeft: '0.5rem' }}>
            Exportar PDF
          </button>
        </section>
      )}

      <ErrorMessage error={error} />
    </section>
  )
}

export function QuotesPage() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [quotes, setQuotes] = useState<Quote[]>([])
  const [selectedQuoteId, setSelectedQuoteId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function reload() {
    try {
      const [customersData, quotesData] = await Promise.all([listCustomers(), listQuotes()])
      setCustomers(customersData)
      setQuotes(quotesData)
      setError(null)
    } catch (err) {
      setError(describeError(err))
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- carga inicial de clientes/orçamentos
    void reload()
  }, [])

  function handleCreated(quote: Quote) {
    setQuotes((prev) => [...prev, quote])
    setSelectedQuoteId(quote.id)
  }

  function handleDuplicated(quote: Quote) {
    setQuotes((prev) => [...prev, quote])
    setSelectedQuoteId(quote.id)
  }

  const selectedQuote = quotes.find((q) => q.id === selectedQuoteId) ?? null

  async function handleSelectionChanged() {
    await reload()
  }

  return (
    <div>
      <h1>Orçamentos — montagem</h1>
      <ErrorMessage error={error} />

      <section>
        <h2>Orçamentos existentes</h2>
        <ul>
          {quotes.map((quote) => (
            <li key={quote.id}>
              <button onClick={() => setSelectedQuoteId(quote.id)}>
                {quote.quote_number} — {quote.customer.name} ({quote.status})
              </button>
            </li>
          ))}
        </ul>
      </section>

      <NewQuoteForm customers={customers} onCreated={handleCreated} />

      {selectedQuote && (
        <QuoteDetail
          quote={selectedQuote}
          onChanged={() => void handleSelectionChanged()}
          onDuplicated={handleDuplicated}
        />
      )}
    </div>
  )
}
