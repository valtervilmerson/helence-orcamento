import { useEffect, useState } from 'react'
import { QuotesApiError } from '../../api/quotes'
import { getSettings, updateSettings, type AppSettings } from '../../api/settings'

function describeError(err: unknown): string {
  if (err instanceof QuotesApiError) return `${err.code}: ${err.message}`
  return String(err)
}

export function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [markupInput, setMarkupInput] = useState('')
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getSettings()
      .then((s) => {
        setSettings(s)
        setMarkupInput(s.global_markup_percent.toString())
      })
      .catch((err) => setError(describeError(err)))
  }, [])

  async function handleSave(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setSaved(false)
    try {
      const updated = await updateSettings({
        global_markup_percent: Number(markupInput) || 0,
      })
      setSettings(updated)
      setSaved(true)
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <div>
      <h1>Configurações</h1>

      <section>
        <h2>Markup de venda global</h2>
        <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-3)' }}>
          Percentual aplicado silenciosamente sobre o preço de custo em todos os orçamentos que não
          possuem override específico. Não é exibido ao cliente.
        </p>
        {settings !== null && (
          <form onSubmit={handleSave} className="action-group">
            <div className="form-field">
              <span className="form-field__label">% de venda global</span>
              <input
                type="number"
                min="0"
                step="0.01"
                style={{ width: '8rem' }}
                value={markupInput}
                onChange={(e) => { setMarkupInput(e.target.value); setSaved(false) }}
              />
            </div>
            <button type="submit">Salvar</button>
          </form>
        )}
        {saved && (
          <p className="feedback-success" style={{ marginTop: 'var(--space-2)' }}>
            Configurações salvas.
          </p>
        )}
        {error && <p className="feedback-error">{error}</p>}
      </section>
    </div>
  )
}
