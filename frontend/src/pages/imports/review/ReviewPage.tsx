import { useEffect, useEffectEvent, useState } from 'react'
import { CatalogApiError } from '../../../api/catalog'
import { listFinishes, type Finish, type FinishGroup } from '../../../api/catalog'
import {
  ImportsApiError,
  applyBatchCorrection,
  batchReviewExtractedItems,
  getImportItems,
  getImportSummary,
  previewBatchCorrection,
  publishImport,
  reviewExtractedItem,
  type BatchCorrectionPreviewOut,
  type BatchCorrectionScope,
  type ConfidenceLevel,
  type ExtractedItem,
  type ImportListItem,
  type ReviewStatus,
} from '../../../api/imports'
import { useAuth } from '../../../context/useAuth'

function describeError(err: unknown): string {
  if (err instanceof ImportsApiError) {
    return `${err.code}: ${err.message}`
  }
  if (err instanceof CatalogApiError) {
    return `${err.code}: ${err.message}`
  }
  return String(err)
}

const REVIEW_STATUS_OPTIONS: ReviewStatus[] = [
  'pendente',
  'revisado',
  'aprovado',
  'rejeitado',
  'corrigido',
]

const CONFIDENCE_LEVEL_OPTIONS: ConfidenceLevel[] = ['alta', 'media', 'baixa']

const CORRECTABLE_FIELDS: { field: keyof ExtractedItem; label: string }[] = [
  { field: 'sku_raw', label: 'SKU' },
  { field: 'price_raw', label: 'Preco' },
  { field: 'finish_raw', label: 'Acabamento' },
  { field: 'dimension_raw', label: 'Dimensao' },
  { field: 'component_type_raw', label: 'Tipo de componente' },
]

const FINAL_STATUSES: ReviewStatus[] = ['aprovado', 'rejeitado']

const REVIEW_STATUS_BADGE_CLASS: Record<ReviewStatus, string> = {
  pendente: 'badge-neutral',
  revisado: 'badge-warning',
  aprovado: 'badge-success',
  rejeitado: 'badge-danger',
  corrigido: 'badge-warning',
}

const CONFIDENCE_BADGE_CLASS: Record<ConfidenceLevel, string> = {
  alta: 'badge-success',
  media: 'badge-warning',
  baixa: 'badge-danger',
}

const BATCH_SCOPE_OPTIONS: { value: BatchCorrectionScope; label: string }[] = [
  { value: 'page', label: 'Mesma pagina' },
  { value: 'page_profile', label: 'Mesmo perfil de pagina em toda a importacao' },
  { value: 'import', label: 'Toda a importacao' },
]

const NEW_FINISH_OPTION = '__new__'

const FINISH_GROUP_OPTIONS: { value: FinishGroup; label: string }[] = [
  { value: 'madeirado', label: 'Madeirado' },
  { value: 'metalico', label: 'Metalico' },
  { value: 'pe_estrutura', label: 'Pe/Estrutura' },
  { value: 'outro', label: 'Outro' },
]

function ReviewStatusBadge({ status }: { status: ReviewStatus }) {
  return <span className={`badge ${REVIEW_STATUS_BADGE_CLASS[status]}`}>{status}</span>
}

function ConfidenceBadge({ level }: { level: ConfidenceLevel | null }) {
  if (!level) return <span>-</span>
  const label = level === 'alta' ? 'ALTA' : level === 'media' ? 'MEDIA' : 'BAIXA'
  return <span className={`badge ${CONFIDENCE_BADGE_CLASS[level]}`}>{label}</span>
}

interface BatchCorrectionModalProps {
  itemId: number
  field: string
  fieldLabel: string
  onClose: () => void
  onApplied: () => void
}

