import { useEffect, useState } from 'react'
import {
  ImportsApiError,
  listImports,
  processImport,
  uploadImport,
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
  return String(err)
}

const IMPORT_STATUS_BADGE_CLASS: Record<string, string> = {
  recebido: 'badge-neutral',
  processando: 'badge-warning',
  concluido: 'badge-success',
  erro: 'badge-danger',
}

function ImportStatusBadge({ status }: { status: string }) {
  return <span className={`badge ${IMPORT_STATUS_BADGE_CLASS[status] ?? 'badge-neutral'}`}>{status}</span>
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
      setError('Selecione um arquivo PDF.')
      return
    }
    try {
      const result = await uploadImport(file, notes || undefined)
      setSuccess(`Arquivo "${result.original_filename}" recebido (id ${result.id}).`)
      setFile(null)
      setNotes('')
      onUploaded()
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <section>
      <h2>Enviar PDF</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <input
          placeholder="Observações (opcional)"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
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
  const [imports, setImports] = useState<ImportListItem[]>([])
  const [error, setError] = useState<string | null>(null)
  const [processingError, setProcessingError] = useState<string | null>(null)
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
    // eslint-disable-next-line react-hooks/set-state-in-effect -- carga inicial da listagem de importações
    void reload()
  }, [])

  // Enquanto houver alguma importação em processamento, faz polling do
  // status (docs/06, seção 7 — polling simples no MVP).
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

  if (reviewingImportId !== null) {
    return <ReviewPage importId={reviewingImportId} onBack={() => setReviewingImportId(null)} />
  }

  return (
    <div>
      <h1>Importações</h1>
      <ErrorMessage error={error} />
      <ErrorMessage error={processingError} />

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
              <th>Páginas</th>
              <th>Enviado em</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {imports.map((item) => (
              <tr key={item.id}>
                <td>{item.id}</td>
                <td>{item.original_filename ?? '—'}</td>
                <td>
                  <ImportStatusBadge status={item.status} />
                </td>
                <td>{item.page_count ?? '—'}</td>
                <td>{item.imported_at}</td>
                <td>
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
