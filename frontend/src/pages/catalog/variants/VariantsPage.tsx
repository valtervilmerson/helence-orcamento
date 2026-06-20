import { useEffect, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import {
  type ComponentVariant,
  type Dimension,
  type Finish,
  type Product,
  type ProductComponentType,
  createComponent,
  deleteComponent,
  searchComponents,
  updateComponent,
} from '../../../api/catalog'
import { ErrorMessage } from '../shared'
import { describeError, type CatalogContextValue } from '../catalogContext'

const PAGE_SIZE = 25

// ---------------------------------------------------------------------------
// Formulário de edição inline de uma variação (linha expandida na tabela)
// ---------------------------------------------------------------------------

function EditVariantForm({
  item,
  componentTypes,
  products,
  dimensions,
  finishes,
  onSaved,
  onCancel,
}: {
  item: ComponentVariant
  componentTypes: ProductComponentType[]
  products: Product[]
  dimensions: Dimension[]
  finishes: Finish[]
  onSaved: () => void
  onCancel: () => void
}) {
  const currentComponentType = componentTypes.find((ct) => ct.name === item.component)
  const currentProduct = products.find((p) => p.name === item.product)
  const currentDimension = dimensions.find((d) => d.raw_label === item.dimension?.raw_label)
  const currentFinish = finishes.find((f) => f.name === item.finish)

  const [componentTypeId, setComponentTypeId] = useState(String(currentComponentType?.id ?? ''))
  const [productId, setProductId] = useState(String(currentProduct?.id ?? ''))
  const [dimensionId, setDimensionId] = useState(String(currentDimension?.id ?? ''))
  const [finishId, setFinishId] = useState(String(currentFinish?.id ?? ''))
  const [descriptor, setDescriptor] = useState(item.descriptor ?? '')
  const [description, setDescription] = useState(item.description ?? '')
  const [skuCode, setSkuCode] = useState(item.sku ?? '')
  const [priceAmount, setPriceAmount] = useState(item.price?.amount.toFixed(2) ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSave(event: React.FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await updateComponent(item.component_variant_id, {
        component_id: componentTypeId ? Number(componentTypeId) : undefined,
        product_id: productId ? Number(productId) : null,
        dimension_id: dimensionId ? Number(dimensionId) : null,
        finish_id: finishId ? Number(finishId) : null,
        descriptor: descriptor || null,
        description: description || null,
        sku: skuCode ? { code: skuCode } : null,
        price: priceAmount ? { amount: Number(priceAmount), currency: 'BRL' } : null,
      })
      onSaved()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSave}>
      <div className="form-row">
        <div className="form-field">
          <span className="form-field__label">Tipo de componente *</span>
          <select value={componentTypeId} onChange={(e) => setComponentTypeId(e.target.value)} required>
            <option value="">(selecione)</option>
            {componentTypes.map((ct) => (
              <option key={ct.id} value={ct.id}>
                {ct.name}
              </option>
            ))}
          </select>
        </div>
        <div className="form-field">
          <span className="form-field__label">Produto-base</span>
          <select value={productId} onChange={(e) => setProductId(e.target.value)}>
            <option value="">(nenhum)</option>
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        <div className="form-field">
          <span className="form-field__label">Dimensão</span>
          <select value={dimensionId} onChange={(e) => setDimensionId(e.target.value)}>
            <option value="">(nenhuma)</option>
            {dimensions.map((d) => (
              <option key={d.id} value={d.id}>
                {d.raw_label ?? `#${d.id}`}
              </option>
            ))}
          </select>
        </div>
        <div className="form-field">
          <span className="form-field__label">Acabamento</span>
          <select value={finishId} onChange={(e) => setFinishId(e.target.value)}>
            <option value="">(nenhum)</option>
            {finishes.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="form-row" style={{ marginTop: 'var(--space-3)' }}>
        <div className="form-field">
          <span className="form-field__label">Descritor</span>
          <input
            value={descriptor}
            onChange={(e) => setDescriptor(e.target.value)}
            placeholder="ex.: Inteiro Simples"
          />
        </div>
        <div className="form-field" style={{ flex: 2 }}>
          <span className="form-field__label">Descrição</span>
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Descrição completa do item"
            style={{ width: '100%' }}
          />
        </div>
        <div className="form-field">
          <span className="form-field__label">SKU</span>
          <input
            value={skuCode}
            onChange={(e) => setSkuCode(e.target.value)}
            placeholder="Código SKU"
          />
        </div>
        <div className="form-field">
          <span className="form-field__label">Preço (R$)</span>
          <input
            type="number"
            min="0"
            step="0.01"
            value={priceAmount}
            onChange={(e) => setPriceAmount(e.target.value)}
            placeholder="0,00"
            style={{ width: '8rem' }}
          />
        </div>
      </div>
      <div className="action-group" style={{ marginTop: 'var(--space-3)' }}>
        <button type="submit" disabled={saving || !componentTypeId}>
          {saving ? 'Salvando…' : 'Salvar'}
        </button>
        <button type="button" className="secondary" onClick={onCancel}>
          Cancelar
        </button>
      </div>
      <ErrorMessage error={error} />
    </form>
  )
}

export function VariantsPage() {
  const { families, products, dimensions, finishes, componentTypes, reload } =
    useOutletContext<CatalogContextValue>()

  const [q, setQ] = useState('')
  const [familyFilter, setFamilyFilter] = useState('')
  const [componentFilter, setComponentFilter] = useState('')
  const [finishFilter, setFinishFilter] = useState('')
  const [page, setPage] = useState(1)
  const [showForm, setShowForm] = useState(false)

  const [results, setResults] = useState<ComponentVariant[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const [productId, setProductId] = useState('')
  const [componentId, setComponentId] = useState('')
  const [dimensionId, setDimensionId] = useState('')
  const [finishId, setFinishId] = useState('')
  const [descriptor, setDescriptor] = useState('')
  const [description, setDescription] = useState('')
  const [skuCode, setSkuCode] = useState('')
  const [priceAmount, setPriceAmount] = useState('')

  async function runSearch(targetPage: number) {
    setLoading(true)
    setError(null)
    try {
      const result = await searchComponents({
        q: q || undefined,
        family: familyFilter || undefined,
        component: componentFilter || undefined,
        finish: finishFilter || undefined,
        page: targetPage,
        page_size: PAGE_SIZE,
      })
      setResults(result.items)
      setTotal(result.total)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  // Busca sempre que algum filtro ou a página mudam. Mudar um filtro reseta
  // a página para 1 diretamente nos handlers (não aqui no efeito).
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- busca de dados ao filtrar/paginar
    void runSearch(page)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, familyFilter, componentFilter, finishFilter, page])

  function updateFilter(setter: (value: string) => void, value: string) {
    setter(value)
    setPage(1)
  }

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await createComponent({
        product_id: productId ? Number(productId) : null,
        component_id: Number(componentId),
        dimension_id: dimensionId ? Number(dimensionId) : null,
        finish_id: finishId ? Number(finishId) : null,
        descriptor: descriptor || null,
        description: description || null,
        sku: skuCode ? { code: skuCode } : null,
        price: priceAmount ? { amount: Number(priceAmount), currency: 'BRL' } : null,
      })
      setDescriptor('')
      setDescription('')
      setSkuCode('')
      setPriceAmount('')
      await reload()
      await runSearch(page)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete(id: number) {
    setError(null)
    setDeletingId(id)
    try {
      await deleteComponent(id)
      await runSearch(page)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setDeletingId(null)
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <section>
      <div className="catalog-section-header">
        <div>
          <h2>Variações vendáveis</h2>
          <p className="catalog-section-header__hint">
            Combinações finais de produto + componente + dimensão + acabamento, com SKU e
            preço. Use os filtros para localizar itens em catálogos grandes.
          </p>
        </div>
        <div className="catalog-section-header__actions">
          <button type="button" className={showForm ? 'secondary' : ''} onClick={() => setShowForm((v) => !v)}>
            {showForm ? 'Cancelar' : '+ Nova variação'}
          </button>
        </div>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="catalog-add-form">
          <select value={componentId} onChange={(e) => setComponentId(e.target.value)} required>
            <option value="">(tipo de componente)</option>
            {componentTypes.map((type) => (
              <option key={type.id} value={type.id}>
                {type.name}
              </option>
            ))}
          </select>
          <select value={productId} onChange={(e) => setProductId(e.target.value)}>
            <option value="">(produto-base)</option>
            {products.map((product) => (
              <option key={product.id} value={product.id}>
                {product.name}
              </option>
            ))}
          </select>
          <select value={dimensionId} onChange={(e) => setDimensionId(e.target.value)}>
            <option value="">(dimensão)</option>
            {dimensions.map((dimension) => (
              <option key={dimension.id} value={dimension.id}>
                {dimension.raw_label ?? `#${dimension.id}`}
              </option>
            ))}
          </select>
          <select value={finishId} onChange={(e) => setFinishId(e.target.value)}>
            <option value="">(acabamento)</option>
            {finishes.map((finish) => (
              <option key={finish.id} value={finish.id}>
                {finish.name}
              </option>
            ))}
          </select>
          <input placeholder="Descritor (ex.: Inteiro Simples)" value={descriptor} onChange={(e) => setDescriptor(e.target.value)} />
          <input placeholder="Descrição" value={description} onChange={(e) => setDescription(e.target.value)} />
          <input placeholder="Código SKU" value={skuCode} onChange={(e) => setSkuCode(e.target.value)} />
          <input placeholder="Preço (R$)" value={priceAmount} onChange={(e) => setPriceAmount(e.target.value)} />
          <button type="submit" disabled={submitting}>
            {submitting ? 'Adicionando…' : 'Adicionar variação'}
          </button>
        </form>
      )}

      <div className="action-group" style={{ marginBottom: 'var(--space-3)' }}>
        <input
          placeholder="Buscar por produto, SKU, descrição..."
          value={q}
          onChange={(e) => updateFilter(setQ, e.target.value)}
          style={{ flex: '2 1 220px' }}
        />
        <select value={familyFilter} onChange={(e) => updateFilter(setFamilyFilter, e.target.value)}>
          <option value="">(todas as famílias)</option>
          {families.map((family) => (
            <option key={family.id} value={family.name}>
              {family.name}
            </option>
          ))}
        </select>
        <select value={componentFilter} onChange={(e) => updateFilter(setComponentFilter, e.target.value)}>
          <option value="">(todos os componentes)</option>
          {componentTypes.map((type) => (
            <option key={type.id} value={type.name}>
              {type.name}
            </option>
          ))}
        </select>
        <select value={finishFilter} onChange={(e) => updateFilter(setFinishFilter, e.target.value)}>
          <option value="">(todos os acabamentos)</option>
          {finishes.map((finish) => (
            <option key={finish.id} value={finish.name}>
              {finish.name}
            </option>
          ))}
        </select>
      </div>

      <p>{loading ? 'Buscando…' : `${total} variação(ões) encontrada(s).`}</p>

      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Família</th>
            <th>Produto</th>
            <th>Componente</th>
            <th>Descritor</th>
            <th>Dimensão</th>
            <th>Acabamento</th>
            <th>SKU</th>
            <th>Preço</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {results.map((item) => (
            <>
              <tr key={item.component_variant_id} className={editingId === item.component_variant_id ? 'is-selected' : ''}>
                <td>{item.component_variant_id}</td>
                <td>{item.family ?? '—'}</td>
                <td>{item.product ?? '—'}</td>
                <td>{item.component}</td>
                <td>{item.descriptor ?? '—'}</td>
                <td>{item.dimension?.raw_label ?? '—'}</td>
                <td>{item.finish ?? '—'}</td>
                <td>{item.sku ?? '—'}</td>
                <td>
                  {item.price ? `${item.price.currency} ${item.price.amount.toFixed(2)}` : '—'}
                </td>
                <td>
                  <div className="action-group">
                    <button
                      className="secondary"
                      onClick={() =>
                        setEditingId(editingId === item.component_variant_id ? null : item.component_variant_id)
                      }
                    >
                      {editingId === item.component_variant_id ? 'cancelar' : 'editar'}
                    </button>
                    <button
                      className="danger"
                      disabled={deletingId === item.component_variant_id}
                      onClick={() => {
                        if (editingId === item.component_variant_id) setEditingId(null)
                        void handleDelete(item.component_variant_id)
                      }}
                    >
                      {deletingId === item.component_variant_id ? 'excluindo…' : 'excluir'}
                    </button>
                  </div>
                </td>
              </tr>
              {editingId === item.component_variant_id && (
                <tr key={`edit-${item.component_variant_id}`}>
                  <td colSpan={10} style={{ background: 'var(--color-bg)', padding: 'var(--space-4)' }}>
                    <p style={{ margin: '0 0 var(--space-3)', fontWeight: 600 }}>
                      Editar variação #{item.component_variant_id} — {item.component}{item.descriptor ? ` · ${item.descriptor}` : ''}
                    </p>
                    <EditVariantForm
                      item={item}
                      componentTypes={componentTypes}
                      products={products}
                      dimensions={dimensions}
                      finishes={finishes}
                      onSaved={() => {
                        setEditingId(null)
                        void runSearch(page)
                      }}
                      onCancel={() => setEditingId(null)}
                    />
                  </td>
                </tr>
              )}
            </>
          ))}
          {!loading && results.length === 0 && (
            <tr>
              <td colSpan={10}>Nenhuma variação encontrada para esses filtros.</td>
            </tr>
          )}
        </tbody>
      </table>

      {totalPages > 1 && (
        <div className="action-group" style={{ marginTop: 'var(--space-3)' }}>
          <button className="secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            ← Anterior
          </button>
          <span>
            Página {page} de {totalPages}
          </span>
          <button className="secondary" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            Próxima →
          </button>
        </div>
      )}

      <ErrorMessage error={error} />
    </section>
  )
}