function BatchCorrectionModal({
  itemId,
  field,
  fieldLabel,
  onClose,
  onApplied,
}: BatchCorrectionModalProps) {
  const [scope, setScope] = useState<BatchCorrectionScope>('page')
  const [preview, setPreview] = useState<BatchCorrectionPreviewOut | null>(null)
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [applying, setApplying] = useState(false)
  const [result, setResult] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    // eslint-disable-next-line react-hooks/set-state-in-effect -- open/scope change should refresh preview state
    setLoading(true)
    setError(null)
    setPreview(null)
    previewBatchCorrection(itemId, field, scope)
      .then((data) => {
        if (!cancelled) setPreview(data)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(describeError(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [itemId, field, scope])

  async function handleApply() {
    setApplying(true)
    setError(null)
    try {
      const out = await applyBatchCorrection(itemId, field, scope, notes || undefined)
      setResult(`${out.applied_count} item(ns) corrigido(s).`)
      onApplied()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setApplying(false)
    }
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.4)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
    >
      <div style={{ background: 'white', padding: '1.5rem', maxWidth: '32rem', width: '90%' }}>
        <h3>Aplicar correcao em lote - {fieldLabel}</h3>

        {preview && (
          <p>
            Voce corrigiu de <strong>{preview.previous_value ?? '-'}</strong> para{' '}
            <strong>{preview.corrected_value}</strong>. Deseja aplicar a mesma correcao a outros
            itens com o valor original <strong>{preview.previous_value ?? '-'}</strong>?
          </p>
        )}

        <p>
          <label>
            Escopo:{' '}
            <select
              value={scope}
              onChange={(e) => setScope(e.target.value as BatchCorrectionScope)}
              disabled={applying}
            >
              {BATCH_SCOPE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
        </p>

        {loading && <p>Carregando pre-visualizacao...</p>}

        {preview && !loading && (
          <>
            <p>
              {preview.eligible_count} item(ns) elegivel(eis) para correcao
              {preview.already_decided_count > 0 && (
                <>
                  {' '}
                  - {preview.already_decided_count} item(ns) ja com decisao propria nao serao
                  alterados.
                </>
              )}
            </p>

            {preview.candidates.length > 0 && (
              <table>
                <thead>
                  <tr>
                    <th>Item</th>
                    <th>Pag.</th>
                    <th>Conf.</th>
                    <th>Novo valor</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.candidates.map((candidate) => (
                    <tr key={candidate.id}>
                      <td>#{candidate.id}</td>
                      <td>{candidate.page_number}</td>
                      <td>
                        <ConfidenceBadge level={candidate.confidence_level} />
                      </td>
                      <td>{candidate.corrected_value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        )}

        <p>
          <label>
            Observacoes (opcional):{' '}
            <input
              style={{ width: '60%' }}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              disabled={applying}
            />
          </label>
        </p>

        {error && <p className="feedback-error">{error}</p>}
        {result && <p className="feedback-success">{result}</p>}

        <p className="action-group">
          <button type="button" className="secondary" onClick={onClose} disabled={applying}>
            Fechar
          </button>
          {!result && (
            <button
              type="button"
              onClick={() => void handleApply()}
              disabled={applying || loading || !preview || preview.eligible_count === 0}
            >
              Aplicar a {preview?.eligible_count ?? 0} item(ns)
            </button>
          )}
        </p>
      </div>
    </div>
  )
}

interface FinishFieldProps {
  finishes: Finish[]
  correctedValue: string
  onCorrectedValueChange: (value: string) => void
  mode: 'existing' | 'new'
  onModeChange: (mode: 'existing' | 'new') => void
  newFinishName: string
  onNewFinishNameChange: (value: string) => void
  newFinishGroup: FinishGroup
  onNewFinishGroupChange: (value: FinishGroup) => void
}

function FinishField({
  finishes,
  correctedValue,
  onCorrectedValueChange,
  mode,
  onModeChange,
  newFinishName,
  onNewFinishNameChange,
  newFinishGroup,
  onNewFinishGroupChange,
}: FinishFieldProps) {
  const names = Array.from(new Set(finishes.map((finish) => finish.name))).sort((a, b) =>
    a.localeCompare(b, 'pt-BR'),
  )
  if (correctedValue && !names.includes(correctedValue)) {
    names.unshift(correctedValue)
  }

  return (
    <>
      <select
        value={mode === 'new' ? NEW_FINISH_OPTION : correctedValue}
        onChange={(e) => {
          if (e.target.value === NEW_FINISH_OPTION) {
            onModeChange('new')
          } else {
            onModeChange('existing')
            onCorrectedValueChange(e.target.value)
          }
        }}
      >
        {names.map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
        <option value={NEW_FINISH_OPTION}>Nao esta na lista - cadastrar novo acabamento</option>
      </select>

      {mode === 'new' && (
        <div style={{ marginTop: '0.5rem' }}>
          <label>
            Nome do novo acabamento:{' '}
            <input
              value={newFinishName}
              onChange={(e) => onNewFinishNameChange(e.target.value)}
            />
          </label>{' '}
          <label>
            Grupo:{' '}
            <select
              value={newFinishGroup}
              onChange={(e) => onNewFinishGroupChange(e.target.value as FinishGroup)}
            >
              {FINISH_GROUP_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
          <p className="feedback-warning">
            Este acabamento precisara ser aprovado e cadastrado antes da publicacao.
          </p>
        </div>
      )}
    </>
  )
}

interface ItemDetailProps {
  item: ExtractedItem
  finishes: Finish[]
  onDecided: () => void
}

function ItemDetail({ item, finishes, onDecided }: ItemDetailProps) {
  const { user } = useAuth()
  const canReview = user?.role === 'revisor' || user?.role === 'admin'
  const [field, setField] = useState<string>('')
  const [correctedValue, setCorrectedValue] = useState('')
  const [finishMode, setFinishMode] = useState<'existing' | 'new'>('existing')
  const [newFinishName, setNewFinishName] = useState('')
  const [newFinishGroup, setNewFinishGroup] = useState<FinishGroup>('madeirado')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [batchPrompt, setBatchPrompt] = useState<{ field: string; label: string } | null>(null)

  const isFinal = FINAL_STATUSES.includes(item.review_status)

  function startCorrection(fieldName: string) {
    setField(fieldName)
    setCorrectedValue((item[fieldName as keyof ExtractedItem] as string | null) ?? '')
    setFinishMode('existing')
    setNewFinishName('')
    setNewFinishGroup('madeirado')
    setError(null)
  }

  function cancelCorrection() {
    setField('')
    setFinishMode('existing')
    setNewFinishName('')
    setError(null)
  }

  async function handleSaveCorrection() {
    setError(null)

    if (!field) {
      setError('Selecione um campo para corrigir.')
      return
    }

    if (field === 'finish_raw' && finishMode === 'new' && !newFinishName.trim()) {
      setError('Informe o nome do novo acabamento.')
      return
    }

    setSubmitting(true)
    try {
      const isNewFinish = field === 'finish_raw' && finishMode === 'new'
      await reviewExtractedItem(item.id, {
        decision: 'corrigido',
        field,
        previous_value: (item[field as keyof ExtractedItem] as string | null) ?? null,
        corrected_value: isNewFinish ? newFinishName.trim() : correctedValue,
        notes: notes || undefined,
        ...(isNewFinish
          ? { new_finish_name: newFinishName.trim(), new_finish_group: newFinishGroup }
          : {}),
      })
      const corrected = CORRECTABLE_FIELDS.find((entry) => entry.field === field)
      setBatchPrompt({ field, label: corrected?.label ?? field })
      setField('')
      setFinishMode('existing')
      setNewFinishName('')
      onDecided()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSubmitting(false)
    }
  }

  async function handleApprove() {
    setError(null)
    setSubmitting(true)
    try {
      await reviewExtractedItem(item.id, { decision: 'aprovado', notes: notes || undefined })
      onDecided()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSubmitting(false)
    }
  }

  async function handleReject() {
    setError(null)
    if (!notes) {
      setError('Justificativa e obrigatoria para rejeitar um item.')
      return
    }
    setSubmitting(true)
    try {
      await reviewExtractedItem(item.id, { decision: 'rejeitado', notes })
      onDecided()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section style={{ marginTop: 'var(--space-4)' }}>
      <h3>
        Item #{item.id} - pag. {item.page_number} <ConfidenceBadge level={item.confidence_level} />
      </h3>

      <p>
        <strong>Linha de origem:</strong> {item.source_text ?? '-'}
      </p>

      {item.review_status === 'corrigido' && !field && (
        <p className="feedback-warning">
          Correcao salva. Este item ainda precisa ser aprovado antes da publicacao.
        </p>
      )}

      <table>
        <tbody>
          <tr>
            <td>Familia</td>
            <td>{item.family_raw ?? '-'}</td>
          </tr>
          <tr>
            <td>Contexto</td>
            <td>{item.product_context_raw ?? '-'}</td>
          </tr>
          <tr>
            <td>Descricao</td>
            <td>{item.description_raw ?? '-'}</td>
          </tr>
          {CORRECTABLE_FIELDS.map(({ field: fieldName, label }) => (
            <tr key={fieldName}>
              <td>{label}</td>
              <td>
                {field === fieldName ? (
                  fieldName === 'finish_raw' ? (
                    <FinishField
                      finishes={finishes}
                      correctedValue={correctedValue}
                      onCorrectedValueChange={setCorrectedValue}
                      mode={finishMode}
                      onModeChange={setFinishMode}
                      newFinishName={newFinishName}
                      onNewFinishNameChange={setNewFinishName}
                      newFinishGroup={newFinishGroup}
                      onNewFinishGroupChange={setNewFinishGroup}
                    />
                  ) : (
                    <input
                      value={correctedValue}
                      onChange={(e) => setCorrectedValue(e.target.value)}
                    />
                  )
                ) : (
                  (item[fieldName] as string | null) ?? '-'
                )}
              </td>
              <td>
                {field === fieldName ? (
                  <button type="button" className="secondary" onClick={cancelCorrection}>
                    Desfazer
                  </button>
                ) : (
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => startCorrection(fieldName)}
                    disabled={isFinal || !canReview}
                  >
                    Corrigir
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <p>
        <label>
          Observacoes (obrigatorias ao rejeitar):{' '}
          <input
            style={{ width: '60%' }}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            disabled={isFinal}
          />
        </label>
      </p>

      {error && <p className="feedback-error">{error}</p>}

      {isFinal ? (
        <p>
          <em>Decisao final registrada: {item.review_status}.</em>
        </p>
      ) : !canReview ? (
        <p>
          <em>Somente Revisor ou Admin podem decidir sobre este item.</em>
        </p>
      ) : (
        <p className="action-group">
          <button
            type="button"
            className="danger"
            onClick={() => void handleReject()}
            disabled={submitting}
          >
            Rejeitar
          </button>
          {field ? (
            <button type="button" onClick={() => void handleSaveCorrection()} disabled={submitting}>
              Salvar correcao
            </button>
          ) : (
            <button type="button" onClick={() => void handleApprove()} disabled={submitting}>
              {item.review_status === 'corrigido' ? 'Aprovar item corrigido' : 'Aprovar'}
            </button>
          )}
        </p>
      )}

      {batchPrompt && (
        <BatchCorrectionModal
          itemId={item.id}
          field={batchPrompt.field}
          fieldLabel={batchPrompt.label}
          onClose={() => setBatchPrompt(null)}
          onApplied={onDecided}
        />
      )}
    </section>
  )
}

function ErrorMessageBlock({ error }: { error: string | null }) {
  if (!error) return null
  return <p className="feedback-error">{error}</p>
}

interface ImportSummaryPanelProps {
  summary: ImportListItem | null
  canPublishImports: boolean
  publishing: boolean
  publishError: string | null
  publishSuccess: string | null
  onPublish: () => void
}

function ImportSummaryPanel({
  summary,
  canPublishImports,
  publishing,
  publishError,
  publishSuccess,
  onPublish,
}: ImportSummaryPanelProps) {
  if (!summary) return null

  const canPublishNow = canPublishImports && summary.items_blocking_publication === 0

  return (
    <section style={{ marginTop: 'var(--space-3)' }}>
      <h2>Status da importacao</h2>
      <table>
        <tbody>
          <tr>
            <td>Arquivo</td>
            <td>{summary.original_filename ?? '-'}</td>
          </tr>
          <tr>
            <td>Itens extraidos</td>
            <td>{summary.items_extracted}</td>
          </tr>
          <tr>
            <td>Pendentes iniciais</td>
            <td>{summary.items_pending_review}</td>
          </tr>
          <tr>
            <td>Bloqueando publicacao</td>
            <td>{summary.items_blocking_publication}</td>
          </tr>
        </tbody>
      </table>

      {summary.items_blocking_publication > 0 && (
        <p className="feedback-warning">
          Ainda ha {summary.items_blocking_publication} item(ns) sem decisao final. Itens
          corrigidos precisam ser aprovados antes da publicacao.
        </p>
      )}

      {publishError && <ErrorMessageBlock error={publishError} />}
      {publishSuccess && <p className="feedback-success">{publishSuccess}</p>}

      {canPublishImports && (
        <p className="action-group">
          <button type="button" onClick={onPublish} disabled={!canPublishNow || publishing}>
            {publishing ? 'Publicando...' : 'Publicar importacao'}
          </button>
        </p>
      )}
    </section>
  )
}

export function ReviewPage({ importId, onBack }: { importId: number; onBack: () => void }) {
  const { user } = useAuth()
  const canReview = user?.role === 'revisor' || user?.role === 'admin'
  const canPublishImports = user?.role === 'admin'
  const [items, setItems] = useState<ExtractedItem[]>([])
  const [total, setTotal] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [finishes, setFinishes] = useState<Finish[]>([])
  const [importSummary, setImportSummary] = useState<ImportListItem | null>(null)
  const [publishError, setPublishError] = useState<string | null>(null)
  const [publishSuccess, setPublishSuccess] = useState<string | null>(null)
  const [publishing, setPublishing] = useState(false)

  const [reviewStatus, setReviewStatus] = useState<ReviewStatus | ''>('pendente')
  const [confidenceLevel, setConfidenceLevel] = useState<ConfidenceLevel | ''>('')

  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [bulkNotes, setBulkNotes] = useState('')
  const [bulkError, setBulkError] = useState<string | null>(null)
  const [bulkResult, setBulkResult] = useState<string | null>(null)
  const [bulkSubmitting, setBulkSubmitting] = useState(false)

  async function reloadSummary() {
    const summary = await getImportSummary(importId)
    setImportSummary(summary)
  }

  async function reloadItems() {
    const result = await getImportItems(importId, {
      review_status: reviewStatus || undefined,
      confidence_level: confidenceLevel || undefined,
      page_size: 50,
    })
    setItems(result.items)
    setTotal(result.total)
  }

  async function reloadAll() {
    try {
      await Promise.all([reloadSummary(), reloadItems()])
      setError(null)
    } catch (err) {
      setError(describeError(err))
    }
  }

  const handleFiltersChanged = useEffectEvent(() => {
    void reloadAll()
  })

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- filter changes should refresh review state
    handleFiltersChanged()
    setSelectedIds(new Set())
  }, [importId, reviewStatus, confidenceLevel])

  useEffect(() => {
    listFinishes()
      .then((data) => setFinishes(data))
      .catch(() => setFinishes([]))
  }, [])

  const selectedItem = items.find((item) => item.id === selectedId) ?? null

  function toggleSelected(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  function toggleSelectAll() {
    setSelectedIds((prev) =>
      prev.size === items.length ? new Set() : new Set(items.map((item) => item.id)),
    )
  }

  async function handleBulkDecision(decision: 'aprovado' | 'rejeitado') {
    setBulkError(null)
    setBulkResult(null)
    if (decision === 'rejeitado' && !bulkNotes) {
      setBulkError('Justificativa e obrigatoria para rejeitar itens em lote.')
      return
    }
    setBulkSubmitting(true)
    try {
      const out = await batchReviewExtractedItems(
        Array.from(selectedIds),
        decision,
        bulkNotes || undefined,
      )
      if (out.failed_count > 0) {
        const failures = out.results.filter((result) => !result.success)
        setBulkError(
          `${out.failed_count} de ${out.requested_count} itens nao puderam ser atualizados: ` +
            failures.map((failure) => `#${failure.item_id} (${failure.error_code})`).join(', '),
        )
      } else {
        setBulkResult(`${out.succeeded_count} item(ns) atualizado(s).`)
      }
      setSelectedIds(new Set())
      setBulkNotes('')
      await reloadAll()
    } catch (err) {
      setBulkError(describeError(err))
    } finally {
      setBulkSubmitting(false)
    }
  }

  async function handlePublish() {
    setPublishError(null)
    setPublishSuccess(null)
    setPublishing(true)
    try {
      const result = await publishImport(importId)
      setPublishSuccess(`Importacao publicada com ${result.items_published} item(ns).`)
      await reloadSummary()
    } catch (err) {
      setPublishError(describeError(err))
    } finally {
      setPublishing(false)
    }
  }

  return (
    <div>
      <h1>Revisao - importacao {importId}</h1>
      <section>
        <button type="button" className="secondary" onClick={onBack}>
          Voltar para importacoes
        </button>
        <ErrorMessageBlock error={error} />

        <ImportSummaryPanel
          summary={importSummary}
          canPublishImports={canPublishImports}
          publishing={publishing}
          publishError={publishError}
          publishSuccess={publishSuccess}
          onPublish={() => void handlePublish()}
        />

        <div className="action-group" style={{ marginTop: 'var(--space-3)' }}>
          <label>
            Status:{' '}
            <select
              value={reviewStatus}
              onChange={(e) => setReviewStatus(e.target.value as ReviewStatus | '')}
            >
              <option value="">Todos</option>
              {REVIEW_STATUS_OPTIONS.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>
          <label>
            Confianca:{' '}
            <select
              value={confidenceLevel}
              onChange={(e) => setConfidenceLevel(e.target.value as ConfidenceLevel | '')}
            >
              <option value="">Todas</option>
              {CONFIDENCE_LEVEL_OPTIONS.map((level) => (
                <option key={level} value={level}>
                  {level}
                </option>
              ))}
            </select>
          </label>
        </div>

        <p>{total} itens encontrados.</p>

        {items.length === 0 ? (
          <p>Nenhum item encontrado com esses filtros.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>
                  <input
                    type="checkbox"
                    checked={items.length > 0 && selectedIds.size === items.length}
                    onChange={toggleSelectAll}
                    aria-label="Selecionar todos os itens listados"
                  />
                </th>
                <th>Conf.</th>
                <th>Pag.</th>
                <th>Componente</th>
                <th>Dimensao</th>
                <th>Acabamento</th>
                <th>SKU</th>
                <th>Preco</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selectedIds.has(item.id)}
                      onChange={() => toggleSelected(item.id)}
                      aria-label={`Selecionar item #${item.id}`}
                    />
                  </td>
                  <td>
                    <ConfidenceBadge level={item.confidence_level} />
                  </td>
                  <td>{item.page_number}</td>
                  <td>{item.component_type_raw ?? '-'}</td>
                  <td>{item.dimension_raw ?? '-'}</td>
                  <td>{item.finish_raw ?? '-'}</td>
                  <td>{item.sku_raw ?? '-'}</td>
                  <td>{item.price_raw ?? '-'}</td>
                  <td>
                    <ReviewStatusBadge status={item.review_status} />
                  </td>
                  <td>
                    <button type="button" className="secondary" onClick={() => setSelectedId(item.id)}>
                      Revisar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {selectedIds.size > 0 && canReview && (
          <div
            className="action-group"
            style={{
              borderTop: '1px solid var(--color-border)',
              paddingTop: 'var(--space-3)',
              marginTop: 'var(--space-3)',
            }}
          >
            <strong>{selectedIds.size} selecionado(s)</strong>
            <label>
              Observacoes (obrigatorias ao rejeitar):{' '}
              <input
                value={bulkNotes}
                onChange={(e) => setBulkNotes(e.target.value)}
                disabled={bulkSubmitting}
              />
            </label>
            <button
              type="button"
              onClick={() => void handleBulkDecision('aprovado')}
              disabled={bulkSubmitting}
            >
              Aprovar selecionados
            </button>
            <button
              type="button"
              className="danger"
              onClick={() => void handleBulkDecision('rejeitado')}
              disabled={bulkSubmitting}
            >
              Rejeitar selecionados
            </button>
            {bulkResult && <span className="feedback-success">{bulkResult}</span>}
          </div>
        )}
        {bulkError && <ErrorMessageBlock error={bulkError} />}

        {selectedItem && (
          <ItemDetail
            key={selectedItem.id}
            item={selectedItem}
            finishes={finishes}
            onDecided={() => void reloadAll()}
          />
        )}
      </section>
    </div>
  )
}
