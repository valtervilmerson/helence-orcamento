import { useEffect, useState } from 'react'
import { CatalogApiError } from '../../../api/catalog'
import {
  deleteImport,
  type ImportJsonIn,
  ImportsApiError,
  listImports,
  processImport,
  publishImport,
  uploadImportJson,
  type ImportListItem,
} from '../../../api/imports'
import { useAuth } from '../../../context/useAuth'
import { usePageHeader } from '../../../layout/usePageHeader'
import { ReviewPage } from '../review/ReviewPage'

function ErrorMessage({ error }: { error: string | null }) {
  if (!error) return null
  return <p className="feedback-error">{error}</p>
}

function describeError(err: unknown): string {
  if (err instanceof ImportsApiError) {
    return `${err.code}: ${err.message}`
  }
  if (err instanceof CatalogApiError) {
    return `${err.code}: ${err.message}`
  }
  return String(err)
}

function isJsonFile(file: File): boolean {
  return file.type === 'application/json' || file.name.toLowerCase().endsWith('.json')
}

function isPdfFile(file: File): boolean {
  return file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
}

const IMPORT_STATUS_BADGE_CLASS: Record<string, string> = {
  recebido: 'badge-neutral',
  processando: 'badge-warning',
  concluido: 'badge-success',
  erro: 'badge-danger',
}

function ImportStatusBadge({ status }: { status: string }) {
  return (
    <span className={`badge ${IMPORT_STATUS_BADGE_CLASS[status] ?? 'badge-neutral'}`}>
      {status}
    </span>
  )
}

