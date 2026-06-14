import { useEffect, useState } from 'react'
import { CatalogApiError } from '../../../api/catalog'
import {
  type ImportJsonIn,
  ImportsApiError,
  listImports,
  processImport,
  publishImport,
  uploadImport,
  uploadImportJson,
  type ImportListItem,
} from '../../../api/imports'
import { useAuth } from '../../../context/useAuth'
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
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setSuccess(null)

    if (!file) {
      setError('Selecione um arquivo PDF ou JSON.')
      return
    }

    try {
      if (isJsonFile(file)) {
        let payload: ImportJsonIn
        try {
          payload = JSON.parse(await file.text()) as ImportJsonIn
        } catch {
          setError('O arquivo JSON esta invalido.')
          return
        }

        const result = await uploadImportJson(payload, file.name)
        setSuccess(
          `JSON "${file.name}" importado (id ${result.imported_file_id}, ${result.items_total} item(ns), ${result.items_pending_review} pendente(s) para revisao).`,
        )
      } else if (isPdfFile(file)) {
        const result = await uploadImport(file, notes || undefined)
        setSuccess(`Arquivo "${result.original_filename}" recebido (id ${result.id}).`)
      } else {
        setError('Formato nao suportado. Envie um PDF ou JSON.')
        return
      }

      setFile(null)
      setNotes('')
      onUploaded()
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <section>
      <h2>Enviar Arquivo</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="file"
          accept=".pdf,application/pdf,.json,application/json"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <input
          placeholder="Observacoes (opcional, usado apenas para PDF)"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
        <button type="submit">Enviar</button>
      </form>
      <p>Arquivos aceitos: PDF para extracao legada e JSON no contrato v1.0.</p>
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
      setPublishSuccess(`Importacao publicada com ${result.items_published} item(ns).`)
      await reload()
    } catch (err) {
      setPublishError(describeError(err))
    } finally {
      setPublishingImportId(null)
    }
  }

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

  return (
    <div>
      <h1>Importacoes</h1>
      <ErrorMessage error={error} />
      <ErrorMessage error={processingError} />
      <ErrorMessage error={publishError} />
      {publishSuccess && <p className="feedback-success">{publishSuccess}</p>}

      {canManageImports && <UploadForm onUploaded={() => void reload()} />}

      <section>
        <h2>Arquivos enviados</h2>
        {imports.length === 0 && <p>Nenhum arquivo enviado ainda.</p>}
        {imports.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Arquivo</th>
                <th>Status</th>
                <th>Itens</th>
                <th>Bloqueando publicacao</th>
                <th>Paginas</th>
                <th>Enviado em</th>
                <th>Acoes</th>
              </tr>
            </thead>
            <tbody>
              {imports.map((item) => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td>{item.original_filename ?? '-'}</td>
                  <td>
                    <ImportStatusBadge status={item.status} />
                  </td>
                  <td>{item.items_extracted}</td>
                  <td>{item.items_blocking_publication}</td>
                  <td>{item.page_count ?? '-'}</td>
                  <td>{item.imported_at}</td>
                  <td className="action-group">
                    {item.status === 'recebido' && canManageImports && (
                      <button type="button" onClick={() => void handleProcess(item.id)}>
                        Processar
                      </button>
                    )}
                    {item.status === 'concluido' && (
                      <button type="button" onClick={() => setReviewingImportId(item.id)}>
                        Revisar
                      </button>
                    )}
                    {item.status === 'concluido' && canPublishImports && (
                      <button
                        type="button"
                        onClick={() => void handlePublish(item)}
                        disabled={
                          publishingImportId === item.id || item.items_blocking_publication > 0
                        }
                      >
                        {publishingImportId === item.id ? 'Publicando...' : 'Publicar importacao'}
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
