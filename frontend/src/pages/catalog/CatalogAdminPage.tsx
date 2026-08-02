import { useEffect, useState } from 'react'
import { Link, useOutletContext } from 'react-router-dom'
import { createComponent, searchComponents, type ComponentVariant } from '../../api/catalog'
import { Botao, Card, Esqueleto } from '../../components/ui'
import { ComponentTypesPage } from './componentTypes/ComponentTypesPage'
import { type CatalogContextValue, describeError } from './catalogContext'
import { DimensionsPage } from './dimensions/DimensionsPage'
import { FamiliesPage } from './families/FamiliesPage'
import { FinishesPage } from './finishes/FinishesPage'
import { ProductsPage } from './products/ProductsPage'
import { VariantEditDrawer } from './VariantEditDrawer'

const money = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const PAGE_SIZE = 25

type Entity = 'variants' | 'families' | 'products' | 'components' | 'dimensions' | 'finishes'

const entities: { id: Entity; name: string; description: string }[] = [
  { id: 'families', name: 'Famílias de produto', description: 'Agrupamentos de alto nível para organizar produtos-base.' },
  { id: 'products', name: 'Produtos-base', description: 'Produtos dentro de uma família, com uma dimensão associada.' },
  { id: 'components', name: 'Tipos de componente', description: 'Peças que compõem um produto, como tampo e estrutura.' },
  { id: 'dimensions', name: 'Dimensões', description: 'Medidas reutilizadas pelos produtos e suas variações.' },
  { id: 'finishes', name: 'Acabamentos', description: 'Cores e materiais agrupados por tipo.' },
  { id: 'variants', name: 'Variações vendáveis', description: 'Combinações finais com SKU e preço para o orçamento.' },
]

export function CatalogAdminPage() {
  const ctx = useOutletContext<CatalogContextValue>()
  const [selected, setSelected] = useState<Entity>('variants')

  const counts: Record<Entity, number> = {
    variants: -1,
    families: ctx.families.length,
    products: ctx.products.length,
    components: ctx.componentTypes.length,
    dimensions: ctx.dimensions.length,
    finishes: ctx.finishes.length,
  }

  return <div className="catalog-admin page">
    <header className="catalog-admin-head">
      <div><span className="eyebrow">Cadastro · somente admin</span><h1>Estrutura do catálogo</h1><p>Famílias, produtos-base, tipos de componente, dimensões e acabamentos são as peças de montagem. As variações vendáveis são o que o vendedor realmente coloca em um orçamento.</p></div>
      <Link className="catalog-admin-link" to="/catalogo">Ir para a consulta</Link>
    </header>
    <div className="admin-entity-grid" role="tablist" aria-label="Entidades do catálogo">
      {entities.map((entity) => <button key={entity.id} type="button" role="tab" aria-selected={selected === entity.id} className={selected === entity.id ? 'is-active' : ''} onClick={() => setSelected(entity.id)}><span>{entity.name}</span><strong>{counts[entity.id] < 0 ? '—' : counts[entity.id]}</strong><small>{entity.description}</small></button>)}
    </div>
    {selected === 'variants' && <VariantsAdmin />}
    {selected === 'families' && <FamiliesPage />}
    {selected === 'products' && <ProductsPage />}
    {selected === 'components' && <ComponentTypesPage />}
    {selected === 'dimensions' && <DimensionsPage />}
    {selected === 'finishes' && <FinishesPage />}
  </div>
}

