import { useEffect, useState } from 'react'
import {
  CatalogApiError,
  type ComponentVariant,
  type Finish,
  type ProductComponentType,
  type ProductFamily,
  getComponent,
  listComponentTypes,
  listFinishes,
  listFamilies,
  searchComponents,
} from '../../../api/catalog'
import { usePageHeader } from '../../../layout/usePageHeader'

function describeError(err: unknown): string {
  if (err instanceof CatalogApiError) {
    return `${err.code}: ${err.message}`
  }
  return String(err)
}

function formatPrice(price: ComponentVariant['price']): string {
  if (!price) return '—'
  return `${price.currency} ${price.amount.toFixed(2)}`
}

function PriceCell({ price }: { price: ComponentVariant['price'] }) {
  if (!price) return <span className="badge badge-danger">sem preço</span>
  return <>{formatPrice(price)}</>
}

export function ConsultaPage() {
  usePageHeader({ title: 'Consulta do catálogo' })

  const [families, setFamilies] = useState<ProductFamily[]>([])
  const [componentTypes, setComponentTypes] = useState<ProductComponentType[]>([])
  const [finishes, setFinishes] = useState<Finish[]>([])

  const [q, setQ] = useState('')
  const [family, setFamily] = useState('')
  const [component, setComponent] = useState('')
  const [finish, setFinish] = useState('')
  const [width, setWidth] = useState('')
  const [depth, setDepth] = useState('')

  const [results, setResults] = useState<ComponentVariant[]>([])
  const [total, setTotal] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const [selected, setSelected] = useState<ComponentVariant | null>(null)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    Promise.all([listFamilies(), listComponentTypes(), listFinishes()])
      .then(([familiesData, componentTypesData, finishesData]) => {
        setFamilies(familiesData)
        setComponentTypes(componentTypesData)
        setFinishes(finishesData)
      })
      .catch((err) => setError(describeError(err)))
  }, [])

  async function runSearch() {
    setLoading(true)
    setError(null)
    try {
      const dimension = width && depth ? `${width}x${depth}` : undefined
      const result = await searchComponents({
        q: q || undefined,
        family: family || undefined,
        component: component || undefined,
        finish: finish || undefined,
        dimension,
      })
      setResults(result.items)
      setTotal(result.total)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- busca ao montar/filtrar
    void runSearch()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, family, component, finish, width, depth])

  async function selectItem(item: ComponentVariant) {
    setSelected(item)
    setDetailError(null)
    setDetailLoading(true)
    try {
      const detail = await getComponent(item.component_variant_id)
      setSelected(detail)
    } catch (err) {
      setDetailError(describeError(err))
    } finally {
      setDetailLoading(false)
    }
  }

  return (
    <div>
      <section>
        <input
          placeholder="Buscar por produto, SKU, descrição..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          style={{ width: '100%' }}
        />
        <div className="action-group" style={{ marginTop: 'var(--space-3)' }}>
          <label>
            Família:{' '}
            <select value={family} onChange={(e) => setFamily(e.target.value)}>
              <option value="">(todas)</option>
              {families.map((f) => (
                <option key={f.id} value={f.name}>
                  {f.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Componente:{' '}
            <select value={component} onChange={(e) => setComponent(e.target.value)}>
              <option value="">(todos)</option>
              {componentTypes.map((c) => (
                <option key={c.id} value={c.name}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Acabamento:{' '}
            <select value={finish} onChange={(e) => setFinish(e.target.value)}>
              <option value="">(todos)</option>
              {finishes.map((f) => (
                <option key={f.id} value={f.name}>
                  {f.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Dimensão: L
            <input
              type="number"
              min="1"
              value={width}
              onChange={(e) => setWidth(e.target.value)}
              style={{ width: '5rem' }}
            />{' '}
            × P
            <input
              type="number"
              min="1"
              value={depth}
              onChange={(e) => setDepth(e.target.value)}
              style={{ width: '5rem' }}
            />
          </label>
        </div>

        {error && (
          <p className="feedback-error action-group">
            {error}
            <button className="secondary" onClick={() => void runSearch()}>
              Tentar novamente
            </button>
          </p>
        )}

        <div className="split-layout">
          <div>
            <p>{loading ? 'Buscando…' : `${total} variação(ões) encontrada(s).`}</p>
            {!loading && total === 0 && !error && (
              <p>Nenhum item encontrado para esses critérios. Tente relaxar os filtros.</p>
            )}
            <table>
              <thead>
                <tr>
                  <th style={{ width: '38%' }}>Produto</th>
                  <th style={{ width: '22%' }}>Componente</th>
                  <th style={{ width: '22%' }}>Acabamento</th>
                  <th style={{ width: '18%' }}>Preço</th>
                </tr>
              </thead>
              <tbody>
                {results.map((item) => (
                  <tr
                    key={item.component_variant_id}
                    onClick={() => void selectItem(item)}
                    className={`row-clickable ${
                      selected?.component_variant_id === item.component_variant_id ? 'is-selected' : ''
                    }`}
                  >
                    <td>
                      {item.product ?? '—'} {item.descriptor ? `— ${item.descriptor}` : ''}
                    </td>
                    <td>{item.component}</td>
                    <td>{item.finish ?? '—'}</td>
                    <td><PriceCell price={item.price} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="split-layout__detail">
            {!selected && <p className="helper-text">Selecione um item para ver os detalhes.</p>}
            {selected && (
              <div>
                <h3 style={{ marginBottom: '2px' }}>
                  {selected.product ?? '—'} — {selected.component}
                  {selected.descriptor ? ` ${selected.descriptor}` : ''}
                </h3>
                <p className="helper-text" style={{ margin: 0 }}>
                  {selected.finish ?? '—'} · SKU {selected.sku ?? '—'}
                </p>
                {selected.price ? (
                  <div className="frozen-callout" style={{ marginTop: 'var(--space-3)' }}>
                    <span className="frozen-callout__price">{formatPrice(selected.price)}</span>
                    <span className="frozen-callout__hint">Preço vigente no catálogo.</span>
                  </div>
                ) : (
                  <p className="feedback-error" style={{ marginTop: 'var(--space-3)' }}>
                    Sem preço cadastrado — este item não pode ser adicionado a um orçamento.
                  </p>
                )}
                <p style={{ marginTop: 'var(--space-3)' }}>Dimensão: {selected.dimension?.raw_label ?? '—'}</p>
                <p>Descrição: {selected.description ?? '—'}</p>
                {detailLoading && <p className="helper-text">Carregando…</p>}
                {detailError && <p className="feedback-error">{detailError}</p>}
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  )
}
