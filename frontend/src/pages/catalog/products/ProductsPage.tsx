import { useEffect, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import {
  addCompositionItem,
  createProduct,
  deleteProduct,
  listCompositionItems,
  removeCompositionItem,
  searchComponents,
  type ComponentVariant,
  type ProductCompositionItem,
} from '../../../api/catalog'
import { ErrorMessage, Pagination } from '../shared'
import { describeError, type CatalogContextValue } from '../catalogContext'

const PAGE_SIZE = 10

function describeVariant(variant: ComponentVariant): string {
  const price = variant.price ? `${variant.price.currency} ${variant.price.amount.toFixed(2)}` : 'sem preço'
  return `${variant.component} — ${variant.descriptor ?? ''} — ${variant.finish ?? '—'} — ${variant.sku ?? 'sem SKU'} — ${price}`
}

export function ProductsPage() {
  const { products, families, dimensions, reload } = useOutletContext<CatalogContextValue>()
  const [search, setSearch] = useState('')
  const [familyFilter, setFamilyFilter] = useState('')
  const [page, setPage] = useState(1)
  const [showForm, setShowForm] = useState(false)
  const [compositionProductId, setCompositionProductId] = useState<number | null>(null)

  const [name, setName] = useState('')
  const [familyId, setFamilyId] = useState('')
  const [dimensionId, setDimensionId] = useState('')
  const [error, setError] = useState<string | null>(null)

  function updateSearch(value: string) {
    setSearch(value)
    setPage(1)
  }

  function updateFamilyFilter(value: string) {
    setFamilyFilter(value)
    setPage(1)
  }

  function familyName(id: number) {
    return families.find((f) => f.id === id)?.name ?? `#${id}`
  }

  const term = search.trim().toLowerCase()
  const filtered = products.filter((product) => {
    if (familyFilter && String(product.family_id) !== familyFilter) return false
    if (term && !product.name.toLowerCase().includes(term)) return false
    return true
  })

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await createProduct({
        family_id: Number(familyId),
        name,
        dimension_id: dimensionId ? Number(dimensionId) : null,
      })
      setName('')
      await reload()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function handleDelete(id: number) {
    setError(null)
    try {
      await deleteProduct(id)
      await reload()
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <section>
      <div className="catalog-section-header">
        <div>
          <h2>Produtos-base</h2>
          <p className="catalog-section-header__hint">
            Produtos dentro de uma família, associados a uma dimensão padrão.
          </p>
        </div>
        <div className="catalog-section-header__actions">
          {products.length > 0 && (
            <>
              <select value={familyFilter} onChange={(e) => updateFamilyFilter(e.target.value)}>
                <option value="">(todas as famílias)</option>
                {families.map((family) => (
                  <option key={family.id} value={family.id}>
                    {family.name}
                  </option>
                ))}
              </select>
              <input
                className="catalog-search"
                placeholder="Buscar produto..."
                value={search}
                onChange={(e) => updateSearch(e.target.value)}
              />
            </>
          )}
          <button type="button" className={showForm ? 'secondary' : ''} onClick={() => setShowForm((v) => !v)}>
            {showForm ? 'Cancelar' : '+ Novo produto'}
          </button>
        </div>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="catalog-add-form">
          <select value={familyId} onChange={(e) => setFamilyId(e.target.value)} required>
            <option value="">(família)</option>
            {families.map((family) => (
              <option key={family.id} value={family.id}>
                {family.name}
              </option>
            ))}
          </select>
          <input placeholder="Nome (ex.: Reunião 1200x900)" value={name} onChange={(e) => setName(e.target.value)} required />
          <select value={dimensionId} onChange={(e) => setDimensionId(e.target.value)}>
            <option value="">(dimensão)</option>
            {dimensions.map((dimension) => (
              <option key={dimension.id} value={dimension.id}>
                {dimension.raw_label ?? `#${dimension.id}`}
              </option>
            ))}
          </select>
          <button type="submit">Adicionar produto</button>
        </form>
      )}

      {products.length === 0 && <p>Nenhum produto-base cadastrado ainda.</p>}
      {products.length > 0 && filtered.length === 0 && <p>Nenhum produto corresponde aos filtros.</p>}

      <ul className="list-plain">
        {pageItems.map((product) => (
          <li key={product.id} className="list-item-card list-item-card--column">
            <div className="list-item-card__row">
              <span>
                #{product.id} — {product.name} ({familyName(product.family_id)})
              </span>
              <div className="action-group">
                <button
                  type="button"
                  className="secondary"
                  onClick={() =>
                    setCompositionProductId((current) => (current === product.id ? null : product.id))
                  }
                >
                  {compositionProductId === product.id ? 'Fechar composição' : 'Gerenciar composição'}
                </button>
                <button className="danger" onClick={() => void handleDelete(product.id)}>
                  excluir
                </button>
              </div>
            </div>
            {compositionProductId === product.id && (
              <CompositionPanel productId={product.id} familyName={familyName(product.family_id)} />
            )}
          </li>
        ))}
      </ul>

      <Pagination page={page} totalPages={totalPages} onChange={setPage} />
      <ErrorMessage error={error} />
    </section>
  )
}

