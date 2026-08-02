import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  type ComponentVariant,
  type ComponentVariantPriceOrigin,
  type Dimension,
  type Finish,
  type ProductComponentType,
  type ProductFamily,
  getComponentPriceOrigin,
  listComponentTypes,
  listDimensions,
  listFinishes,
  listFamilies,
  searchComponents,
} from '../../../api/catalog'
import { addItem, listQuotes, type Quote } from '../../../api/quotes'
import { Botao, Card, Esqueleto, Vazio } from '../../../components/ui'
import { useAuth } from '../../../context/useAuth'
import { FINISH_HEX } from '../../../labels'
import { usePageHeader } from '../../../layout/usePageHeader'

const PAGE_SIZE = 25
const money = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

function variantName(item: ComponentVariant) {
  return [item.product, item.component, item.descriptor].filter(Boolean).join(' · ')
}

function formatDate(value: string | null) {
  if (!value) return null
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(value.replace(' ', 'T')),
  )
}

/**
 * Rótulo curto para a medida completa. Os rótulos do catálogo vêm como
 * "1800x1000x740"; na coluna estreita da tabela e nos chips do filtro isso
 * estoura a largura, então mostramos "1800 × 1000" e deixamos a altura como
 * sufixo discreto.
 */
function splitMeasure(rawLabel: string) {
  const parts = rawLabel.split(/[x×]/i).map((part) => part.trim())
  if (parts.length < 3) return { principal: rawLabel, altura: null as string | null }
  return { principal: `${parts[0]} × ${parts[1]}`, altura: parts[2] }
}