function UploadForm({ onUploaded }: { onUploaded: () => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setSuccess(null)

    if (!file) {
      setError('Selecione um arquivo JSON.')
      return
    }

    if (isPdfFile(file)) {
      setError('Importação via PDF foi descontinuada. Envie o JSON gerado a partir da planilha.')
      return
    }

    if (!isJsonFile(file)) {
      setError('Formato não suportado. Envie um arquivo JSON.')
      return
    }

    try {
      let payload: ImportJsonIn
      try {
        payload = JSON.parse(await file.text()) as ImportJsonIn
      } catch {
        setError('O arquivo JSON está inválido.')
        return
      }

      const result = await uploadImportJson(payload, file.name)
      setSuccess(
        `JSON "${file.name}" importado (id ${result.imported_file_id}, ${result.items_total} item(ns), ${result.items_pending_review} pendente(s) para revisão).`,
      )

      setFile(null)
      onUploaded()
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <section>
      <h2>Enviar tabela de preço</h2>
      <p className="section-subtitle">
        JSON no contrato v1.0, gerado pelo agente de extração a partir da planilha. A
        importação por PDF foi descontinuada.
      </p>
      <div className="dropzone">
        <strong>{file ? file.name : 'Selecione o arquivo .json'}</strong>
        <span>O conteúdo é validado contra o contrato antes de gravar qualquer item</span>
        <input
          type="file"
          accept=".json,application/json"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          style={{ marginTop: 'var(--space-2)' }}
        />
      </div>
      <form onSubmit={handleSubmit} className="action-group" style={{ marginTop: 'var(--space-3)' }}>
        <button type="submit">Enviar</button>
      </form>
      <ErrorMessage error={error} />
      {success && <p className="feedback-success">{success}</p>}
    </section>
  )
}

export function ImportsPage() {
  const { user } = useAuth()
  const canManageImports = user?.role === 'importador' || user?.role === 'admin'
  const canPublishImports = user?.role === 'admin'
  const [imports, setImports] = useState<ImportListItem[]>([])
  const [error, setError] = useState<string | null>(null)
  const [processingError, setProcessingError] = useState<string | null>(null)
  const [publishError, setPublishError] = useState<string | null>(null)
  const [publishSuccess, setPublishSuccess] = useState<string | null>(null)
  const [publishingImportId, setPublishingImportId] = useState<number | null>(null)
  const [reviewingImportId, setReviewingImportId] = useState<number | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [deletingImportId, setDeletingImportId] = useState<number | null>(null)

  async function reload() {
    try {
      const result = await listImports()
      setImports(result.items)
      setError(null)
    } catch (err) {
      setError(describeError(err))
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial imports list load
    void reload()
  }, [])

  useEffect(() => {
    if (!imports.some((item) => item.status === 'processando')) {
      return
    }
    const timer = setInterval(() => void reload(), 2000)
    return () => clearInterval(timer)
  }, [imports])

  async function handleProcess(importId: number) {
    setProcessingError(null)
    try {
      await processImport(importId)
      await reload()
    } catch (err) {
      setProcessingError(describeError(err))
    }
  }

  async function handlePublish(item: ImportListItem) {
    setPublishError(null)
    setPublishSuccess(null)
    setPublishingImportId(item.id)
    try {
      const result = await publishImport(item.id)
      setPublishSuccess(`Importação publicada com ${result.items_published} item(ns).`)
      await reload()
    } catch (err) {
      setPublishError(describeError(err))
    } finally {
      setPublishingImportId(null)
    }
  }

  async function handleDelete(item: ImportListItem) {
    if (!window.confirm(`Excluir a importação "${item.original_filename ?? item.id}"?`)) {
      return
    }
    setDeleteError(null)
    setDeletingImportId(item.id)
    try {
      await deleteImport(item.id)
      await reload()
    } catch (err) {
      setDeleteError(describeError(err))
    } finally {
      setDeletingImportId(null)
    }
  }

  usePageHeader(
    reviewingImportId !== null
      ? {
          title: `Revisão da importação #${reviewingImportId}`,
          breadcrumb: [
            { label: 'Importações', to: '/importacoes' },
            { label: `#${reviewingImportId}` },
            { label: 'Revisão' },
          ],
          narrow: true,
        }
      : { title: 'Importações', narrow: true },
  )

  if (reviewingImportId !== null) {
    return (
      <ReviewPage
        importId={reviewingImportId}
        onBack={() => {
          setReviewingImportId(null)
          void reload()
        }}
      />
    )
  }

  const lastImport = imports.reduce<ImportListItem | null>(
    (latest, item) => (latest === null || item.id > latest.id ? item : latest),
    null,
  )
  const totalBlocking = imports.reduce((sum, item) => sum + item.items_blocking_publication, 0)

  return (
    <div>
      <ErrorMessage error={error} />
      <ErrorMessage error={processingError} />
      <ErrorMessage error={publishError} />
      <ErrorMessage error={deleteError} />
      {publishSuccess && <p className="feedback-success">{publishSuccess}</p>}

      {imports.length > 0 && (
        <div className="metric-row" style={{ marginBottom: 'var(--space-5)' }}>
          <div className="metric">
            <div className="metric__value">{lastImport?.items_extracted ?? 0}</div>
            <div className="metric__label">Itens na última importação</div>
          </div>
          <div className={`metric${totalBlocking > 0 ? ' metric--warning' : ''}`}>
            <div className="metric__value">{totalBlocking}</div>
            <div className="metric__label">Itens bloqueando publicação</div>
          </div>
          <div className="metric">
            <div className="metric__value">{imports.length}</div>
            <div className="metric__label">Importações enviadas</div>
          </div>
        </div>
      )}

      {canManageImports && <UploadForm onUploaded={() => void reload()} />}

      <section>
        <h2>Importações recentes</h2>
        {imports.length === 0 && <p>Nenhum arquivo enviado ainda.</p>}
        {imports.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Arquivo</th>
                <th>Status</th>
                <th>Itens</th>
                <th>Pendentes</th>
                <th>Enviado em</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {imports.map((item) => (
                <tr key={item.id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{item.original_filename ?? '-'}</div>
                    <div className="helper-text">
                      #{item.id}
                      {item.page_count != null ? ` · ${item.page_count} página(s)` : ''}
                    </div>
                  </td>
                  <td>
                    <ImportStatusBadge status={item.status} />
                  </td>
                  <td>{item.items_extracted}</td>
                  <td>
                    <span className={`badge ${item.items_blocking_publication > 0 ? 'badge-warning' : 'badge-success'}`}>
                      {item.items_blocking_publication} {item.items_blocking_publication === 1 ? 'pendente' : 'pendentes'}
                    </span>
                  </td>
                  <td>{item.imported_at}</td>
                  <td className="action-group">
                    {item.status === 'recebido' && canManageImports && (
                      <button type="button" onClick={() => void handleProcess(item.id)}>
                        Processar
                      </button>
                    )}
                    {item.status === 'concluido' && (
                      <button type="button" onClick={() => setReviewingImportId(item.id)}>
                        {item.items_blocking_publication > 0
                          ? `Revisar ${item.items_blocking_publication} itens`
                          : 'Revisar'}
                      </button>
                    )}
                    {item.status === 'concluido' && canPublishImports && (
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => void handlePublish(item)}
                        disabled={
                          publishingImportId === item.id || item.items_blocking_publication > 0
                        }
                        title={
                          item.items_blocking_publication > 0
                            ? 'Habilita quando não há itens pendentes'
                            : undefined
                        }
                      >
                        {publishingImportId === item.id ? 'Publicando...' : 'Publicar'}
                      </button>
                    )}
                    {item.status !== 'processando' && canManageImports && (
                      <button
                        type="button"
                        className="danger"
                        onClick={() => void handleDelete(item)}
                        disabled={deletingImportId === item.id}
                      >
                        {deletingImportId === item.id ? 'Excluindo...' : 'Excluir'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}
