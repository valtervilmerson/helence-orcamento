import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { createFinish, deleteFinish, type Finish } from '../../../api/catalog'
import { ErrorMessage, Pagination } from '../shared'
import { describeError, type CatalogContextValue } from '../catalogContext'

const PAGE_SIZE = 10

export function FinishesPage() {
  const { finishes, reload } = useOutletContext<CatalogContextValue>()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [showForm, setShowForm] = useState(false)

  const [name, setName] = useState('')
  const [group, setGroup] = useState('')
  const [error, setError] = useState<string | null>(null)

  function updateSearch(value: string) {
    setSearch(value)
    setPage(1)
  }

  const term = search.trim().toLowerCase()
  const filtered = term
    ? finishes.filter(
        (f) => f.name.toLowerCase().includes(term) || (f.finish_group ?? '').toLowerCase().includes(term),
      )
    : finishes

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await createFinish({
        name,
        finish_group: (group || null) as Finish['finish_group'],
      })
      setName('')
      setGroup('')
      await reload()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function handleDelete(id: number) {
    setError(null)
    try {
      await deleteFinish(id)
      await reload()
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <section>
      <div className="catalog-section-header">
        <div>
          <h2>Acabamentos</h2>
          <p className="catalog-section-header__hint">
            Cores e materiais de acabamento. O nome precisa coincidir exatamente com o usado
            nas planilhas/importações para que os itens sejam reconhecidos automaticamente.
          </p>
        </div>
        <div className="catalog-section-header__actions">
          {finishes.length > 0 && (
            <input
              className="catalog-search"
              placeholder="Buscar acabamento..."
              value={search}
              onChange={(e) => updateSearch(e.target.value)}
            />
          )}
          <button type="button" className={showForm ? 'secondary' : ''} onClick={() => setShowForm((v) => !v)}>
            {showForm ? 'Cancelar' : '+ Novo acabamento'}
          </button>
        </div>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="catalog-add-form">
          <input placeholder="Nome" value={name} onChange={(e) => setName(e.target.value)} required />
          <select value={group} onChange={(e) => setGroup(e.target.value)}>
            <option value="">(grupo)</option>
            <option value="madeirado">madeirado</option>
            <option value="metalico">metálico</option>
            <option value="pe_estrutura">pé/estrutura</option>
            <option value="outro">outro</option>
          </select>
          <button type="submit">Adicionar acabamento</button>
        </form>
      )}

      {finishes.length === 0 && <p>Nenhum acabamento cadastrado ainda.</p>}
      {finishes.length > 0 && filtered.length === 0 && <p>Nenhum acabamento corresponde à busca.</p>}

      <ul className="list-plain">
        {pageItems.map((finish) => (
          <li key={finish.id} className="list-item-card">
            <span>
              #{finish.id} — {finish.name} {finish.finish_group ? `(${finish.finish_group})` : ''}
            </span>
            <button className="danger" onClick={() => void handleDelete(finish.id)}>
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
