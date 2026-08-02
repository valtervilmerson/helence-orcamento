import { useEffect, useState } from 'react'
import { listFinishes, type Finish, type FinishGroup } from '../../../api/catalog'
import { applyBatchCorrection, batchReviewExtractedItems, getImportItems, getImportSummary, previewBatchCorrection, reviewExtractedItem, type BatchCorrectionPreviewOut, type BatchCorrectionScope, type ConfidenceLevel, type ExtractedItem, type ImportListItem, type ReviewStatus } from '../../../api/imports'
import { Botao, Selo } from '../../../components/ui'
import { useAuth } from '../../../context/useAuth'

const fields: { field: keyof ExtractedItem; label: string }[] = [
  { field: 'component_type_raw', label: 'Tipo de componente' }, { field: 'description_raw', label: 'Descrição' }, { field: 'dimension_raw', label: 'Dimensão' }, { field: 'finish_raw', label: 'Acabamento' }, { field: 'sku_raw', label: 'SKU' }, { field: 'price_raw', label: 'Preço' },
]
const finalStatuses: ReviewStatus[] = ['aprovado', 'rejeitado']
const finishGroups: { value: FinishGroup; label: string }[] = [{ value: 'madeirado', label: 'Madeirado' }, { value: 'metalico', label: 'Metálico' }, { value: 'pe_estrutura', label: 'Pé/estrutura' }, { value: 'outro', label: 'Outro' }]
const errorMessage = (error: unknown) => error instanceof Error ? error.message : 'Não foi possível concluir a ação.'
const tone = (level: ConfidenceLevel | null): 'erro' | 'atencao' | 'ok' => level === 'baixa' ? 'erro' : level === 'media' ? 'atencao' : 'ok'
function reason(item: ExtractedItem) {
  const problem = [[item.price_raw, 'Preço não identificado'], [item.finish_raw, 'Acabamento não identificado'], [item.dimension_raw, 'Dimensão não identificada'], [item.component_type_raw, 'Tipo de peça não identificado']].find(([value]) => !value)
  return problem?.[1] ?? item.source_text ?? 'Este item requer uma decisão humana antes de entrar no catálogo.'
}

function RawItem({ item }: { item: ExtractedItem }) {
  return <section className="review-raw"><header><b>Como veio da planilha</b><small>somente leitura</small></header>{fields.map(({ field, label }) => { const value = item[field] as string | null; return <p key={field}><span>{label}</span><strong className={value ? 'mono' : 'review-raw__missing'}>{value || '(célula vazia)'}</strong></p> })}</section>
}

function BatchPanel({ itemId, field, onDone }: { itemId: number; field: string; onDone: () => void }) {
  const [scope, setScope] = useState<BatchCorrectionScope>('page')
  const [preview, setPreview] = useState<BatchCorrectionPreviewOut | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { setPreview(null); void previewBatchCorrection(itemId, field, scope).then(setPreview).catch((err) => setError(errorMessage(err))) }, [itemId, field, scope])
  const apply = async () => { setBusy(true); setError(''); try { await applyBatchCorrection(itemId, field, scope); onDone() } catch (err) { setError(errorMessage(err)) } finally { setBusy(false) } }
  return <div className="review-batch"><label><input type="checkbox" defaultChecked /> Aplicar a mesma correção em <b>{preview?.eligible_count ?? 0} itens</b> <select value={scope} onChange={(event) => setScope(event.target.value as BatchCorrectionScope)}><option value="page">nesta página</option><option value="page_profile">neste tipo de página</option><option value="import">nesta importação</option></select></label><small>Itens já decididos por alguém não serão tocados{preview?.already_decided_count ? ` (${preview.already_decided_count} preservados)` : ''}.</small>{error && <p className="feedback-error">{error}</p>}<Botao tamanho="sm" variante="secundario" disabled={busy || !preview?.eligible_count} onClick={() => void apply()}>{busy ? 'Aplicando…' : 'Aplicar correção em lote'}</Botao></div>
}

