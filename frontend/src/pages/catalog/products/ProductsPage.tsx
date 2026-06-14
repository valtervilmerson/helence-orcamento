import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { createProduct, deleteProduct } from '../../../api/catalog'
import { ErrorMessage, Pagination } from '../shared'
import { describeError, type CatalogContextValue } from '../catalogContext'

const PAGE_SIZE = 10

export function ProductsPage() {
  const { products, families, dimensions, reload } = useOutletContext<CatalogContextValue>()
  const [search, setSearch] = useState('')
  const [familyFilter, setFamilyFilter] = useState('')
  const [page, setPage] = useState(1)
  const [showForm, setShowForm] = useState(false)

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
          <li key={product.id} className="list-item-card">
            <span>
              #{product.id} — {product.name} ({familyName(product.family_id)})
            </span>
            <button className="danger" onClick={() => void handleDelete(product.id)}>
              excluir
            </button>
          </li>
        ))}
      </ul>

      <Pagination page={page} totalPages={totalPages} onChange={setPage} />
      <ErrorMessage error={error} />
    </section>
  )
}
