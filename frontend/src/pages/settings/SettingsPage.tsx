import { useEffect, useState } from 'react'
import { listUsers, type AuthUser } from '../../api/auth'
import { getSettings, updateSettings, type AppSettings } from '../../api/settings'
import { Botao, Card, Esqueleto, Selo } from '../../components/ui'
import { useAuth } from '../../context/useAuth'

type SettingKey = keyof AppSettings
const policies: { key: SettingKey; label: string; suffix: string; min: number; hint: string }[] = [
  { key: 'global_markup_percent', label: 'Margem padrão', suffix: '%', min: 0, hint: 'Aplicada aos orçamentos que usam a margem global.' },
  { key: 'discount_limit_percent', label: 'Alçada de desconto do vendedor', suffix: '%', min: 0, hint: 'Acima desse limite, a proposta precisa de aprovação.' },
  { key: 'default_validity_days', label: 'Validade padrão da proposta', suffix: 'dias', min: 1, hint: 'Preenchida automaticamente ao criar um orçamento.' },
]
const roleLabel: Record<AuthUser['role'], string> = { admin: 'Admin', importador: 'Importador', revisor: 'Revisor', vendedor: 'Vendedor', colaborador: 'Colaborador' }
const initials = (name: string) => name.split(' ').filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase()

export function SettingsPage() {
  const { user } = useAuth()
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [team, setTeam] = useState<AuthUser[]>([])
  const [error, setError] = useState('')
  const [editing, setEditing] = useState<SettingKey | null>(null)
  const [draft, setDraft] = useState('')
  const [saving, setSaving] = useState(false)
  useEffect(() => { if (user?.role !== 'admin') return; void Promise.all([getSettings(), listUsers()]).then(([appSettings, users]) => { setSettings(appSettings); setTeam(users); setError('') }).catch((err) => setError(err instanceof Error ? err.message : 'Não foi possível carregar os ajustes.')) }, [user?.role])
  const begin = (key: SettingKey) => { if (!settings) return; setEditing(key); setDraft(String(settings[key])) }
  const save = async (key: SettingKey, min: number) => { const value = Number(draft.replace(',', '.')); if (!Number.isFinite(value) || value < min) { setError(`Informe um valor igual ou maior que ${min}.`); return }; setSaving(true); setError(''); try { setSettings(await updateSettings({ [key]: value })); setEditing(null) } catch (err) { setError(err instanceof Error ? err.message : 'Não foi possível salvar o ajuste.') } finally { setSaving(false) } }
  if (user?.role !== 'admin') return <div className="page settings-page"><span className="eyebrow">Administração</span><h1>Ajustes</h1><p className="feedback-warning">Somente administradores podem alterar a política comercial.</p></div>
  if (!settings) return <div className="page settings-page">{error ? <p className="feedback-error">{error}</p> : <Esqueleto linhas={6} />}</div>
  return <div className="page settings-page"><header><span className="eyebrow">Administração · somente admin</span><h1>Ajustes</h1><p>Parâmetros usados na criação, aprovação e cálculo comercial dos orçamentos.</p></header>{error && <p className="feedback-error">{error}</p>}<div className="settings-redesign-grid"><Card title="Política comercial" className="settings-policy">{policies.map((policy) => <div className="settings-policy__row" key={policy.key}><div><b>{policy.label}</b><small>{policy.hint}</small></div>{editing === policy.key ? <div className="settings-policy__edit"><input type="number" min={policy.min} step={policy.suffix === '%' ? '0.1' : '1'} value={draft} onChange={(event) => setDraft(event.target.value)} autoFocus /><span>{policy.suffix}</span><Botao tamanho="sm" disabled={saving} onClick={() => void save(policy.key, policy.min)}>{saving ? 'Salvando…' : 'Salvar'}</Botao><Botao tamanho="sm" variante="fantasma" onClick={() => setEditing(null)}>Cancelar</Botao></div> : <button className="settings-policy__value mono" onClick={() => begin(policy.key)}>{settings[policy.key]} <span>{policy.suffix}</span><small>Editar</small></button>}</div>)}</Card><Card title="Equipe" className="settings-team">{team.map((member) => <div className="settings-member" key={member.id}><span className="settings-member__avatar">{initials(member.name)}</span><span><b>{member.name}</b><small>{member.email}</small></span><Selo tom={member.role === 'admin' ? 'marca' : 'neutro'}>{roleLabel[member.role]}</Selo></div>)}</Card></div></div>
}
