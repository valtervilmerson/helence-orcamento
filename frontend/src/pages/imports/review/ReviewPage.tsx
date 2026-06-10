import { useEffect, useState } from 'react'
import {
  ImportsApiError,
  applyBatchCorrection,
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

const BATCH_SCOPE_OPTIONS: { value: BatchCorrectionScope; label: string }[] = [
  { value: 'page', label: 'Mesma página' },
  { value: 'page_profile', label: 'Mesmo perfil de página, em toda a importação' },
  { value: 'import', label: 'Toda a importação' },
]

function ConfidenceBadge({ level }: { level: ConfidenceLevel | null }) {
  if (!level) return <span>—</span>
  const color = level === 'alta' ? 'green' : level === 'media' ? 'darkorange' : 'crimson'
  const label = level === 'alta' ? 'ALTA' : level === 'media' ? 'MÉDIA' : 'BAIXA'
  return <span style={{ color, fontWeight: 'bold' }}>{label}</span>
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

        {error && <p style={{ color: 'crimson' }}>{error}</p>}
        {result && <p>{result}</p>}

        <p>
          <button type="button" onClick={onClose} disabled={applying}>
            Fechar
          </button>{' '}
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

interface ItemDetailProps {
  item: ExtractedItem
  onDecided: () => void
}

function ItemDetail({ item, onDecided }: ItemDetailProps) {
  const [field, setField] = useState<string>('')
  const [correctedValue, setCorrectedValue] = useState('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [batchPrompt, setBatchPrompt] = useState<{ field: string; label: string } | null>(null)

  const isFinal = FINAL_STATUSES.includes(item.review_status)

  async function handleApprove() {
    setError(null)
    setSubmitting(true)
    try {
      if (field) {
        await reviewExtractedItem(item.id, {
          decision: 'corrigido',
          field,
          previous_value: (item[field as keyof ExtractedItem] as string | null) ?? null,
          corrected_value: correctedValue,
          notes: notes || undefined,
        })
        const corrected = CORRECTABLE_FIELDS.find((f) => f.field === field)
        setBatchPrompt({ field, label: corrected?.label ?? field })
        setField('')
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
  }

  return (
    <section style={{ border: '1px solid #ccc', padding: '1rem', marginTop: '1rem' }}>
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
                  <input
                    value={correctedValue}
                    onChange={(e) => setCorrectedValue(e.target.value)}
                  />
                ) : (
                  (item[f] as string | null) ?? '—'
                )}
              </td>
              <td>
                {field === f ? (
                  <button type="button" onClick={() => setField('')}>
                    Desfazer
                  </button>
                ) : (
                  <button type="button" onClick={() => startCorrection(f)} disabled={isFinal}>
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

      {error && <p style={{ color: 'crimson' }}>{error}</p>}

      {isFinal ? (
        <p>
          <em>Decisão final registrada: {item.review_status}.</em>
        </p>
      ) : (
        <p>
          <button type="button" onClick={() => void handleReject()} disabled={submitting}>
            Rejeitar
          </button>{' '}
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

  const [reviewStatus, setReviewStatus] = useState<ReviewStatus | ''>('pendente')
  const [confidenceLevel, setConfidenceLevel] = useState<ConfidenceLevel | ''>('')

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
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload é recriada a cada render
  }, [importId, reviewStatus, confidenceLevel])

  const selectedItem = items.find((item) => item.id === selectedId) ?? null

  return (
    <section>
      <h2>Revisão — importação {importId}</h2>
      <button type="button" onClick={onBack}>
        ← Voltar para importações
      </button>
      <ErrorMessageBlock error={error} />

      <p>
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
        </select>{' '}
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
      </p>

      <p>{total} itens encontrados.</p>

      {items.length === 0 ? (
        <p>Nenhum item encontrado com esses filtros.</p>
      ) : (
        <table>
          <thead>
            <tr>
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
                  <ConfidenceBadge level={item.confidence_level} />
                </td>
                <td>{item.page_number}</td>
                <td>{item.component_type_raw ?? '—'}</td>
                <td>{item.dimension_raw ?? '—'}</td>
                <td>{item.finish_raw ?? '—'}</td>
                <td>{item.sku_raw ?? '—'}</td>
                <td>{item.price_raw ?? '—'}</td>
                <td>{item.review_status}</td>
                <td>
                  <button type="button" onClick={() => setSelectedId(item.id)}>
                    Revisar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {selectedItem && (
        <ItemDetail key={selectedItem.id} item={selectedItem} onDecided={() => void reload()} />
      )}
    </section>
  )
}

function ErrorMessageBlock({ error }: { error: string | null }) {
  if (!error) return null
  return <p style={{ color: 'crimson' }}>{error}</p>
}
