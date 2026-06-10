import { useEffect, useState } from 'react'
import {
  listFamilies,
  searchComponents,
  type ComponentVariant,
  type ProductFamily,
} from '../../api/catalog'
import {
  QuotesApiError,
  addItem,
  createQuote,
  freezeTotals,
  getTotals,
  listCustomers,
  listItems,
  listQuotes,
  updateItem,
  updateQuoteStatus,
  type Customer,
  type Quote,
  type QuoteItem,
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

function AddItemForm({
  quoteId,
  families,
  onAdded,
}: {
  quoteId: number
  families: ProductFamily[]
  onAdded: () => void
}) {
  const [familyFilter, setFamilyFilter] = useState('')
  const [results, setResults] = useState<ComponentVariant[]>([])
  const [variantId, setVariantId] = useState('')
  const [label, setLabel] = useState('')
  const [quantity, setQuantity] = useState('1')
  const [error, setError] = useState<string | null>(null)

  async function runSearch() {
    try {
      const result = await searchComponents({ family: familyFilter || undefined })
      setResults(result.items)
      setError(null)
    } catch (err) {
      setError(describeError(err))
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- busca de variações ao filtrar
    void runSearch()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [familyFilter])

  async function handleAdd(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await addItem(quoteId, {
        component_variant_id: Number(variantId),
        label,
        quantity: Number(quantity) || 1,
      })
      setLabel('')
      setQuantity('1')
      setVariantId('')
      onAdded()
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <section>
      <h3>Adicionar item</h3>
      <div>
        <label>
          Família:{' '}
          <select value={familyFilter} onChange={(e) => setFamilyFilter(e.target.value)}>
            <option value="">(todas)</option>
            {families.map((family) => (
              <option key={family.id} value={family.name}>
                {family.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <form onSubmit={handleAdd}>
        <select value={variantId} onChange={(e) => setVariantId(e.target.value)} required>
          <option value="">(variação)</option>
          {results.map((item) => (
            <option key={item.component_variant_id} value={item.component_variant_id}>
              {item.product ?? item.component} — {item.descriptor ?? ''} — {item.finish ?? '—'} —{' '}
              {item.sku ?? 'sem SKU'} —{' '}
              {item.price ? `${item.price.currency} ${item.price.amount.toFixed(2)}` : 'sem preço'}
            </option>
          ))}
        </select>
        <input placeholder="Descrição do item" value={label} onChange={(e) => setLabel(e.target.value)} required />
        <input
          type="number"
          min="1"
          placeholder="Quantidade"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
        />
        <button type="submit">Adicionar</button>
      </form>
      <ErrorMessage error={error} />
    </section>
  )
}

function ItemRow({ item, quoteId, onChanged }: { item: QuoteItem; quoteId: number; onChanged: () => void }) {
  const [quantity, setQuantity] = useState(String(item.quantity))
  const [discountPercent, setDiscountPercent] = useState(item.discount_percent?.toString() ?? '')
  const [discountReason, setDiscountReason] = useState(item.discount_reason ?? '')
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

  return (
    <tr>
      <td>{item.id}</td>
      <td>{item.label}</td>
      <td>
        {item.components.map((c) => (
          <div key={c.id}>
            {c.sku} — {c.frozen_currency} {c.frozen_unit_price.toFixed(2)}
          </div>
        ))}
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
        <ErrorMessage error={error} />
      </td>
      <td>{item.line_subtotal.toFixed(2)}</td>
    </tr>
  )
}

function QuoteDetail({ quote, onChanged }: { quote: Quote; onChanged: () => void }) {
  const [items, setItems] = useState<QuoteItem[]>([])
  const [families, setFamilies] = useState<ProductFamily[]>([])
  const [totals, setTotals] = useState<QuoteTotals | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function reload() {
    try {
      const [itemsData, familiesData, totalsData] = await Promise.all([
        listItems(quote.id),
        listFamilies(),
        getTotals(quote.id),
      ])
      setItems(itemsData)
      setFamilies(familiesData)
      setTotals(totalsData)
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
            <th>Quantidade / desconto</th>
            <th>Subtotal</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <ItemRow key={item.id} item={item} quoteId={quote.id} onChanged={handleItemChanged} />
          ))}
        </tbody>
      </table>

      {quote.status === 'rascunho' && (
        <AddItemForm quoteId={quote.id} families={families} onAdded={() => void reload()} />
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
          <button onClick={handleFreeze}>Congelar total</button>
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

  const selectedQuote = quotes.find((q) => q.id === selectedQuoteId) ?? null

  async function handleSelectionChanged() {
    await reload()
  }

  return (
    <div>
      <h1>Orçamentos — montagem básica</h1>
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

      {selectedQuote && <QuoteDetail quote={selectedQuote} onChanged={() => void handleSelectionChanged()} />}
    </div>
  )
}
