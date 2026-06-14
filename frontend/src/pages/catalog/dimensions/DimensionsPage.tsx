import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { createDimension, deleteDimension } from '../../../api/catalog'
import { ErrorMessage, Pagination } from '../shared'
import { describeError, type CatalogContextValue } from '../catalogContext'

const PAGE_SIZE = 10

export function DimensionsPage() {
  const { dimensions, reload } = useOutletContext<CatalogContextValue>()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [showForm, setShowForm] = useState(false)

  const [width, setWidth] = useState('')
  const [depth, setDepth] = useState('')
  const [diameter, setDiameter] = useState('')
  const [height, setHeight] = useState('')
  const [rawLabel, setRawLabel] = useState('')
  const [error, setError] = useState<string | null>(null)

  function updateSearch(value: string) {
    setSearch(value)
    setPage(1)
  }

  const term = search.trim().toLowerCase()
  const filtered = term
    ? dimensions.filter((d) => (d.raw_label ?? '').toLowerCase().includes(term))
    : dimensions

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await createDimension({
        width_mm: width ? Number(width) : null,
        depth_mm: depth ? Number(depth) : null,
        diameter_mm: diameter ? Number(diameter) : null,
        height_mm: height ? Number(height) : null,
        raw_label: rawLabel || null,
      })
      setWidth('')
      setDepth('')
      setDiameter('')
      setHeight('')
      setRawLabel('')
      await reload()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function handleDelete(id: number) {
    setError(null)
    try {
      await deleteDimension(id)
      await reload()
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <section>
      <div className="catalog-section-header">
        <div>
          <h2>Dimensões</h2>
          <p className="catalog-section-header__hint">
            Medidas reutilizadas pelos produtos-base e pelas variações vendáveis.
          </p>
        </div>
        <div className="catalog-section-header__actions">
          {dimensions.length > 0 && (
            <input
              className="catalog-search"
              placeholder="Buscar por rótulo..."
              value={search}
              onChange={(e) => updateSearch(e.target.value)}
            />
          )}
          <button type="button" className={showForm ? 'secondary' : ''} onClick={() => setShowForm((v) => !v)}>
            {showForm ? 'Cancelar' : '+ Nova dimensão'}
          </button>
        </div>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="catalog-add-form">
          <input placeholder="Rótulo (ex.: 1200x900)" value={rawLabel} onChange={(e) => setRawLabel(e.target.value)} />
          <input placeholder="Largura (mm)" value={width} onChange={(e) => setWidth(e.target.value)} />
          <input placeholder="Profundidade (mm)" value={depth} onChange={(e) => setDepth(e.target.value)} />
          <input placeholder="Diâmetro (mm)" value={diameter} onChange={(e) => setDiameter(e.target.value)} />
          <input placeholder="Altura (mm)" value={height} onChange={(e) => setHeight(e.target.value)} />
          <button type="submit">Adicionar dimensão</button>
        </form>
      )}

      {dimensions.length === 0 && <p>Nenhuma dimensão cadastrada ainda.</p>}
      {dimensions.length > 0 && filtered.length === 0 && <p>Nenhuma dimensão corresponde à busca.</p>}

      <ul className="list-plain">
        {pageItems.map((dimension) => (
          <li key={dimension.id} className="list-item-card">
            <span>
              #{dimension.id} — {dimension.raw_label ?? '—'} (L:{dimension.width_mm ?? '-'} P:
              {dimension.depth_mm ?? '-'} ⌀:{dimension.diameter_mm ?? '-'} A:
              {dimension.height_mm ?? '-'})
            </span>
            <button className="danger" onClick={() => void handleDelete(dimension.id)}>
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
