import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CatalogApiError } from '../../../api/catalog'
import { deleteImport, type ImportJsonIn, ImportsApiError, listImports, processImport, publishImport, uploadImportJson, type ImportListItem } from '../../../api/imports'
import { Botao, Card, ConfirmDialog, Esqueleto, Selo, Vazio } from '../../../components/ui'
import { useAuth } from '../../../context/useAuth'
import { usePageHeader } from '../../../layout/usePageHeader'

function describeError(err: unknown): string {
  if (err instanceof ImportsApiError || err instanceof CatalogApiError) {
    const details = err.details ? Object.entries(err.details).map(([key, value]) => `${key}: ${String(value)}`).join(' · ') : ''
    return details ? `${err.message}: ${details}` : err.message
  }
  return 'Não foi possível concluir esta ação.'
}

function formatDate(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.valueOf()) ? value : new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }).format(date)
}

function statusMeta(item: ImportListItem): { label: string; tom: 'ok' | 'atencao' | 'erro' | 'neutro' } {
  if (item.status === 'erro') return { label: 'Erro no arquivo', tom: 'erro' }
  if (item.status === 'recebido' || item.status === 'processando') return { label: 'Processando', tom: 'atencao' }
  if (item.items_blocking_publication > 0) return { label: 'Em revisão', tom: 'atencao' }
  return { label: 'Pronta para publicar', tom: 'ok' }
}

function UploadCard({ onUploaded }: { onUploaded: () => void }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const selectFile = (candidate: File | undefined) => {
    setError(''); setSuccess('')
    if (!candidate) return
    if (!candidate.name.toLowerCase().endsWith('.json')) { setFile(null); setError('Envie apenas o JSON estruturado gerado a partir da planilha.'); return }
    setFile(candidate)
  }
  const submit = async () => {
    if (!file) { setError('Escolha um arquivo JSON para continuar.'); return }
    setSending(true); setError(''); setSuccess('')
    try {
      let payload: ImportJsonIn
      try { payload = JSON.parse(await file.text()) as ImportJsonIn } catch { setError('O arquivo não contém um JSON válido.'); return }
      const result = await uploadImportJson(payload, file.name)
      setSuccess(`${result.items_total} itens recebidos; ${result.items_pending_review} aguardam revisão.`)
      setFile(null); if (inputRef.current) inputRef.current.value = ''
      onUploaded()
    } catch (err) { setError(describeError(err)) } finally { setSending(false) }
  }

  return <Card className={`imports-upload ${dragging ? 'is-dragging' : ''}`}>
    <div className="imports-upload__icon">↑</div><strong>Solte o JSON da tabela aqui</strong><p>Gerado pelo agente de extração a partir das planilhas do fabricante.</p>
    <input ref={inputRef} type="file" accept=".json,application/json" onChange={(event) => selectFile(event.target.files?.[0])} onDragEnter={() => setDragging(true)} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); selectFile(event.dataTransfer.files[0]) }} />
    <div className="imports-upload__actions"><Botao variante="secundario" onClick={() => inputRef.current?.click()}>Escolher arquivo</Botao>{file && <Botao disabled={sending} onClick={() => void submit()}>{sending ? 'Processando itens…' : 'Enviar JSON'}</Botao>}</div>
    {file && <small className="mono">{file.name}</small>}{sending && <div className="progress"><div className="progress__fill imports-upload__progress" /></div>}{error && <p className="feedback-error">{error}</p>}{success && <p className="feedback-success">{success}</p>}
  </Card>
}

function ReviewPriority({ item, canPublish, publishing, onReview, onPublish }: { item: ImportListItem | null; canPublish: boolean; publishing: boolean; onReview: () => void; onPublish: () => void }) {
  if (!item) return <Card className="imports-ready"><Selo tom="ok">Tudo em dia</Selo><h2>Nada aguardando revisão</h2><p>As importações concluídas podem seguir para publicação quando necessário.</p></Card>
  const decided = Math.max(0, item.items_extracted - item.items_blocking_publication)
  const progress = item.items_extracted ? Math.round((decided / item.items_extracted) * 100) : 0
  const blocked = item.items_blocking_publication > 0
  return <Card className={blocked ? 'imports-review-priority' : 'imports-ready'}>
    <header><div><h2>{blocked ? 'Fila de revisão' : 'Importação pronta'}</h2><span>{blocked ? `${item.items_blocking_publication} bloqueando publicação` : 'Nenhum item pendente'}</span></div><Selo tom={blocked ? 'atencao' : 'ok'}>{blocked ? 'atenção' : 'ok'}</Selo></header>
    <div className="progress"><div className="progress__fill" style={{ width: `${progress}%` }} /></div><p>{decided} de {item.items_extracted} itens decididos em <b>{item.original_filename ?? `importação #${item.id}`}</b>.</p>
    {blocked ? <Botao className="imports-review-priority__action" onClick={onReview}>Abrir fila de revisão · {item.items_blocking_publication}</Botao> : canPublish && <Botao className="imports-review-priority__action" disabled={publishing} onClick={onPublish}>{publishing ? 'Publicando…' : 'Publicar importação'}</Botao>}
  </Card>
}

