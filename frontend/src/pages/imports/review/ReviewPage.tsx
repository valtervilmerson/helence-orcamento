import { useEffect, useState } from 'react'
import { listFinishes, type Finish, type FinishGroup } from '../../../api/catalog'
import {
  ImportsApiError,
  applyBatchCorrection,
  batchReviewExtractedItems,
  getImportItems,
  previewBatchCorrection,
  reviewExtractedItem,
  type BatchCorrectionPreviewOut,
  type BatchCorrectionScope,
  type ConfidenceLevel,
  type ExtractedItem,
  type ReviewStatus,
} from '../../../api/imports'

function describeError(err: unknown): string {
  if (err instanceof ImportsApiError) {
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

// Campos do item extraído elegíveis para correção (espelha
// CORRECTABLE_FIELDS em backend/app/imports/service.py).
const CORRECTABLE_FIELDS: { field: keyof ExtractedItem; label: string }[] = [
  { field: 'sku_raw', label: 'SKU' },
  { field: 'price_raw', label: 'Preço' },
  { field: 'finish_raw', label: 'Acabamento' },
  { field: 'dimension_raw', label: 'Dimensão' },
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

function ReviewStatusBadge({ status }: { status: ReviewStatus }) {
  return <span className={`badge ${REVIEW_STATUS_BADGE_CLASS[status]}`}>{status}</span>
}

const BATCH_SCOPE_OPTIONS: { value: BatchCorrectionScope; label: string }[] = [
  { value: 'page', label: 'Mesma página' },
  { value: 'page_profile', label: 'Mesmo perfil de página, em toda a importação' },
  { value: 'import', label: 'Toda a importação' },
]

// Vocabulário fechado de acabamentos (docs/04, seção 4, capacidade 5):
// sentinela usado no combo para abrir o sub-formulário de cadastro.
const NEW_FINISH_OPTION = '__new__'

const FINISH_GROUP_OPTIONS: { value: FinishGroup; label: string }[] = [
  { value: 'madeirado', label: 'Madeirado' },
  { value: 'metalico', label: 'Metálico' },
  { value: 'pe_estrutura', label: 'Pé/Estrutura' },
  { value: 'outro', label: 'Outro' },
]

const CONFIDENCE_BADGE_CLASS: Record<ConfidenceLevel, string> = {
  alta: 'badge-success',
  media: 'badge-warning',
  baixa: 'badge-danger',
}

function ConfidenceBadge({ level }: { level: ConfidenceLevel | null }) {
  if (!level) return <span>—</span>
  const label = level === 'alta' ? 'ALTA' : level === 'media' ? 'MÉDIA' : 'BAIXA'
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
    // eslint-disable-next-line react-hooks/set-state-in-effect -- carrega pré-visualização ao abrir/trocar escopo
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
        <h3>Aplicar correção em lote — {fieldLabel}</h3>

        {preview && (
          <p>
            Você corrigiu de <strong>{preview.previous_value ?? '—'}</strong> para{' '}
            <strong>{preview.corrected_value}</strong>. Deseja aplicar a mesma correção a outros
            itens com o valor original <strong>{preview.previous_value ?? '—'}</strong>?
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

        {loading && <p>Carregando pré-visualização…</p>}

        {preview && !loading && (
          <>
            <p>
              {preview.eligible_count} item(ns) elegível(eis) para correção
              {preview.already_decided_count > 0 && (
                <>
                  {' '}
                  — {preview.already_decided_count} item(ns) já com decisão própria não serão
                  alterados.
                </>
              )}
            </p>

            {preview.candidates.length > 0 && (
              <table>
                <thead>
                  <tr>
                    <th>Item</th>
                    <th>Pág.</th>
                    <th>Conf.</th>
                    <th>Novo valor</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.candidates.map((c) => (
                    <tr key={c.id}>
                      <td>#{c.id}</td>
                      <td>{c.page_number}</td>
                      <td>
                        <ConfidenceBadge level={c.confidence_level} />
                      </td>
                      <td>{c.corrected_value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        )}

        <p>
          <label>
            Observações (opcional):{' '}
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

// Combo de acabamento restrito ao vocabulário fechado de `finishes`
// (docs/04, seção 4, capacidade 5), com opção de cadastrar um novo
// acabamento — fica marcado para atenção do Aprovador na tela 5.
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
  const names = Array.from(new Set(finishes.map((f) => f.name))).sort((a, b) =>
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
        <option value={NEW_FINISH_OPTION}>Não está na lista — cadastrar novo acabamento</option>
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
            Este acabamento será marcado para atenção do Aprovador antes da publicação.
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

  async function handleApprove() {
    setError(null)

    if (field === 'finish_raw' && finishMode === 'new' && !newFinishName.trim()) {
      setError('Informe o nome do novo acabamento.')
      return
    }

    setSubmitting(true)
    try {
      if (field) {
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
        const corrected = CORRECTABLE_FIELDS.find((f) => f.field === field)
        setBatchPrompt({ field, label: corrected?.label ?? field })
        setField('')
        setFinishMode('existing')
        setNewFinishName('')
      } else {
        await reviewExtractedItem(item.id, { decision: 'aprovado', notes: notes || undefined })
      }
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
      setError('Justificativa é obrigatória para rejeitar um item.')
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

  function startCorrection(fieldName: string) {
    setField(fieldName)
    setCorrectedValue((item[fieldName as keyof ExtractedItem] as string | null) ?? '')
    setFinishMode('existing')
    setNewFinishName('')
    setNewFinishGroup('madeirado')
  }

  function cancelCorrection() {
    setField('')
    setFinishMode('existing')
    setNewFinishName('')
  }

  return (
    <section style={{ marginTop: 'var(--space-4)' }}>
      <h3>
        Item #{item.id} — pág. {item.page_number}{' '}
        <ConfidenceBadge level={item.confidence_level} />
      </h3>

      <p>
        <strong>Linha de origem:</strong> {item.source_text ?? '—'}
      </p>

      <table>
        <tbody>
          <tr>
            <td>Família</td>
            <td>{item.family_raw ?? '—'}</td>
          </tr>
          <tr>
            <td>Contexto</td>
            <td>{item.product_context_raw ?? '—'}</td>
          </tr>
          <tr>
            <td>Descrição</td>
            <td>{item.description_raw ?? '—'}</td>
          </tr>
          {CORRECTABLE_FIELDS.map(({ field: f, label }) => (
            <tr key={f}>
              <td>{label}</td>
              <td>
                {field === f ? (
                  f === 'finish_raw' ? (
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
                  (item[f] as string | null) ?? '—'
                )}
              </td>
              <td>
                {field === f ? (
                  <button type="button" className="secondary" onClick={cancelCorrection}>
                    Desfazer
                  </button>
                ) : (
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => startCorrection(f)}
                    disabled={isFinal}
                  >
                    ✎ Corrigir
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <p>
        <label>
          Justificativa {field || 'obrigatória ao rejeitar'}:{' '}
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
          <em>Decisão final registrada: {item.review_status}.</em>
        </p>
      ) : (
        <p className="action-group">
          <button type="button" className="danger" onClick={() => void handleReject()} disabled={submitting}>
            Rejeitar
          </button>
          <button type="button" onClick={() => void handleApprove()} disabled={submitting}>
            {field ? 'Salvar correção e aprovar' : '✓ Aprovar'}
          </button>
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

export function ReviewPage({ importId, onBack }: { importId: number; onBack: () => void }) {
  const [items, setItems] = useState<ExtractedItem[]>([])
  const [total, setTotal] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [finishes, setFinishes] = useState<Finish[]>([])

  const [reviewStatus, setReviewStatus] = useState<ReviewStatus | ''>('pendente')
  const [confidenceLevel, setConfidenceLevel] = useState<ConfidenceLevel | ''>('')

  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [bulkNotes, setBulkNotes] = useState('')
  const [bulkError, setBulkError] = useState<string | null>(null)
  const [bulkResult, setBulkResult] = useState<string | null>(null)
  const [bulkSubmitting, setBulkSubmitting] = useState(false)

  async function reload() {
    try {
      const result = await getImportItems(importId, {
        review_status: reviewStatus || undefined,
        confidence_level: confidenceLevel || undefined,
        page_size: 50,
      })
      setItems(result.items)
      setTotal(result.total)
      setError(null)
    } catch (err) {
      setError(describeError(err))
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- carrega itens ao montar/filtrar
    void reload()
    setSelectedIds(new Set())
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload é recriada a cada render
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
      setBulkError('Justificativa é obrigatória para rejeitar itens em lote.')
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
        const failures = out.results.filter((r) => !r.success)
        setBulkError(
          `${out.failed_count} de ${out.requested_count} itens não puderam ser atualizados: ` +
            failures.map((f) => `#${f.item_id} (${f.error_code})`).join(', '),
        )
      } else {
        setBulkResult(`${out.succeeded_count} item(ns) atualizado(s).`)
      }
      setSelectedIds(new Set())
      setBulkNotes('')
      await reload()
    } catch (err) {
      setBulkError(describeError(err))
    } finally {
      setBulkSubmitting(false)
    }
  }

  return (
    <div>
      <h1>Revisão — importação {importId}</h1>
      <section>
      <button type="button" className="secondary" onClick={onBack}>
        ← Voltar para importações
      </button>
      <ErrorMessageBlock error={error} />

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
          Confiança:{' '}
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
              <th>Pág.</th>
              <th>Componente</th>
              <th>Dimensão</th>
              <th>Acabamento</th>
              <th>SKU</th>
              <th>Preço</th>
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
                <td>{item.component_type_raw ?? '—'}</td>
                <td>{item.dimension_raw ?? '—'}</td>
                <td>{item.finish_raw ?? '—'}</td>
                <td>{item.sku_raw ?? '—'}</td>
                <td>{item.price_raw ?? '—'}</td>
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

      {selectedIds.size > 0 && (
        <div
          className="action-group"
          style={{ borderTop: '1px solid var(--color-border)', paddingTop: 'var(--space-3)', marginTop: 'var(--space-3)' }}
        >
          <strong>{selectedIds.size} selecionado(s)</strong>
          <label>
            Justificativa (obrigatória ao rejeitar):{' '}
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
          onDecided={() => void reload()}
        />
      )}
      </section>
    </div>
  )
}

function ErrorMessageBlock({ error }: { error: string | null }) {
  if (!error) return null
  return <p className="feedback-error">{error}</p>
}