export function ConsultaPage() {
  usePageHeader({ title: 'Catálogo' })
  const { user } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const returnTo = searchParams.get('voltarPara')
  const quoteFromOrigin = returnTo?.match(/^\/orcamentos\/(\d+)\/itens$/)?.[1]
  const [families, setFamilies] = useState<ProductFamily[]>([])
  const [types, setTypes] = useState<ProductComponentType[]>([])
  const [finishes, setFinishes] = useState<Finish[]>([])
  const [dimensions, setDimensions] = useState<Dimension[]>([])
  const [q, setQ] = useState('')
  const [family, setFamily] = useState('')
  const [component, setComponent] = useState('')
  const [finish, setFinish] = useState('')
  const [dimension, setDimension] = useState('')
  // Passo 1 do seletor de dimensão. Não é um filtro enviado à API: serve para
  // reduzir a lista de medidas completas (que hoje passa de 50 valores) a um
  // punhado. Ver REDESIGN/09 — quando o backend aceitar filtro por eixo, esta
  // largura passa a ser um filtro de verdade.
  const [widthPick, setWidthPick] = useState('')
  const [page, setPage] = useState(1)
  const [items, setItems] = useState<ComponentVariant[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [drafts, setDrafts] = useState<Quote[]>([])
  const [adding, setAdding] = useState<ComponentVariant | null>(null)
  const [quoteId, setQuoteId] = useState('')
  const [addingBusy, setAddingBusy] = useState(false)
  const [auditItem, setAuditItem] = useState<ComponentVariant | null>(null)
  const [priceOrigin, setPriceOrigin] = useState<ComponentVariantPriceOrigin | null>(null)
  const [auditLoading, setAuditLoading] = useState(false)
  const [auditError, setAuditError] = useState('')

  useEffect(() => {
    void Promise.all([listFamilies(), listComponentTypes(), listFinishes(), listDimensions(), listQuotes()])
      .then(([loadedFamilies, loadedTypes, loadedFinishes, loadedDimensions, quotes]) => {
        setFamilies(loadedFamilies)
        setTypes(loadedTypes)
        setFinishes(loadedFinishes)
        setDimensions(loadedDimensions)
        setDrafts(quotes.filter((quote) => quote.status === 'rascunho'))
      })
      .catch(() => setError('Não foi possível carregar os filtros do catálogo.'))
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setLoading(true)
      void searchComponents({
        q: q || undefined,
        family: family || undefined,
        component: component || undefined,
        finish: finish || undefined,
        dimension: dimension || undefined,
        page,
        page_size: PAGE_SIZE,
      })
        .then((result) => {
          setItems(result.items)
          setTotal(result.total)
          setError('')
        })
        .catch(() => setError('Não foi possível buscar o catálogo.'))
        .finally(() => setLoading(false))
    }, 300)
    return () => window.clearTimeout(timer)
  }, [q, family, component, finish, dimension, page])

  const resetPage = (update: () => void) => { update(); setPage(1) }
  const clear = () => { setQ(''); setFamily(''); setComponent(''); setFinish(''); setDimension(''); setWidthPick(''); setPage(1) }
  const addToQuote = async (variant: ComponentVariant, targetId: string) => {
    setAddingBusy(true)
    try {
      await addItem(Number(targetId), { label: variantName(variant), component_variant_id: variant.component_variant_id })
      setAdding(null)
      navigate(`/orcamentos/${targetId}/itens`)
    } catch {
      setError('Não foi possível adicionar a peça ao orçamento.')
    } finally {
      setAddingBusy(false)
    }
  }
  const openAdd = (variant: ComponentVariant) => {
    if (quoteFromOrigin) { void addToQuote(variant, quoteFromOrigin); return }
    setAdding(variant)
    setQuoteId(drafts[0] ? String(drafts[0].id) : '')
  }
  const openAudit = async (variant: ComponentVariant) => {
    setAuditItem(variant)
    setPriceOrigin(null)
    setAuditError('')
    setAuditLoading(true)
    try {
      setPriceOrigin(await getComponentPriceOrigin(variant.component_variant_id))
    } catch {
      setAuditError('Não foi possível carregar a origem deste preço.')
    } finally {
      setAuditLoading(false)
    }
  }

  const active = [family, component, finish, dimension].filter(Boolean)
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const canSeeAudit = user?.role === 'admin' || user?.role === 'revisor'

  // Eixo de largura: valores distintos, ordenados. Reduz ~50 medidas completas
  // a ~13 chips curtos que cabem 4 por linha na barra de 198px úteis.
  const widths = [...new Set(dimensions.map((item) => item.width_mm).filter((value): value is number => value != null))]
    .sort((left, right) => left - right)
  const measures = dimensions
    .filter((item) => item.raw_label && (widthPick ? String(item.width_mm) === widthPick : false))
    .sort((left, right) => (left.raw_label ?? '').localeCompare(right.raw_label ?? '', 'pt-BR', { numeric: true }))
  const pickWidth = (value: string) => resetPage(() => {
    const next = widthPick === value ? '' : value
    setWidthPick(next)
    // Trocar de largura invalida a medida escolhida antes.
    if (dimension) setDimension('')
  })

  return <div className="catalog-page">
    <aside className="catalog-filters">
      <div className="catalog-filters__head">
        <span className="eyebrow">Refinar</span>
        {active.length > 0 && <button type="button" className="catalog-filters__clear" onClick={clear}>Limpar</button>}
      </div>

      <FilterGroup label="Linha" ativo={family} aberto>
        {families.map((item) => <FilterButton key={item.id} active={family === item.name} onClick={() => resetPage(() => setFamily(family === item.name ? '' : item.name))}>{item.name}</FilterButton>)}
      </FilterGroup>

      <FilterGroup label="Tipo de peça" ativo={component}>
        {types.map((item) => <FilterButton key={item.id} active={component === item.name} onClick={() => resetPage(() => setComponent(component === item.name ? '' : item.name))}>{item.name}</FilterButton>)}
      </FilterGroup>

      <FilterGroup label="Acabamento" ativo={finish}>
        <div className="finish-swatches">
          {finishes.map((item) => <button key={item.id} type="button" title={item.name} aria-label={item.name} aria-pressed={finish === item.name} className={finish === item.name ? 'is-active' : ''} style={{ backgroundColor: FINISH_HEX[item.name] ?? '#9BA39C' }} onClick={() => resetPage(() => setFinish(finish === item.name ? '' : item.name))} />)}
        </div>
        {finish && <small>{finish}</small>}
      </FilterGroup>

      <FilterGroup label="Dimensão" ativo={dimension || (widthPick && `${widthPick} de largura`) || ''}>
        <div className="dimension-step">
          <small>1 · Largura (mm)</small>
          <div className="dimension-axis">
            {widths.map((value) => <button key={value} type="button" aria-pressed={widthPick === String(value)} className={widthPick === String(value) ? 'is-active' : ''} onClick={() => pickWidth(String(value))}>{value}</button>)}
          </div>
        </div>
        {widthPick ? <div className="dimension-step">
          <small>2 · Medida completa</small>
          <div className="dimension-chips">
            {measures.map((item) => {
              const label = item.raw_label ?? ''
              const { principal, altura } = splitMeasure(label)
              return <button key={item.id} type="button" aria-pressed={dimension === label} className={dimension === label ? 'is-active' : ''} onClick={() => resetPage(() => setDimension(dimension === label ? '' : label))}>
                {principal}{altura && <i>h {altura}</i>}
              </button>
            })}
          </div>
          {measures.length === 0 && <p className="dimension-hint">Nenhuma medida cadastrada com esta largura.</p>}
        </div> : <p className="dimension-hint">Escolha a largura para ver as medidas disponíveis.</p>}
      </FilterGroup>
    </aside>

    <main className="catalog-results">
      <header className="catalog-head"><div><span className="eyebrow">Preços ativos do catálogo</span><h1>Catálogo</h1></div><input value={q} onChange={(event) => resetPage(() => setQ(event.target.value))} placeholder="Buscar SKU, peça ou descritor…" /></header>
      <div className="catalog-context"><span>{total} variações encontradas</span>{active.map((value) => <button key={value} onClick={() => resetPage(() => { if (value === family) setFamily(''); if (value === component) setComponent(''); if (value === finish) setFinish(''); if (value === dimension) setDimension('') })}>{value} ×</button>)}{active.length > 0 && <button onClick={clear}>Limpar filtros</button>}</div>
      {error && <p className="feedback-error">{error}</p>}
      {loading ? <Esqueleto linhas={7} /> : items.length === 0 ? <Vazio titulo="Nenhuma peça com estes filtros" descricao="Ajuste ou limpe os filtros para consultar outras variações." acao={<Botao variante="secundario" onClick={clear}>Limpar filtros</Botao>} /> : <>
        <Card padding="none" className="catalog-table">
          <header><span>Peça</span><span>SKU</span><span>Dimensão</span><span>Preço atual</span><span /></header>
          {items.map((item) => {
            const rawLabel = item.dimension?.raw_label ?? null
            const measure = rawLabel ? splitMeasure(rawLabel) : null
            return <div className="catalog-row" key={item.component_variant_id}>
              <span><b>{variantName(item)}</b><small>{item.finish ?? 'Sem acabamento definido'}</small></span>
              <span className="mono">{item.sku ?? '—'}</span>
              <span className="catalog-measure mono" title={rawLabel ?? undefined}>{measure ? <>{measure.principal}{measure.altura && <small>h {measure.altura}</small>}</> : '—'}</span>
              {item.price ? <strong className="mono">{money.format(item.price.amount)}</strong> : <strong className="catalog-no-price">sem preço</strong>}
              <span className="catalog-row-actions"><Botao tamanho="sm" variante="secundario" disabled={!item.price || addingBusy} title={!item.price ? 'Sem preço cadastrado.' : undefined} onClick={() => openAdd(item)}>{quoteFromOrigin && addingBusy ? 'Adicionando…' : '+ Orçamento'}</Botao>{canSeeAudit && <button className="catalog-audit-button" title="Ver origem do preço" aria-label={`Ver origem do preço: ${variantName(item)}`} onClick={() => void openAudit(item)}>⋯</button>}</span>
            </div>
          })}
        </Card>
        {totalPages > 1 && <nav className="catalog-pagination-redesign" aria-label="Paginação do catálogo"><Botao tamanho="sm" variante="secundario" disabled={page === 1} onClick={() => setPage((value) => value - 1)}>Anterior</Botao><span>Página {page} de {totalPages}</span><Botao tamanho="sm" variante="secundario" disabled={page === totalPages} onClick={() => setPage((value) => value + 1)}>Próxima</Botao></nav>}
      </>}
    </main>
    {adding && <div className="catalog-add-dialog" role="dialog" aria-modal="true"><Card title="Adicionar ao orçamento"><p>{variantName(adding)}</p>{drafts.length > 0 ? <select value={quoteId} onChange={(event) => setQuoteId(event.target.value)}>{drafts.map((quote) => <option key={quote.id} value={quote.id}>{quote.quote_number} · {quote.customer.name}</option>)}</select> : <p className="feedback-warning">Crie um orçamento em rascunho antes de adicionar peças.</p>}<footer><Botao variante="secundario" onClick={() => setAdding(null)}>Cancelar</Botao><Botao disabled={!quoteId || addingBusy} onClick={() => void addToQuote(adding, quoteId)}>{addingBusy ? 'Adicionando…' : 'Adicionar'}</Botao></footer></Card></div>}
    {auditItem && <PriceOriginDrawer item={auditItem} origin={priceOrigin} loading={auditLoading} error={auditError} onClose={() => setAuditItem(null)} />}
  </div>
}