function VariantsAdmin() {
  const { componentTypes, products, dimensions, finishes, reload } = useOutletContext<CatalogContextValue>()
  const [variants, setVariants] = useState<ComponentVariant[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState<ComponentVariant | null>(null)
  const [showNew, setShowNew] = useState(false)
  const [saving, setSaving] = useState(false)
  const [componentId, setComponentId] = useState('')
  const [productId, setProductId] = useState('')
  const [dimensionId, setDimensionId] = useState('')
  const [finishId, setFinishId] = useState('')
  const [descriptor, setDescriptor] = useState('')
  const [sku, setSku] = useState('')
  const [price, setPrice] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const result = await searchComponents({ page, page_size: PAGE_SIZE })
      setVariants(result.items); setTotal(result.total); setError('')
    } catch (err) { setError(describeError(err)) } finally { setLoading(false) }
  }
  useEffect(() => { void load() }, [page])

  const create = async (event: React.FormEvent) => {
    event.preventDefault(); if (!componentId) return
    const amount = price.trim() ? Number(price.replace(',', '.')) : NaN
    if (price.trim() && (Number.isNaN(amount) || amount < 0)) { setError('Informe um preço válido.'); return }
    setSaving(true); setError('')
    try {
      await createComponent({ component_id: Number(componentId), product_id: productId ? Number(productId) : null, dimension_id: dimensionId ? Number(dimensionId) : null, finish_id: finishId ? Number(finishId) : null, descriptor: descriptor || null, sku: sku ? { code: sku } : null, price: price.trim() ? { amount, currency: 'BRL' } : null })
      setShowNew(false); setComponentId(''); setProductId(''); setDimensionId(''); setFinishId(''); setDescriptor(''); setSku(''); setPrice('')
      await reload(); await load()
    } catch (err) { setError(describeError(err)) } finally { setSaving(false) }
  }
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return <Card className="admin-entity-table" title="Variações vendáveis" action={<Botao tamanho="sm" onClick={() => setShowNew((open) => !open)}>{showNew ? 'Cancelar' : '+ Nova variação'}</Botao>}>
    <p className="helper-text">Produto + componente + dimensão + acabamento, com SKU e preço.</p>
    {showNew && <form className="admin-variant-form" onSubmit={create}>
      <select required value={componentId} onChange={(event) => setComponentId(event.target.value)}><option value="">Tipo de componente *</option>{componentTypes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
      <select value={productId} onChange={(event) => setProductId(event.target.value)}><option value="">Produto-base</option>{products.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
      <select value={dimensionId} onChange={(event) => setDimensionId(event.target.value)}><option value="">Dimensão</option>{dimensions.map((item) => <option key={item.id} value={item.id}>{item.raw_label ?? `#${item.id}`}</option>)}</select>
      <select value={finishId} onChange={(event) => setFinishId(event.target.value)}><option value="">Acabamento</option>{finishes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
      <input value={descriptor} onChange={(event) => setDescriptor(event.target.value)} placeholder="Descritor" />
      <input value={sku} onChange={(event) => setSku(event.target.value)} placeholder="SKU" />
      <input value={price} onChange={(event) => setPrice(event.target.value)} inputMode="decimal" placeholder="Preço (BRL)" />
      <Botao tamanho="sm" disabled={saving}>{saving ? 'Salvando…' : 'Criar variação'}</Botao>
    </form>}
    {error && <p className="feedback-error">{error}</p>}
    {loading ? <Esqueleto linhas={6} /> : <>
      <div className="admin-variant-head"><span>Componente</span><span>SKU</span><span>Dimensão</span><span>Acabamento</span><span>Preço</span><span /></div>
      {variants.map((variant) => <div className="admin-variant-row" key={variant.component_variant_id}><span><b>{variant.component}</b><small>{variant.descriptor ?? variant.product ?? 'Sem descritor'}</small></span><span className="mono">{variant.sku ?? '—'}</span><span className="mono">{variant.dimension?.raw_label ?? '—'}</span><span>{variant.finish ?? '—'}</span><strong className={variant.price ? 'mono' : 'admin-no-price'}>{variant.price ? money.format(variant.price.amount) : 'sem preço'}</strong><button className="admin-edit" onClick={() => setEditing(variant)}>Editar</button></div>)}
      <footer><span>Mostrando {variants.length} de {total} variações · Toda edição aqui exige justificativa e fica no histórico.</span>{totalPages > 1 && <span className="admin-pagination"><Botao tamanho="sm" variante="secundario" disabled={page === 1} onClick={() => setPage((value) => value - 1)}>Anterior</Botao><b>Página {page} de {totalPages}</b><Botao tamanho="sm" variante="secundario" disabled={page === totalPages} onClick={() => setPage((value) => value + 1)}>Próxima</Botao></span>}</footer>
    </>}
    <VariantEditDrawer variant={editing} onClose={() => setEditing(null)} onSaved={load} />
  </Card>
}
