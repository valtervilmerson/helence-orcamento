import { useEffect, useState } from 'react'
import {
  getProductComposition,
  listDimensions,
  listFamilies,
  listFinishes,
  listProducts,
  searchComponents,
  type ComponentVariant,
  type Dimension,
  type Finish,
  type FinishGroup,
  type Product,
  type ProductFamily,
} from '../../api/catalog'
import {
  QuotesApiError,
  addComponent,
  addItem,
  createCustomer,
  createQuote,
  deleteQuote,
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
  updateQuoteSettings,
  updateQuoteStatus,
  type Customer,
  type Quote,
  type QuoteItem,
  type QuoteItemComponentSwap,
  type QuoteReviewChecklist,
  type QuoteStatus,
  type QuoteTotals,
} from '../../api/quotes'
import { getSettings } from '../../api/settings'

const STATUS_TRANSITIONS: Record<QuoteStatus, QuoteStatus[]> = {
  rascunho: ['enviado', 'rejeitado', 'expirado'],
  enviado: ['aprovado', 'rejeitado', 'expirado'],
  aprovado: ['expirado'],
  rejeitado: [],
  expirado: [],
}

function ErrorMessage({ error }: { error: string | null }) {
  if (!error) return null
  return <p className="feedback-error">{error}</p>
}

function describeError(err: unknown): string {
  if (err instanceof QuotesApiError) {
    return `${err.code}: ${err.message}`
  }
  return String(err)
}

const STATUS_BADGE_CLASS: Record<QuoteStatus, string> = {
  rascunho: 'badge-neutral',
  enviado: '',
  aprovado: 'badge-success',
  rejeitado: 'badge-danger',
  expirado: 'badge-warning',
}

function StatusBadge({ status }: { status: QuoteStatus }) {
  return <span className={`badge ${STATUS_BADGE_CLASS[status]}`}>{status}</span>
}

// ---------------------------------------------------------------------------
// Combobox de busca: permite digitar parte do nome/SKU/acabamento para
// localizar uma variação entre os resultados já filtrados.
// ---------------------------------------------------------------------------