function Detail({ item, finishes, onDecided }: { item: ExtractedItem; finishes: Finish[]; onDecided: () => void }) {
  const { user } = useAuth()
  const canReview = user?.role === 'revisor' || user?.role === 'admin'
  const final = finalStatuses.includes(item.review_status)
  const [editing, setEditing] = useState<string | null>(null)
  const [value, setValue] = useState('')
  const [newFinish, setNewFinish] = useState(false)
  const [finishGroup, setFinishGroup] = useState<FinishGroup>('madeirado')
  const [notes, setNotes] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [batchField, setBatchField] = useState<string | null>(null)
  const begin = (field: keyof ExtractedItem) => { setEditing(field); setValue((item[field] as string | null) ?? ''); setNewFinish(false); setError('') }
  const saveCorrection = async () => { if (!editing) return; if (editing === 'finish_raw' && newFinish && !value.trim()) { setError('Informe o novo acabamento.'); return }; setBusy(true); setError(''); try { await reviewExtractedItem(item.id, { decision: 'corrigido', field: editing, previous_value: (item[editing as keyof ExtractedItem] as string | null) ?? null, corrected_value: value, notes: notes || undefined, ...(editing === 'finish_raw' && newFinish ? { new_finish_name: value, new_finish_group: finishGroup } : {}) }); setBatchField(editing); setEditing(null) } catch (err) { setError(errorMessage(err)) } finally { setBusy(false) } }
  const decide = async (decision: 'aprovado' | 'rejeitado') => { if (decision === 'rejeitado' && !notes.trim()) { setError('Informe a justificativa para rejeitar.'); return }; setBusy(true); setError(''); try { await reviewExtractedItem(item.id, { decision, notes: notes || undefined }); onDecided() } catch (err) { setError(errorMessage(err)) } finally { setBusy(false) } }
  return <section className="review-normalized"><header><b>Como vai para o catálogo</b><small>editável</small></header>{fields.map(({ field, label }) => <label className={`review-field${editing === field ? ' is-editing' : ''}`} key={field}><span>{label}</span>{editing === field ? field === 'finish_raw' ? <><select value={newFinish ? '__new__' : value} onChange={(event) => { if (event.target.value === '__new__') { setNewFinish(true); setValue('') } else { setNewFinish(false); setValue(event.target.value) } }}><option value="">Selecione</option>{finishes.map((finish) => <option key={finish.id} value={finish.name}>{finish.name}</option>)}<option value="__new__">Cadastrar novo acabamento</option></select>{newFinish && <><input value={value} onChange={(event) => setValue(event.target.value)} placeholder="Nome do acabamento" /><select value={finishGroup} onChange={(event) => setFinishGroup(event.target.value as FinishGroup)}>{finishGroups.map((group) => <option key={group.value} value={group.value}>{group.label}</option>)}</select></>}</> : <input value={value} onChange={(event) => setValue(event.target.value)} /> : <strong>{(item[field] as string | null) ?? '—'}</strong>} {!final && canReview && <button type="button" onClick={() => editing === field ? setEditing(null) : begin(field)}>{editing === field ? 'Cancelar' : 'Corrigir'}</button>}</label>)}{editing && <div className="review-save-correction"><Botao tamanho="sm" disabled={busy} onClick={() => void saveCorrection()}>{busy ? 'Salvando…' : 'Salvar correção'}</Botao></div>}{batchField && <BatchPanel itemId={item.id} field={batchField} onDone={onDecided} />}<label className="review-notes">Observações {final ? '' : '(obrigatórias ao rejeitar)'}<textarea value={notes} onChange={(event) => setNotes(event.target.value)} disabled={final} /></label>{error && <p className="feedback-error">{error}</p>}{final ? <p className="review-final">Decisão final registrada: {item.review_status}.</p> : !canReview ? <p className="helper-text">Somente revisor ou admin podem decidir.</p> : <footer><Botao variante="perigo" disabled={busy} onClick={() => void decide('rejeitado')}>Rejeitar item</Botao><span>Toda decisão fica registrada com seu nome e horário.</span><Botao disabled={busy || Boolean(editing)} onClick={() => void decide('aprovado')}>{item.review_status === 'corrigido' ? 'Aprovar corrigido →' : 'Aprovar →'}</Botao></footer>}</section>
}

