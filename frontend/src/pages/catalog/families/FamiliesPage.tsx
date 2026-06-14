import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { createFamily, deleteFamily } from '../../../api/catalog'
import { ErrorMessage, Pagination } from '../shared'
import { describeError, type CatalogContextValue } from '../catalogContext'

const PAGE_SIZE = 10

export function FamiliesPage() {
  const { families, reload } = useOutletContext<CatalogContextValue>()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [showForm, setShowForm] = useState(false)

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState<string | null>(null)

  function updateSearch(value: string) {
    setSearch(value)
    setPage(1)
  }

  const term = search.trim().toLowerCase()
  const filtered = term
    ? families.filter(
        (f) => f.name.toLowerCase().includes(term) || (f.description ?? '').toLowerCase().includes(term),
      )
    : families

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await createFamily({ name, description: description || null })
      setName('')
      setDescription('')
      await reload()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function handleDelete(id: number) {
    setError(null)
    try {
      await deleteFamily(id)
      await reload()
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <section>
      <div className="catalog-section-header">
        <div>
          <h2>Famílias de produto</h2>
          <p className="catalog-section-header__hint">
            Agrupamentos de alto nível usados para organizar produtos-base e variações.
          </p>
        </div>
        <div className="catalog-section-header__actions">
          {families.length > 0 && (
            <input
              className="catalog-search"
              placeholder="Buscar família..."
              value={search}
              onChange={(e) => updateSearch(e.target.value)}
            />
          )}
          <button type="button" className={showForm ? 'secondary' : ''} onClick={() => setShowForm((v) => !v)}>
            {showForm ? 'Cancelar' : '+ Nova família'}
          </button>
        </div>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="catalog-add-form">
          <input placeholder="Nome" value={name} onChange={(e) => setName(e.target.value)} required />
          <input
            placeholder="Descrição (opcional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <button type="submit">Adicionar família</button>
        </form>
      )}

      {families.length === 0 && <p>Nenhuma família cadastrada ainda.</p>}
      {families.length > 0 && filtered.length === 0 && <p>Nenhuma família corresponde à busca.</p>}

      <ul className="list-plain">
        {pageItems.map((family) => (
          <li key={family.id} className="list-item-card">
            <span>
              #{family.id} — {family.name}
              {family.description ? ` (${family.description})` : ''}
            </span>
            <button className="danger" onClick={() => void handleDelete(family.id)}>
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
