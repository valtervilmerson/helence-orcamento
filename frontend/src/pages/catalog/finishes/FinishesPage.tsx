import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { createFinish, deleteFinish, updateFinish, type Finish, type FinishGroup } from '../../../api/catalog'
import { ErrorMessage, Pagination } from '../shared'
import { describeError, type CatalogContextValue } from '../catalogContext'

const PAGE_SIZE = 10

const GROUP_OPTIONS: { value: FinishGroup; label: string }[] = [
  { value: 'madeirado', label: 'madeirado' },
  { value: 'metalico', label: 'metálico' },
  { value: 'pe_estrutura', label: 'pé/estrutura' },
  { value: 'outro', label: 'outro' },
]

function toggleGroup(groups: FinishGroup[], group: FinishGroup): FinishGroup[] {
  return groups.includes(group) ? groups.filter((g) => g !== group) : [...groups, group]
}

function GroupCheckboxes({
  value,
  onChange,
}: {
  value: FinishGroup[]
  onChange: (groups: FinishGroup[]) => void
}) {
  return (
    <div className="action-group">
      {GROUP_OPTIONS.map((opt) => (
        <label key={opt.value} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <input
            type="checkbox"
            checked={value.includes(opt.value)}
            onChange={() => onChange(toggleGroup(value, opt.value))}
          />
          {opt.label}
        </label>
      ))}
    </div>
  )
}

export function FinishesPage() {
  const { finishes, reload } = useOutletContext<CatalogContextValue>()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [showForm, setShowForm] = useState(false)

  const [name, setName] = useState('')
  const [groups, setGroups] = useState<FinishGroup[]>([])
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const [editingId, setEditingId] = useState<number | null>(null)
  const [editingGroups, setEditingGroups] = useState<FinishGroup[]>([])
  const [savingGroups, setSavingGroups] = useState(false)

  function updateSearch(value: string) {
    setSearch(value)
    setPage(1)
  }

  const term = search.trim().toLowerCase()
  const filtered = term
    ? finishes.filter(
        (f) => f.name.toLowerCase().includes(term) || f.finish_groups.some((g) => g.includes(term)),
      )
    : finishes

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await createFinish({ name, finish_groups: groups })
      setName('')
      setGroups([])
      await reload()
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
      await deleteFinish(id)
      await reload()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setDeletingId(null)
    }
  }

  function startEditingGroups(finish: Finish) {
    setEditingId(finish.id)
    setEditingGroups(finish.finish_groups)
    setError(null)
  }

  async function handleSaveGroups() {
    if (editingId === null) return
    setError(null)
    setSavingGroups(true)
    try {
      await updateFinish(editingId, { finish_groups: editingGroups })
      setEditingId(null)
      await reload()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSavingGroups(false)
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
          <GroupCheckboxes value={groups} onChange={setGroups} />
          <button type="submit" disabled={submitting}>
            {submitting ? 'Adicionando…' : 'Adicionar acabamento'}
          </button>
        </form>
      )}

      {finishes.length === 0 && <p>Nenhum acabamento cadastrado ainda.</p>}
      {finishes.length > 0 && filtered.length === 0 && <p>Nenhum acabamento corresponde à busca.</p>}

      <ul className="list-plain">
        {pageItems.map((finish) => (
          <li key={finish.id} className="list-item-card list-item-card--column">
            <div className="list-item-card__row">
              <span>
                #{finish.id} — {finish.name}{' '}
                {finish.finish_groups.length > 0 ? `(${finish.finish_groups.join(', ')})` : ''}
              </span>
              <div className="action-group">
                <button type="button" className="secondary" onClick={() => startEditingGroups(finish)}>
                  {editingId === finish.id ? 'fechar' : 'editar grupos'}
                </button>
                <button
                  className="danger"
                  disabled={deletingId === finish.id}
                  onClick={() => void handleDelete(finish.id)}
                >
                  {deletingId === finish.id ? 'excluindo…' : 'excluir'}
                </button>
              </div>
            </div>
            {editingId === finish.id && (
              <div className="field-group" style={{ marginTop: 'var(--space-2)' }}>
                <GroupCheckboxes value={editingGroups} onChange={setEditingGroups} />
                <button type="button" disabled={savingGroups} onClick={() => void handleSaveGroups()}>
                  {savingGroups ? 'Salvando…' : 'Salvar grupos'}
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>

      <Pagination page={page} totalPages={totalPages} onChange={setPage} />
      <ErrorMessage error={error} />
    </section>
  )
}