function PriceOriginDrawer({ item, origin, loading, error, onClose }: { item: ComponentVariant; origin: ComponentVariantPriceOrigin | null; loading: boolean; error: string; onClose: () => void }) {
  const imported = origin?.source.kind === 'importacao_json' || origin?.source.kind === 'importacao_pdf'
  const sourceLabel = origin?.source.kind === 'importacao_json' ? 'Importação estruturada' : 'Importação de PDF (legado)'
  return <div className="catalog-audit-backdrop" role="presentation"><aside className="catalog-audit-drawer" role="dialog" aria-modal="true" aria-label="Origem do preço"><header><div><span className="eyebrow">Auditoria de preço</span><h2>{variantName(item)}</h2></div><button onClick={onClose} aria-label="Fechar">×</button></header><div className="catalog-audit-body">{loading && <Esqueleto linhas={4} />}{error && <p className="feedback-error">{error}</p>}{origin && <><section><span className="eyebrow">Preço atual</span><strong className="mono">{origin.price ? money.format(origin.price.amount) : 'Sem preço cadastrado'}</strong></section><section><span className="eyebrow">Origem</span>{imported ? <><b>{sourceLabel}</b>{origin.source.original_filename && <p>{origin.source.original_filename}</p>}{origin.source.reference && <p>{origin.source.reference}</p>}{formatDate(origin.source.imported_at) && <small>Importado em {formatDate(origin.source.imported_at)}</small>}</> : <p>Cadastro manual no catálogo.</p>}</section><section><span className="eyebrow">Alterações registradas</span>{origin.changes.length === 0 ? <p>Nenhuma alteração manual registrada.</p> : <ol className="catalog-audit-history">{origin.changes.map((change) => <li key={`${change.changed_at}-${change.reason}`}><b>{change.reason}</b><small>{change.changed_by} · {formatDate(change.changed_at)}</small>{change.previous_price && change.new_price && <span className="mono">{money.format(change.previous_price.amount)} → {money.format(change.new_price.amount)}</span>}</li>)}</ol>}</section></>}</div></aside></div>
}

function FilterGroup({ label, ativo, aberto, children }: { label: string; ativo?: string; aberto?: boolean; children: React.ReactNode }) {
  return <details className="filter-group" open={aberto || Boolean(ativo)}>
    <summary><b>{label}</b>{ativo && <em title={ativo}>{ativo}</em>}</summary>
    {children}
  </details>
}

function FilterButton({ active, children, onClick }: { active: boolean; children: React.ReactNode; onClick: () => void }) {
  return <button type="button" aria-pressed={active} className={active ? 'is-active' : ''} onClick={onClick}>{children}</button>
}