function VariantCombobox({
  results,
  variantId,
  onSelect,
}: {
  results: ComponentVariant[]
  variantId: string
  onSelect: (id: string) => void
}) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)

  const selected = results.find((item) => item.component_variant_id === Number(variantId))

  const normalized = query.trim().toLowerCase()
  const filtered = normalized
    ? results.filter((item) => describeVariant(item).toLowerCase().includes(normalized))
    : results

  function handleSelect(item: ComponentVariant) {
    onSelect(String(item.component_variant_id))
    setQuery('')
    setOpen(false)
  }

  function handleChange(value: string) {
    setQuery(value)
    setOpen(true)
    if (variantId) onSelect('')
  }

  const inputValue = open || !selected ? query : describeVariant(selected)

  return (
    <div className="combobox" style={{ flex: 1, minWidth: '18rem' }}>
      <input
        type="text"
        placeholder="Digite para buscar por produto, SKU, acabamento..."
        value={inputValue}
        onChange={(e) => handleChange(e.target.value)}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
      />
      {open && (
        <ul className="combobox-list">
          {filtered.length === 0 && <li className="combobox-empty">Nenhuma variação encontrada.</li>}
          {filtered.slice(0, 30).map((item) => (
            <li key={item.component_variant_id}>
              <button type="button" onMouseDown={() => handleSelect(item)}>
                {describeVariant(item)}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function describeVariant(variant: ComponentVariant): string {
  const price = variant.price ? `${variant.price.currency} ${variant.price.amount.toFixed(2)}` : 'sem preço'
  return `${variant.product ?? variant.component} — ${variant.component} — ${variant.descriptor ?? ''} — ${variant.finish ?? '—'} — ${variant.sku ?? 'sem SKU'} — ${price}`
}

function NewCustomerForm({ onCreated }: { onCreated: (customer: Customer) => void }) {
  const [name, setName] = useState('')
  const [document, setDocument] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      const customer = await createCustomer({
        name,
        document: document || null,
        email: email || null,
        phone: phone || null,
      })
      setName('')
      setDocument('')
      setEmail('')
      setPhone('')
      onCreated(customer)
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <section>
      <h2>Novo cliente</h2>
      <form onSubmit={handleCreate} className="action-group">
        <input placeholder="Nome" value={name} onChange={(e) => setName(e.target.value)} required />
        <input placeholder="CNPJ/CPF (opcional)" value={document} onChange={(e) => setDocument(e.target.value)} />
        <input placeholder="E-mail (opcional)" value={email} onChange={(e) => setEmail(e.target.value)} />
        <input placeholder="Telefone (opcional)" value={phone} onChange={(e) => setPhone(e.target.value)} />
        <button type="submit">Criar cliente</button>
      </form>
      <ErrorMessage error={error} />
    </section>
  )
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
  finishes = [],
  dimensions = [],
  onPick,
  pickLabel = 'Adicionar',
  dimensionFilter,
  finishGroupFilter,
}: {
  families: ProductFamily[]
  finishes?: Finish[]
  dimensions?: Dimension[]
  onPick: (variant: ComponentVariant) => void
  pickLabel?: string
  // RN-03: restringe os resultados à dimensão já escolhida para a linha.
  dimensionFilter?: string | null
  // RN-05 (camada 1): restringe os resultados ao finish_group compatível
  // com o tipo de componente sendo selecionado.
  finishGroupFilter?: FinishGroup | null
}) {
  const [familyFilter, setFamilyFilter] = useState('')
  const [finishFilter, setFinishFilter] = useState('')
  const [dimensionFilterManual, setDimensionFilterManual] = useState('')
  const [results, setResults] = useState<ComponentVariant[]>([])
  const [variantId, setVariantId] = useState('')
  const [error, setError] = useState<string | null>(null)

  const effectiveDimension = dimensionFilter || dimensionFilterManual

  useEffect(() => {
    async function runSearch() {
      try {
        const result = await searchComponents({
          family: familyFilter || undefined,
          dimension: effectiveDimension || undefined,
          finish: finishFilter || undefined,
          finish_group: finishGroupFilter || undefined,
        })
        setResults(result.items)
        setError(null)
      } catch (err) {
        setError(describeError(err))
      }
    }
    void runSearch()
  }, [familyFilter, effectiveDimension, finishFilter, finishGroupFilter])

  function handlePick() {
    const variant = results.find((item) => item.component_variant_id === Number(variantId))
    if (!variant) return
    onPick(variant)
    setVariantId('')
  }

  return (
    <div className="component-picker">
      <div className="form-row">
        <div className="form-field">
          <span className="form-field__label">Família</span>
          <select value={familyFilter} onChange={(e) => setFamilyFilter(e.target.value)}>
            <option value="">(todas as famílias)</option>
            {families.map((family) => (
              <option key={family.id} value={family.name}>
                {family.name}
              </option>
            ))}
          </select>
        </div>
        {!finishGroupFilter && (
          <div className="form-field">
            <span className="form-field__label">Acabamento</span>
            <select value={finishFilter} onChange={(e) => setFinishFilter(e.target.value)}>
              <option value="">(todos os acabamentos)</option>
              {finishes.map((finish) => (
                <option key={finish.id} value={finish.name}>
                  {finish.name}
                </option>
              ))}
            </select>
          </div>
        )}
        <div className="form-field">
          <span className="form-field__label">Dimensão</span>
          {dimensionFilter ? (
            <span className="badge badge-neutral">{dimensionFilter}</span>
          ) : (
            <select value={dimensionFilterManual} onChange={(e) => setDimensionFilterManual(e.target.value)}>
              <option value="">(todas as dimensões)</option>
              {dimensions.map((dimension) => (
                <option key={dimension.id} value={dimension.raw_label ?? ''}>
                  {dimension.raw_label ?? `#${dimension.id}`}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>
      <div className="form-row form-row--actions">
        <VariantCombobox results={results} variantId={variantId} onSelect={setVariantId} />
        <button type="button" className="secondary" onClick={handlePick} disabled={!variantId}>
          {pickLabel}
        </button>
      </div>
      <ErrorMessage error={error} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Carrega a composição pré-cadastrada de um produto (expandida recursivamente)
// ---------------------------------------------------------------------------

function ProductCompositionLoader({
  families,
  onLoad,
}: {
  families: ProductFamily[]
  onLoad: (variants: ComponentVariant[], productName: string) => void
}) {
  const [familyFilter, setFamilyFilter] = useState('')
  const [products, setProducts] = useState<Product[]>([])
  const [productId, setProductId] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadProducts() {
      try {
        setProducts(await listProducts())
      } catch (err) {
        setError(describeError(err))
      }
    }
    void loadProducts()
  }, [])

  const family = families.find((f) => f.name === familyFilter)
  const filteredProducts = family ? products.filter((p) => p.family_id === family.id) : products

  async function handleLoad() {
    if (!productId) return
    setError(null)
    try {
      const compositionItems = await getProductComposition(Number(productId))
      if (compositionItems.length === 0) {
        setError('Este produto não tem itens de composição cadastrados.')
        return
      }
      const variants: ComponentVariant[] = []
      for (const item of compositionItems) {
        for (let i = 0; i < item.quantity; i += 1) {
          variants.push(item.variant)
        }
      }
      const product = products.find((p) => p.id === Number(productId))
      onLoad(variants, product?.name ?? '')
      setProductId('')
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <div className="form-row">
      <div className="form-field">
        <span className="form-field__label">Família</span>
        <select
          value={familyFilter}
          onChange={(e) => {
            setFamilyFilter(e.target.value)
            setProductId('')
          }}
        >
          <option value="">(todas as famílias)</option>
          {families.map((f) => (
            <option key={f.id} value={f.name}>
              {f.name}
            </option>
          ))}
        </select>
      </div>
      <div className="form-field" style={{ flex: 1, minWidth: '16rem' }}>
        <span className="form-field__label">Produto</span>
        <select value={productId} onChange={(e) => setProductId(e.target.value)} style={{ width: '100%' }}>
          <option value="">(carregar produto completo)</option>
          {filteredProducts.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>
      <button type="button" className="secondary" onClick={() => void handleLoad()} disabled={!productId}>
        carregar produto completo
      </button>
      <ErrorMessage error={error} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tela 7 — montagem: adicionar item avulso ou composto
// ---------------------------------------------------------------------------

type ItemMode = 'avulso' | 'composto'

function NewItemForm({
  quoteId,
  families,
  finishes,
  dimensions,
  onAdded,
}: {
  quoteId: number
  families: ProductFamily[]
  finishes: Finish[]
  dimensions: Dimension[]
  onAdded: () => void
}) {
  const [mode, setMode] = useState<ItemMode>('avulso')
  const [label, setLabel] = useState('')
  const [quantity, setQuantity] = useState('1')
  // components[0] é sempre o componente base (quando presente)
  const [components, setComponents] = useState<ComponentVariant[]>([])
  const [error, setError] = useState<string | null>(null)

  const baseComponent = components[0] ?? null
  // RN-03: depois do componente base escolhido, restringe os adicionais à mesma dimensão.
  const dimensionFilter = baseComponent?.dimension?.raw_label ?? null
  const totalPrice = components.reduce((sum, v) => sum + (v.price?.amount ?? 0), 0)

  function reset() {
    setLabel('')
    setQuantity('1')
    setComponents([])
    setError(null)
  }

  function handleModeChange(newMode: ItemMode) {
    setMode(newMode)
    reset()
  }

  function handlePickBase(variant: ComponentVariant) {
    setComponents([variant])
    setLabel((prev) => prev || variant.descriptor || variant.component || '')
  }

  function handleAddExtra(variant: ComponentVariant) {
    setComponents((prev) => [...prev, variant])
  }

  function handleRemoveAt(index: number) {
    if (index === 0) {
      // Remover a base limpa tudo
      setComponents([])
      setLabel('')
    } else {
      setComponents((prev) => prev.filter((_, i) => i !== index))
    }
  }

  function handleLoadComposition(variants: ComponentVariant[], productName: string) {
    setComponents(variants)
    setLabel((prev) => prev || productName)
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    if (components.length === 0) {
      setError(mode === 'avulso' ? 'Selecione o componente.' : 'Selecione o componente base.')
      return
    }
    if (mode === 'composto' && components.length < 2) {
      setError('Adicione ao menos um componente além do base para criar um item composto.')
      return
    }
    try {
      await addItem(quoteId, {
        label,
        quantity: Number(quantity) || 1,
        components: components.map((v) => ({ component_variant_id: v.component_variant_id })),
      })
      reset()
      onAdded()
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <section>
      <h3>Adicionar item</h3>

      {/* Seletor de modo */}
      <div className="mode-toggle">
        <span className="mode-toggle__label">Tipo</span>
        <button
          type="button"
          className={mode !== 'avulso' ? 'secondary' : ''}
          onClick={() => handleModeChange('avulso')}
        >
          Avulso
        </button>
        <button
          type="button"
          className={mode !== 'composto' ? 'secondary' : ''}
          onClick={() => handleModeChange('composto')}
        >
          Composto
        </button>
      </div>

      {/* ── Modo: Avulso ── */}
      {mode === 'avulso' && (
        <>
          <div className="form-block">
            <h4 className="form-block__title">Componente</h4>
            {baseComponent ? (
              <div className="list-item-card">
                <span style={{ flex: 1 }}>{describeVariant(baseComponent)}</span>
                <button type="button" className="secondary" onClick={() => setComponents([])}>
                  trocar
                </button>
              </div>
            ) : (
              <ComponentPicker
                families={families}
                finishes={finishes}
                dimensions={dimensions}
                onPick={handlePickBase}
                pickLabel="Selecionar"
              />
            )}
          </div>

          {baseComponent && (
            <div className="form-block">
              <h4 className="form-block__title">Finalizar</h4>
              <form onSubmit={handleSubmit} className="action-group">
                <input
                  placeholder="Descrição do item"
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                  required
                />
                <input
                  type="number"
                  min="1"
                  placeholder="Qtd"
                  style={{ width: '5rem' }}
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                />
                <button type="submit">Adicionar avulso</button>
              </form>
            </div>
          )}
        </>
      )}

      {/* ── Modo: Composto ── */}
      {mode === 'composto' && (
        <>
          <div className="form-block">
            <h4 className="form-block__title">1. Componente base</h4>
            {baseComponent ? (
              <div className="list-item-card">
                <span className="badge badge-composite badge--sm">base</span>
                <span style={{ flex: 1 }}>{describeVariant(baseComponent)}</span>
                <button type="button" className="secondary" onClick={() => handleRemoveAt(0)}>
                  trocar
                </button>
              </div>
            ) : (
              <ComponentPicker
                families={families}
                finishes={finishes}
                dimensions={dimensions}
                onPick={handlePickBase}
                pickLabel="Selecionar como base"
              />
            )}
          </div>

          {baseComponent && (
            <>
              <div className="form-block">
                <h4 className="form-block__title">2. Componentes adicionais</h4>
                {components.slice(1).length > 0 && (
                  <ul className="list-plain form-block__pending">
                    {components.slice(1).map((variant, i) => (
                      <li key={`extra-${variant.component_variant_id}-${i}`} className="list-item-card">
                        <span style={{ flex: 1 }}>{describeVariant(variant)}</span>
                        <button type="button" className="secondary" onClick={() => handleRemoveAt(i + 1)}>
                          remover
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
                <div style={{ marginTop: components.length > 1 ? 'var(--space-3)' : 0 }}>
                  <ComponentPicker
                    families={families}
                    finishes={finishes}
                    dimensions={dimensions}
                    onPick={handleAddExtra}
                    pickLabel="+ componente"
                    dimensionFilter={dimensionFilter}
                  />
                </div>
              </div>

              <div className="form-block">
                <h4 className="form-block__title">Ou carregar composição de produto pronto</h4>
                <ProductCompositionLoader families={families} onLoad={handleLoadComposition} />
              </div>

              <div className="form-block">
                <h4 className="form-block__title">3. Finalizar</h4>
                <form onSubmit={handleSubmit} className="action-group">
                  <input
                    placeholder="Nome do item composto"
                    value={label}
                    onChange={(e) => setLabel(e.target.value)}
                    required
                  />
                  <input
                    type="number"
                    min="1"
                    placeholder="Qtd"
                    style={{ width: '5rem' }}
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                  />
                  <button type="submit" disabled={components.length < 2}>
                    Adicionar composto ({totalPrice.toFixed(2)})
                  </button>
                </form>
                {components.length < 2 && (
                  <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)', margin: 'var(--space-2) 0 0' }}>
                    Adicione ao menos um componente além do base.
                  </p>
                )}
              </div>
            </>
          )}
        </>
      )}

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
  finishes,
  dimensions,
  onChanged,
}: {
  item: QuoteItem
  quoteId: number
  families: ProductFamily[]
  finishes: Finish[]
  dimensions: Dimension[]
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
      <td colSpan={5} style={{ background: 'var(--color-bg)' }}>
        <p>
          <strong>Editar composição — {item.label}</strong>
        </p>
        {item.missing_required_components.length > 0 && (
          <div className="feedback-error field-group">
            <p>
              Pendências: faltam componente(s) obrigatório(s) —{' '}
              {item.missing_required_components.join(', ')}.
            </p>
            <form onSubmit={handleSaveJustification} className="action-group">
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
        <ul className="list-plain">
          {item.components.map((component) => {
            const swap = swapResults[component.id]
            return (
              <li key={component.id} className="field-group">
                <div className="action-group">
                  {component.sku ?? 'sem SKU'} — {component.frozen_currency} {component.frozen_unit_price.toFixed(2)}
                  <button type="button" className="secondary" onClick={() => handleRemoveComponent(component.id)}>
                    remover componente
                  </button>
                </div>
                {swap && swap.price_changed && (
                  <p className="feedback-warning">
                    Preço atualizado de {swap.frozen_currency} {swap.previous_frozen_unit_price.toFixed(2)} para{' '}
                    {swap.frozen_currency} {swap.frozen_unit_price.toFixed(2)}.
                  </p>
                )}
                <ComponentPicker
                  families={families}
                  finishes={finishes}
                  dimensions={dimensions}
                  pickLabel="Trocar variação"
                  onPick={(variant) => handleSwap(component.id, variant)}
                />
              </li>
            )
          })}
        </ul>
        <div className="form-block" style={{ marginTop: 'var(--space-3)' }}>
          <h4 className="form-block__title">+ componente</h4>
          <ComponentPicker
            families={families}
            finishes={finishes}
            dimensions={dimensions}
            pickLabel="Adicionar componente"
            onPick={handleAddComponent}
          />
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
  finishes,
  dimensions,
  onChanged,
}: {
  item: QuoteItem
  quoteId: number
  families: ProductFamily[]
  finishes: Finish[]
  dimensions: Dimension[]
  onChanged: () => void
}) {
  const [quantity, setQuantity] = useState(String(item.quantity))
  const [discountMode, setDiscountMode] = useState<'none' | 'percent' | 'amount'>(
    item.discount_percent != null ? 'percent' : item.discount_amount != null ? 'amount' : 'none',
  )
  const [discountValue, setDiscountValue] = useState(
    item.discount_percent?.toString() ?? item.discount_amount?.toString() ?? '',
  )
  const [discountReason, setDiscountReason] = useState(item.discount_reason ?? '')
  const [editing, setEditing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function handleDiscountModeChange(mode: 'none' | 'percent' | 'amount') {
    setDiscountMode(mode)
    setDiscountValue('')
  }

  async function handleSave(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await updateItem(quoteId, item.id, {
        quantity: Number(quantity) || 1,
        discount_percent: discountMode === 'percent' ? Number(discountValue) || 0 : null,
        discount_amount: discountMode === 'amount' ? Number(discountValue) || 0 : null,
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

  const isComposite = item.components.length > 1

  return (
    <>
      <tr>
        <td>{item.id}</td>
        <td>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
            <span className={`badge ${isComposite ? 'badge-composite' : 'badge-neutral'}`}>
              {isComposite ? 'Composto' : 'Avulso'}
            </span>
            {item.label}
          </div>
        </td>
        <td>
          {isComposite ? (
            <ul className="component-list">
              {item.components.map((c, idx) => (
                <li key={c.id} className="component-list__item">
                  {idx === 0 && (
                    <span className="badge badge-composite badge--sm">base</span>
                  )}
                  <span>
                    {c.sku ?? 'sem SKU'} — {c.frozen_currency} {c.frozen_unit_price.toFixed(2)}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            item.components.map((c) => (
              <div key={c.id}>
                {c.sku ?? 'sem SKU'} — {c.frozen_currency} {c.frozen_unit_price.toFixed(2)}
              </div>
            ))
          )}
          {item.pricing_pendencias.length > 0 && (
            <p className="feedback-error">{item.pricing_pendencias.join('; ')}</p>
          )}
        </td>
        <td>
          <form onSubmit={handleSave} className="action-group">
            <input
              type="number"
              min="1"
              style={{ width: '4rem' }}
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
            />
            <select
              style={{ width: '6rem' }}
              value={discountMode}
              onChange={(e) => handleDiscountModeChange(e.target.value as 'none' | 'percent' | 'amount')}
            >
              <option value="none">sem desc.</option>
              <option value="percent">% desc.</option>
              <option value="amount">R$ desc.</option>
            </select>
            {discountMode !== 'none' && (
              <input
                type="number"
                min="0"
                step="0.01"
                placeholder={discountMode === 'percent' ? '0' : '0,00'}
                style={{ width: '6rem' }}
                value={discountValue}
                onChange={(e) => setDiscountValue(e.target.value)}
              />
            )}
            <input
              placeholder="Justificativa"
              style={{ width: '8rem' }}
              value={discountReason}
              onChange={(e) => setDiscountReason(e.target.value)}
            />
            <button type="submit">salvar</button>
          </form>
          <div className="action-group" style={{ marginTop: 'var(--space-2)' }}>
            <button type="button" className="secondary" onClick={() => setEditing((prev) => !prev)}>
              {editing ? 'fechar composição' : 'editar composição'}
            </button>
            <button type="button" className="danger" onClick={() => void handleRemoveItem()}>
              remover linha
            </button>
          </div>
          <ErrorMessage error={error} />
        </td>
        <td>{item.line_subtotal.toFixed(2)}</td>
      </tr>
      {editing && (
        <EditItemPanel
          item={item}
          quoteId={quoteId}
          families={families}
          finishes={finishes}
          dimensions={dimensions}
          onChanged={onChanged}
        />
      )}
    </>
  )
}

function QuoteSettingsForm({
  quote,
  onChanged,
}: {
  quote: Quote
  onChanged: () => void
}) {
  const [globalMarkup, setGlobalMarkup] = useState<number | null>(null)
  const [usesGlobal, setUsesGlobal] = useState(quote.markup_uses_global)
  const [markupPercent, setMarkupPercent] = useState(quote.markup_percent.toString())
  const [discountMode, setDiscountMode] = useState<'none' | 'percent' | 'amount'>(
    quote.quote_discount_percent != null ? 'percent' : quote.quote_discount_amount != null ? 'amount' : 'none',
  )
  const [discountValue, setDiscountValue] = useState(
    quote.quote_discount_percent?.toString() ?? quote.quote_discount_amount?.toString() ?? '',
  )
  const [discountReason, setDiscountReason] = useState(quote.quote_discount_reason ?? '')
  const [installmentCount, setInstallmentCount] = useState(
    quote.installment_count > 1 ? quote.installment_count.toString() : '',
  )
  const [installmentInterest, setInstallmentInterest] = useState(
    quote.installment_interest_percent > 0 ? quote.installment_interest_percent.toString() : '',
  )
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getSettings()
      .then((s) => setGlobalMarkup(s.global_markup_percent))
      .catch(() => null)
  }, [])

  function handleDiscountModeChange(mode: 'none' | 'percent' | 'amount') {
    setDiscountMode(mode)
    setDiscountValue('')
  }

  async function handleSave(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    const count = Number(installmentCount) || 1
    const interest = count > 1 ? Number(installmentInterest) || 0 : 0
    try {
      await updateQuoteSettings(quote.id, {
        markup_uses_global: usesGlobal,
        markup_percent: usesGlobal ? 0 : Number(markupPercent) || 0,
        quote_discount_percent: discountMode === 'percent' ? Number(discountValue) || 0 : null,
        quote_discount_amount: discountMode === 'amount' ? Number(discountValue) || 0 : null,
        quote_discount_reason: discountReason || null,
        installment_count: count,
        installment_interest_percent: interest,
      })
      onChanged()
    } catch (err) {
      setError(describeError(err))
    }
  }

  const count = Number(installmentCount) || 1

  return (
    <section>
      <h3>Configurações de preço</h3>
      <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
        {/* Markup */}
        <div className="form-field">
          <span className="form-field__label">% de venda</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={usesGlobal}
                onChange={(e) => setUsesGlobal(e.target.checked)}
              />
              <span>Global{globalMarkup !== null ? ` (${globalMarkup}%)` : ''}</span>
            </label>
            {!usesGlobal && (
              <input
                type="number"
                min="0"
                step="0.01"
                placeholder="0"
                style={{ width: '6rem' }}
                value={markupPercent}
                onChange={(e) => setMarkupPercent(e.target.value)}
              />
            )}
          </div>
        </div>

        {/* Desconto */}
        <div className="action-group">
          <div className="form-field">
            <span className="form-field__label">Desconto orçamento</span>
            <select
              value={discountMode}
              onChange={(e) => handleDiscountModeChange(e.target.value as 'none' | 'percent' | 'amount')}
            >
              <option value="none">Sem desconto</option>
              <option value="percent">%</option>
              <option value="amount">R$</option>
            </select>
          </div>
          {discountMode !== 'none' && (
            <input
              type="number"
              min="0"
              step="0.01"
              placeholder={discountMode === 'percent' ? '0 %' : '0,00'}
              style={{ width: '7rem' }}
              value={discountValue}
              onChange={(e) => setDiscountValue(e.target.value)}
            />
          )}
          <input
            placeholder="Justificativa desconto"
            style={{ width: '12rem' }}
            value={discountReason}
            onChange={(e) => setDiscountReason(e.target.value)}
          />
        </div>

        {/* Parcelamento */}
        <div className="action-group">
          <div className="form-field">
            <span className="form-field__label">Parcelamento</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)' }}>
              <input
                type="number"
                min="1"
                max="60"
                placeholder="1"
                style={{ width: '4rem' }}
                value={installmentCount}
                onChange={(e) => setInstallmentCount(e.target.value)}
              />
              <span style={{ color: 'var(--color-text-muted)' }}>×</span>
            </div>
          </div>
          {count > 1 && (
            <div className="form-field">
              <span className="form-field__label">Juros (%)</span>
              <input
                type="number"
                min="0"
                step="0.01"
                placeholder="0"
                style={{ width: '6rem' }}
                value={installmentInterest}
                onChange={(e) => setInstallmentInterest(e.target.value)}
              />
            </div>
          )}
        </div>

        <div>
          <button type="submit">Salvar configurações</button>
        </div>
      </form>
      <ErrorMessage error={error} />
    </section>
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
  const [finishes, setFinishes] = useState<Finish[]>([])
  const [dimensions, setDimensions] = useState<Dimension[]>([])
  const [totals, setTotals] = useState<QuoteTotals | null>(null)
  const [checklist, setChecklist] = useState<QuoteReviewChecklist | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function reload() {
    try {
      const [itemsData, familiesData, finishesData, dimensionsData, totalsData, checklistData] = await Promise.all([
        listItems(quote.id),
        listFamilies(),
        listFinishes(),
        listDimensions(),
        getTotals(quote.id),
        getReviewChecklist(quote.id),
      ])
      setItems(itemsData)
      setFamilies(familiesData)
      setFinishes(finishesData)
      setDimensions(dimensionsData)
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
      `Este orçamento será duplicado com os preços atuais de cada item. ` +
        `Os valores podem ser diferentes dos deste orçamento. Continuar?`,
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
      <div className="quote-header">
        <div className="quote-header__title">
          <span className="quote-header__number">{quote.quote_number}</span>
          <h2>
            {quote.customer.name} <StatusBadge status={quote.status} />
          </h2>
          {quote.source_quote_id !== null && <p>Duplicado do orçamento #{quote.source_quote_id}.</p>}
        </div>
        <div className="action-group">
          <button type="button" className="secondary" onClick={() => void handleDuplicate()}>
            Duplicar orçamento
          </button>
          {transitions.length > 0 && (
            <>
              <span style={{ color: 'var(--color-text-muted)' }}>Mudar status para:</span>
              {transitions.map((status) => (
                <button key={status} className="secondary" onClick={() => handleStatusChange(status)}>
                  {status}
                </button>
              ))}
            </>
          )}
        </div>
      </div>

      <div className="table-responsive">
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
              <ItemRow
                key={item.id}
                item={item}
                quoteId={quote.id}
                families={families}
                finishes={finishes}
                dimensions={dimensions}
                onChanged={handleItemChanged}
              />
            ))}
          </tbody>
        </table>
      </div>

      {quote.status === 'rascunho' && (
        <>
          <QuoteSettingsForm
            quote={quote}
            onChanged={() => { void reload(); onChanged() }}
          />
          <NewItemForm
            quoteId={quote.id}
            families={families}
            finishes={finishes}
            dimensions={dimensions}
            onAdded={() => void reload()}
          />
        </>
      )}

      {checklist && (
        <section>
          <h3>Checklist de revisão final (RN-18)</h3>
          <ul className="list-plain">
            {checklist.items.map((checkItem) => (
              <li key={checkItem.code}>
                <span className={`badge ${checkItem.ok ? 'badge-success' : 'badge-danger'}`}>
                  {checkItem.ok ? '✓ ok' : '✗ pendente'}
                </span>{' '}
                {checkItem.label}
                {!checkItem.ok && (
                  <p className="feedback-error">{checkItem.pendencias.join('; ')}</p>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {totals && (
        <section>
          <h3>Totais{totals.is_snapshot ? ' (congelado)' : ' (ao vivo)'}</h3>
          <div className="totals-card__grid">
            <div className="totals-card__item">
              <span className="totals-card__label">Subtotal</span>
              <span className="totals-card__value">
                {totals.currency} {totals.subtotal.toFixed(2)}
              </span>
            </div>
            {totals.item_discount_amount > 0 && (
              <div className="totals-card__item">
                <span className="totals-card__label">Desc. itens</span>
                <span className="totals-card__value">
                  − {totals.currency} {totals.item_discount_amount.toFixed(2)}
                </span>
              </div>
            )}
            {totals.quote_discount_amount > 0 && (
              <div className="totals-card__item">
                <span className="totals-card__label">Desc. orçamento</span>
                <span className="totals-card__value">
                  − {totals.currency} {totals.quote_discount_amount.toFixed(2)}
                </span>
              </div>
            )}
            {totals.item_discount_amount === 0 && totals.quote_discount_amount === 0 && totals.discount_amount > 0 && (
              <div className="totals-card__item">
                <span className="totals-card__label">Desconto</span>
                <span className="totals-card__value">
                  − {totals.currency} {totals.discount_amount.toFixed(2)} ({totals.discount_percent.toFixed(2)}%)
                </span>
              </div>
            )}
            {totals.installment_count > 1 && totals.installment_interest_amount > 0 ? (
              <>
                <div className="totals-card__item">
                  <span className="totals-card__label">Total à vista</span>
                  <span className="totals-card__value">{totals.currency} {totals.total.toFixed(2)}</span>
                </div>
                <div className="totals-card__item">
                  <span className="totals-card__label">Juros ({totals.installment_interest_percent}%)</span>
                  <span className="totals-card__value">+ {totals.currency} {totals.installment_interest_amount.toFixed(2)}</span>
                </div>
                <div className="totals-card__item totals-card__item--total">
                  <span className="totals-card__label">Total c/ juros</span>
                  <span className="totals-card__value">{totals.currency} {totals.installment_total.toFixed(2)}</span>
                </div>
                <div className="totals-card__item">
                  <span className="totals-card__label">{totals.installment_count}× de</span>
                  <span className="totals-card__value">{totals.currency} {totals.installment_value.toFixed(2)}</span>
                </div>
              </>
            ) : totals.installment_count > 1 ? (
              <>
                <div className="totals-card__item totals-card__item--total">
                  <span className="totals-card__label">Total</span>
                  <span className="totals-card__value">{totals.currency} {totals.total.toFixed(2)}</span>
                </div>
                <div className="totals-card__item">
                  <span className="totals-card__label">{totals.installment_count}× de</span>
                  <span className="totals-card__value">{totals.currency} {totals.installment_value.toFixed(2)}</span>
                </div>
              </>
            ) : (
              <div className="totals-card__item totals-card__item--total">
                <span className="totals-card__label">Total</span>
                <span className="totals-card__value">
                  {totals.currency} {totals.total.toFixed(2)}
                </span>
              </div>
            )}
          </div>
          {totals.warnings.map((warning) => (
            <p key={warning.code} className="feedback-warning">
              {warning.message}
            </p>
          ))}
          <div className="action-group">
            <button onClick={handleFreeze} disabled={!checklist?.ready}>
              Congelar total
            </button>
            <button className="secondary" onClick={() => void handleExportPdf()} disabled={!totals.is_snapshot}>
              Exportar PDF
            </button>
          </div>
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
  const [search, setSearch] = useState('')
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

  function handleCustomerCreated(customer: Customer) {
    setCustomers((prev) => [...prev, customer].sort((a, b) => a.name.localeCompare(b.name)))
  }

  function handleDuplicated(quote: Quote) {
    setQuotes((prev) => [...prev, quote])
    setSelectedQuoteId(quote.id)
  }

  const selectedQuote = quotes.find((q) => q.id === selectedQuoteId) ?? null

  async function handleSelectionChanged() {
    await reload()
  }

  async function handleDelete(quote: Quote) {
    if (!window.confirm(`Excluir o orçamento ${quote.quote_number}? Esta ação não pode ser desfeita.`)) {
      return
    }
    setError(null)
    try {
      await deleteQuote(quote.id)
      setQuotes((prev) => prev.filter((q) => q.id !== quote.id))
      setSelectedQuoteId((current) => (current === quote.id ? null : current))
    } catch (err) {
      setError(describeError(err))
    }
  }

  const normalizedSearch = search.trim().toLowerCase()
  const matchesSearch = (quote: Quote) =>
    !normalizedSearch ||
    quote.quote_number.toLowerCase().includes(normalizedSearch) ||
    quote.customer.name.toLowerCase().includes(normalizedSearch)

  const inProgressQuotes = quotes.filter(
    (q) => (q.status === 'rascunho' || q.status === 'enviado') && matchesSearch(q),
  )
  const finishedQuotes = quotes.filter(
    (q) =>
      (q.status === 'aprovado' || q.status === 'rejeitado' || q.status === 'expirado') &&
      matchesSearch(q),
  )

  function renderQuoteItem(quote: Quote) {
    return (
      <li
        key={quote.id}
        className={`list-item-card list-item-card--column ${quote.id === selectedQuoteId ? 'is-selected' : ''}`}
      >
        <div className="list-item-card__row">
          <span>
            <strong>{quote.quote_number}</strong> — {quote.customer.name}
          </span>
          <StatusBadge status={quote.status} />
        </div>
        <div className="action-group">
          <button type="button" className="secondary" onClick={() => setSelectedQuoteId(quote.id)}>
            {quote.id === selectedQuoteId ? 'Selecionado' : 'Abrir'}
          </button>
          <button type="button" className="danger" onClick={() => void handleDelete(quote)}>
            excluir
          </button>
        </div>
      </li>
    )
  }

  return (
    <div>
      <h1>Orçamentos — montagem</h1>
      <ErrorMessage error={error} />

      <div className="quotes-layout">
        <aside className="quotes-sidebar">
          <input
            type="search"
            className="quotes-search"
            placeholder="Buscar por número ou cliente..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />

          <section>
            <h2>Em andamento</h2>
            {inProgressQuotes.length === 0 && (
              <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
                Nenhum orçamento em andamento.
              </p>
            )}
            <ul className="list-plain">{inProgressQuotes.map(renderQuoteItem)}</ul>
          </section>

          <details>
            <summary style={{ cursor: 'pointer', fontWeight: 600 }}>
              Finalizados ({finishedQuotes.length})
            </summary>
            <ul className="list-plain" style={{ marginTop: 'var(--space-2)' }}>
              {finishedQuotes.length === 0 ? (
                <li style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
                  Nenhum orçamento finalizado.
                </li>
              ) : (
                finishedQuotes.map(renderQuoteItem)
              )}
            </ul>
          </details>

          <details>
            <summary>Novo cliente</summary>
            <NewCustomerForm onCreated={handleCustomerCreated} />
          </details>

          <details>
            <summary>Novo orçamento</summary>
            <NewQuoteForm customers={customers} onCreated={handleCreated} />
          </details>
        </aside>

        <main className="quotes-main">
          {selectedQuote ? (
            <QuoteDetail
              quote={selectedQuote}
              onChanged={() => void handleSelectionChanged()}
              onDuplicated={handleDuplicated}
            />
          ) : (
            <section className="quotes-empty-state">
              <p>Selecione um orçamento na lista ao lado ou crie um novo para começar.</p>
            </section>
          )}
        </main>
      </div>
    </div>
  )
}