export function ImportsPage() {
  const { user } = useAuth(); const navigate = useNavigate()
  const canUpload = user?.role === 'importador' || user?.role === 'admin'
  const canReview = user?.role === 'importador' || user?.role === 'revisor' || user?.role === 'admin'
  const canPublish = user?.role === 'admin'
  const [imports, setImports] = useState<ImportListItem[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState(''); const [publishingId, setPublishingId] = useState<number | null>(null); const [deleting, setDeleting] = useState<ImportListItem | null>(null); const [processingId, setProcessingId] = useState<number | null>(null)
  usePageHeader({ title: 'Importações', narrow: true })
  const reload = async () => { try { const result = await listImports({ page_size: 50 }); setImports(result.items); setError('') } catch (err) { setError(describeError(err)) } finally { setLoading(false) } }
  useEffect(() => { void reload() }, [])
  useEffect(() => { if (!imports.some((item) => item.status === 'processando')) return; const timer = window.setInterval(() => void reload(), 2000); return () => window.clearInterval(timer) }, [imports])
  const publish = async (item: ImportListItem) => { setPublishingId(item.id); setError(''); try { await publishImport(item.id); await reload() } catch (err) { setError(describeError(err)) } finally { setPublishingId(null) } }
  const remove = async () => { if (!deleting) return; setError(''); try { await deleteImport(deleting.id); setDeleting(null); await reload() } catch (err) { setError(describeError(err)) } }
  const processLegacy = async (id: number) => { setProcessingId(id); setError(''); try { await processImport(id); await reload() } catch (err) { setError(describeError(err)) } finally { setProcessingId(null) } }
  const priority = imports.find((item) => item.items_blocking_publication > 0) ?? imports.find((item) => item.status === 'concluido') ?? null

  return <div className="imports-page"><header className="imports-page__head"><span className="eyebrow">Catálogo & preços</span><h1>Importações</h1></header>{error && <p className="feedback-error">{error}</p>}
    <div className="imports-top">{canUpload ? <UploadCard onUploaded={() => void reload()} /> : <Card className="imports-upload"><strong>Importação restrita</strong><p>Seu perfil pode acompanhar a fila, mas não enviar tabelas.</p></Card>}<ReviewPriority item={priority} canPublish={canPublish} publishing={publishingId === priority?.id} onReview={() => priority && navigate(`/importacoes/${priority.id}/revisao`)} onPublish={() => priority && void publish(priority)} /></div>
    <Card title="Histórico de importações" className="imports-history">{loading ? <Esqueleto linhas={6} /> : imports.length === 0 ? <Vazio titulo="Nenhuma importação enviada" descricao="Envie o JSON estruturado da tabela para atualizar o catálogo." /> : <><div className="imports-history__head"><span>Arquivo</span><span>Tabela</span><span>Itens</span><span>Enviado</span><span>Situação</span><span /></div>{imports.map((item) => { const status = statusMeta(item); return <div className="imports-history__row" key={item.id}><span><b>{item.original_filename ?? `Importação #${item.id}`}</b><small>#{item.id}{item.page_count ? ` · ${item.page_count} páginas` : ''}</small></span><span className="mono">—</span><span className="mono">{item.items_extracted}</span><span>{formatDate(item.imported_at)}</span><span><Selo tom={status.tom}>{status.label}</Selo></span><span className="imports-row-actions">{item.status === 'recebido' && canUpload && <Botao tamanho="sm" variante="secundario" disabled={processingId === item.id} onClick={() => void processLegacy(item.id)}>{processingId === item.id ? 'Processando…' : 'Processar'}</Botao>}{item.status === 'concluido' && canReview && <Botao tamanho="sm" variante="secundario" onClick={() => navigate(`/importacoes/${item.id}/revisao`)}>Revisar</Botao>}{item.status === 'concluido' && canPublish && <Botao tamanho="sm" variante="secundario" disabled={item.items_blocking_publication > 0 || publishingId === item.id} onClick={() => void publish(item)}>{publishingId === item.id ? 'Publicando…' : 'Publicar'}</Botao>}{item.status !== 'processando' && canUpload && <Botao tamanho="sm" variante="fantasma" onClick={() => setDeleting(item)}>Excluir</Botao>}</span></div> })}</>}</Card>
    <ConfirmDialog aberta={Boolean(deleting)} titulo="Excluir importação?" descricao={deleting ? `“${deleting.original_filename ?? `Importação #${deleting.id}`}” será removida. Esta ação não pode ser desfeita.` : ''} confirmarLabel="Excluir" onConfirmar={() => void remove()} onFechar={() => setDeleting(null)} />
  </div>
}
