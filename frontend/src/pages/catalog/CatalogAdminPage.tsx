import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { type ComponentVariant, searchComponents } from '../../api/catalog'
import { Card, Esqueleto } from '../../components/ui'
import { usePageHeader } from '../../layout/usePageHeader'
import { VariantEditDrawer } from './VariantEditDrawer'

const money = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
export function CatalogAdminPage() {
  usePageHeader({ title: 'Estrutura do catálogo' })
  const [variants, setVariants] = useState<ComponentVariant[]>([]); const [total, setTotal] = useState(0); const [loading, setLoading] = useState(true); const [error, setError] = useState(''); const [editing, setEditing] = useState<ComponentVariant | null>(null)
  const load = async () => { try { const result = await searchComponents({ page_size: 25 }); setVariants(result.items); setTotal(result.total); setError('') } catch { setError('Não foi possível carregar as variações.') } finally { setLoading(false) } }
  useEffect(() => { void load() }, [])
  if (loading) return <div className="page"><Esqueleto linhas={8} /></div>
  return <div className="catalog-admin page"><header className="catalog-admin-head"><div><span className="eyebrow">Cadastro · somente admin</span><h1>Estrutura do catálogo</h1><p>Variações vendáveis são as combinações com SKU e preço usadas nos orçamentos.</p></div><Link className="catalog-admin-link" to="/catalogo">Ir para a consulta</Link></header>{error && <p className="feedback-error">{error}</p>}<Card className="admin-entity-table" title="Variações vendáveis" action={<Link to="/catalogo/admin/variacoes">Gerenciar cadastro →</Link>}><p className="helper-text">Produto + componente + dimensão + acabamento, com SKU e preço.</p><div className="admin-variant-head"><span>Componente</span><span>SKU</span><span>Dimensão</span><span>Acabamento</span><span>Preço</span><span /></div>{variants.map((variant) => <div className="admin-variant-row" key={variant.component_variant_id}><span><b>{variant.component}</b><small>{variant.descriptor ?? variant.product ?? 'Sem descritor'}</small></span><span className="mono">{variant.sku ?? '—'}</span><span className="mono">{variant.dimension?.raw_label ?? '—'}</span><span>{variant.finish ?? '—'}</span><strong className={variant.price ? 'mono' : 'admin-no-price'}>{variant.price ? money.format(variant.price.amount) : 'sem preço'}</strong><button className="admin-edit" onClick={() => setEditing(variant)}>Editar</button></div>)}<footer>Mostrando {variants.length} de {total} variações · Toda edição exige justificativa e fica no histórico.</footer></Card><VariantEditDrawer variant={editing} onClose={() => setEditing(null)} onSaved={load} /></div>
}
