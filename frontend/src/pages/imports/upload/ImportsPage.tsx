import { useEffect, useState } from 'react'
import {
  ImportsApiError,
  listImports,
  uploadImport,
  type ImportListItem,
} from '../../../api/imports'

function ErrorMessage({ error }: { error: string | null }) {
  if (!error) return null
  return <p style={{ color: 'crimson' }}>{error}</p>
}

function describeError(err: unknown): string {
  if (err instanceof ImportsApiError) {
    return `${err.code}: ${err.message}`
  }
  return String(err)
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
      {success && <p style={{ color: 'green' }}>{success}</p>}
    </section>
  )
}

export function ImportsPage() {
  const [imports, setImports] = useState<ImportListItem[]>([])
  const [error, setError] = useState<string | null>(null)

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

  return (
    <div>
      <h1>Importações</h1>
      <ErrorMessage error={error} />

      <UploadForm onUploaded={() => void reload()} />

      <section>
        <h2>Arquivos enviados</h2>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Arquivo</th>
              <th>Status</th>
              <th>Páginas</th>
              <th>Enviado em</th>
            </tr>
          </thead>
          <tbody>
            {imports.map((item) => (
              <tr key={item.id}>
                <td>{item.id}</td>
                <td>{item.original_filename ?? '—'}</td>
                <td>{item.status}</td>
                <td>{item.page_count ?? '—'}</td>
                <td>{item.imported_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  )
}