// ---------------------------------------------------------------------------
// Composição de um produto
// ---------------------------------------------------------------------------

function CompositionPanel({ productId, familyName }: { productId: number; familyName: string }) {
  const [items, setItems] = useState<ProductCompositionItem[]>([])
  const [results, setResults] = useState<ComponentVariant[]>([])
  const [variantId, setVariantId] = useState('')
  const [quantity, setQuantity] = useState('1')
  const [error, setError] = useState<string | null>(null)

  async function reload() {
    try {
      const compositionItems = await listCompositionItems(productId)
      setItems(compositionItems)
      setError(null)
    } catch (err) {
      setError(describeError(err))
    }
  }

  useEffect(() => {
    async function load() {
      try {
        setItems(await listCompositionItems(productId))
        setError(null)
      } catch (err) {
        setError(describeError(err))
      }
    }
    void load()
    async function runSearch() {
      try {
        const result = await searchComponents({ family: familyName })
        setResults(result.items)
      } catch (err) {
        setError(describeError(err))
      }
    }
    void runSearch()
  }, [productId, familyName])

  async function handleAdd() {
    if (!variantId) return
    setError(null)
    try {
      await addCompositionItem(productId, {
        component_variant_id: Number(variantId),
        quantity: Number(quantity) || 1,
      })
      setVariantId('')
      setQuantity('1')
      await reload()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function handleRemove(componentVariantId: number) {
    setError(null)
    try {
      await removeCompositionItem(productId, componentVariantId)
      await reload()
    } catch (err) {
      setError(describeError(err))
    }
  }

  const usedIds = new Set(items.map((item) => item.variant.component_variant_id))
  const availableResults = results.filter((variant) => !usedIds.has(variant.component_variant_id))

  return (
    <div className="catalog-composition-panel">
      {items.length === 0 && <p>Este produto ainda não tem itens de composição cadastrados.</p>}
      {items.length > 0 && (
        <ul className="list-plain">
          {items.map((item) => (
            <li key={item.id} className="list-item-card">
              <span>
                {item.quantity}x {describeVariant(item.variant)}
              </span>
              <button
                type="button"
                className="danger"
                onClick={() => void handleRemove(item.variant.component_variant_id)}
              >
                remover
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="action-group">
        <select value={variantId} onChange={(e) => setVariantId(e.target.value)} style={{ flex: 1, minWidth: '20rem' }}>
          <option value="">(selecione uma variação da família "{familyName}")</option>
          {availableResults.map((variant) => (
            <option key={variant.component_variant_id} value={variant.component_variant_id}>
              {describeVariant(variant)}
            </option>
          ))}
        </select>
        <input
          type="number"
          min="1"
          placeholder="Qtd."
          style={{ width: '5rem' }}
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
        />
        <button type="button" className="secondary" onClick={() => void handleAdd()} disabled={!variantId}>
          + adicionar à composição
        </button>
      </div>
      <ErrorMessage error={error} />
    </div>
  )
}
