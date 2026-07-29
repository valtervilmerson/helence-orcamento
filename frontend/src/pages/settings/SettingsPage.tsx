import { useEffect, useState } from 'react'
import { getSettings, updateSettings, type AppSettings } from '../../api/settings'
import { Botao, Card, Esqueleto } from '../../components/ui'

export function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  useEffect(() => { void getSettings().then(setSettings).catch((err) => setError(String(err))) }, [])
  if (!settings) return <div className="page">{error ? <p className="feedback-error">{error}</p> : <Esqueleto linhas={4} />}</div>
  async function save() { if (!settings) return; setSaving(true); setError(null); try { setSettings(await updateSettings(settings)) } catch (err) { setError(String(err)) } finally { setSaving(false) } }
  return <div className="page"><span className="eyebrow">Administração</span><h1>Ajustes</h1><div className="settings-grid"><Card title="Política comercial"><label>Margem padrão <input type="number" value={settings.global_markup_percent} onChange={(e) => setSettings({ ...settings, global_markup_percent: Number(e.target.value) })} /> %</label><label>Alçada de desconto <input type="number" value={settings.discount_limit_percent} onChange={(e) => setSettings({ ...settings, discount_limit_percent: Number(e.target.value) })} /> %</label><label>Validade padrão <input type="number" min="1" value={settings.default_validity_days} onChange={(e) => setSettings({ ...settings, default_validity_days: Number(e.target.value) })} /> dias</label><Botao disabled={saving} onClick={() => void save()}>{saving ? 'Salvando…' : 'Salvar alterações'}</Botao>{error && <p className="feedback-error">{error}</p>}</Card></div></div>
}