export function ReviewPage({ importId, onBack }: { importId: number; onBack: () => void }) {
  const { user } = useAuth()
  const canReview = user?.role === 'revisor' || user?.role === 'admin'
  const [items, setItems] = useState<ExtractedItem[]>([])
  const [summary, setSummary] = useState<ImportListItem | null>(null)
  const [total, setTotal] = useState(0)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [finishes, setFinishes] = useState<Finish[]>([])
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<ReviewStatus | ''>('pendente')
  const [confidence, setConfidence] = useState<ConfidenceLevel | ''>('')
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [bulkNotes, setBulkNotes] = useState('')
  const [bulkBusy, setBulkBusy] = useState(false)
  const [error, setError] = useState('')
  const reload = async () => { try { const [info, result] = await Promise.all([getImportSummary(importId), getImportItems(importId, { review_status: status || undefined, confidence_level: confidence || undefined, search: search || undefined, page_size: 50 })]); setSummary(info); setItems(result.items); setTotal(result.total); setSelectedId((current) => current && result.items.some((item) => item.id === current) ? current : result.items[0]?.id ?? null); setError('') } catch (err) { setError(errorMessage(err)) } }
  useEffect(() => { void reload(); setSelected(new Set()) }, [importId, status, confidence, search])
  useEffect(() => { void listFinishes().then(setFinishes).catch(() => setFinishes([])) }, [])
  const current = items.find((item) => item.id === selectedId) ?? null
  const decided = Math.max(0, (summary?.items_extracted ?? 0) - (summary?.items_blocking_publication ?? 0))
  const progress = summary?.items_extracted ? Math.round(decided * 100 / summary.items_extracted) : 0
  const toggle = (id: number) => setSelected((old) => { const next = new Set(old); next.has(id) ? next.delete(id) : next.add(id); return next })
  const afterDecision = () => { const index = items.findIndex((item) => item.id === selectedId); const next = items.slice(index + 1).find((item) => !finalStatuses.includes(item.review_status)) ?? items.find((item) => item.id !== selectedId && !finalStatuses.includes(item.review_status)); if (next) setSelectedId(next.id); void reload() }
  const bulk = async (decision: 'aprovado' | 'rejeitado') => { if (decision === 'rejeitado' && !bulkNotes.trim()) { setError('Informe a justificativa para rejeitar em lote.'); return }; setBulkBusy(true); try { await batchReviewExtractedItems(Array.from(selected), decision, bulkNotes || undefined); setSelected(new Set()); setBulkNotes(''); await reload() } catch (err) { setError(errorMessage(err)) } finally { setBulkBusy(false) } }
  return <div className="review-page"><aside className="review-list"><header><Botao tamanho="sm" variante="fantasma" onClick={onBack}>← Importações</Botao><span className="eyebrow">{summary?.original_filename ?? `Importação #${importId}`}</span><h1>Fila de revisão</h1><div className="progress"><div className="progress__fill" style={{ width: `${progress}%` }} /></div><small className="mono">{decided}/{summary?.items_extracted ?? 0} decididos</small><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar SKU ou descrição…" /></header><nav className="review-filter-chips"><button className={status === 'pendente' ? 'is-active' : ''} onClick={() => setStatus('pendente')}>Pendentes</button><button className={confidence === 'baixa' ? 'is-active' : ''} onClick={() => setConfidence(confidence === 'baixa' ? '' : 'baixa')}>Baixa</button><button className={confidence === 'media' ? 'is-active' : ''} onClick={() => setConfidence(confidence === 'media' ? '' : 'media')}>Média</button><button className={status === '' ? 'is-active' : ''} onClick={() => { setStatus(''); setConfidence('') }}>Decididos</button></nav><div className="review-list__items">{items.map((item) => <article key={item.id} className={item.id === selectedId ? 'is-active' : ''} onClick={() => setSelectedId(item.id)}><input type="checkbox" checked={selected.has(item.id)} onClick={(event) => event.stopPropagation()} onChange={() => toggle(item.id)} aria-label={`Selecionar item ${item.id}`} /><div><b className="mono">{item.sku_raw ?? `Item #${item.id}`}</b><p>{item.description_raw ?? item.component_type_raw ?? 'Sem descrição'}</p><small>{reason(item)}</small></div><Selo tom={tone(item.confidence_level)}>{item.confidence_level ?? '—'}</Selo></article>)}</div>{selected.size > 0 && canReview && <footer className="review-bulk"><b>{selected.size} selecionados</b><input value={bulkNotes} onChange={(event) => setBulkNotes(event.target.value)} placeholder="Justificativa para rejeitar" /><Botao tamanho="sm" variante="secundario" disabled={bulkBusy} onClick={() => void bulk('rejeitado')}>Rejeitar</Botao><Botao tamanho="sm" disabled={bulkBusy} onClick={() => void bulk('aprovado')}>Aprovar em lote</Botao></footer>}</aside><main className="review-detail">{error && <p className="feedback-error">{error}</p>}{!current ? <p className="helper-text">Nenhum item encontrado com estes filtros.</p> : <><header className="review-detail__head"><div><span className="eyebrow">Página {current.page_number} · item {items.findIndex((item) => item.id === current.id) + 1} de {total}</span><h2>{current.sku_raw ?? `Item #${current.id}`}</h2></div><Selo tom={tone(current.confidence_level)}>{current.confidence_level ?? '—'}</Selo></header><section className="review-why"><b>Por que caiu na revisão</b><p>{reason(current)}. Nada entra no catálogo enquanto isso não for decidido por uma pessoa.</p></section><div className="review-comparison"><RawItem item={current} /><Detail item={current} finishes={finishes} onDecided={afterDecision} /></div></>}</main></div>
}
