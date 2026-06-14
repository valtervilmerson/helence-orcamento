import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { createComponentType, deleteComponentType } from '../../../api/catalog'
import { ErrorMessage, Pagination } from '../shared'
import { describeError, type CatalogContextValue } from '../catalogContext'

const PAGE_SIZE = 10

export function ComponentTypesPage() {
  const { componentTypes, reload } = useOutletContext<CatalogContextValue>()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [showForm, setShowForm] = useState(false)

  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)

  function updateSearch(value: string) {
    setSearch(value)
    setPage(1)
  }

  const term = search.trim().toLowerCase()
  const filtered = term
    ? componentTypes.filter((type) => type.name.toLowerCase().includes(term))
    : componentTypes

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await createComponentType({ name })
      setName('')
      await reload()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function handleDelete(id: number) {
    setError(null)
    try {
      await deleteComponentType(id)
      await reload()
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <section>
      <div className="catalog-section-header">
        <div>
          <h2>Tipos de componente</h2>
          <p className="catalog-section-header__hint">
            Peças que compõem um produto (ex.: Tampo, Estrutura, Painel Ripado).
          </p>
        </div>
        <div className="catalog-section-header__actions">
          {componentTypes.length > 0 && (
            <input
              className="catalog-search"
              placeholder="Buscar tipo de componente..."
              value={search}
              onChange={(e) => updateSearch(e.target.value)}
            />
          )}
          <button type="button" className={showForm ? 'secondary' : ''} onClick={() => setShowForm((v) => !v)}>
            {showForm ? 'Cancelar' : '+ Novo tipo de componente'}
          </button>
        </div>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="catalog-add-form">
          <input placeholder="Nome (ex.: Tampo)" value={name} onChange={(e) => setName(e.target.value)} required />
          <button type="submit">Adicionar tipo de componente</button>
        </form>
      )}

      {componentTypes.length === 0 && <p>Nenhum tipo de componente cadastrado ainda.</p>}
      {componentTypes.length > 0 && filtered.length === 0 && (
        <p>Nenhum tipo de componente corresponde à busca.</p>
      )}

      <ul className="list-plain">
        {pageItems.map((type) => (
          <li key={type.id} className="list-item-card">
            <span>
              #{type.id} — {type.name}
            </span>
            <button className="danger" onClick={() => void handleDelete(type.id)}>
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
