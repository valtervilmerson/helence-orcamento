import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { listImports } from '../api/imports'
import type { UserRole } from '../api/auth'
import { useAuth } from '../context/useAuth'
import './AppShell.css'

type ApiStatus = 'loading' | 'ok' | 'error'
const nav = [
  { to: '/', label: 'Painel', icon: '▦', roles: ['admin', 'importador', 'revisor', 'vendedor', 'colaborador'] },
  { to: '/orcamentos', label: 'Orçamentos', icon: '▤', roles: ['admin', 'vendedor'] },
  { to: '/catalogo', label: 'Catálogo', icon: '⌕', roles: ['admin', 'importador', 'revisor', 'vendedor', 'colaborador'] },
  { to: '/importacoes', label: 'Importar', icon: '↑', roles: ['admin', 'importador', 'revisor'] },
  { to: '/ajustes', label: 'Ajustes', icon: '⚙', roles: ['admin'] },
] as const

function initials(name: string) { return name.trim().split(/\s+/).map((part) => part[0]).slice(0, 2).join('').toUpperCase() }
function useBlockingImports(enabled: boolean) {
  const [count, setCount] = useState(0)
  useEffect(() => { if (!enabled) return; let dead = false; const load = () => listImports({ page_size: 100 }).then((r) => !dead && setCount(r.items.reduce((sum, item) => sum + item.items_blocking_publication, 0))).catch(() => !dead && setCount(0)); void load(); const timer = setInterval(load, 30000); return () => { dead = true; clearInterval(timer) } }, [enabled])
  return count
}

export function AppShell({ apiStatus }: { apiStatus: ApiStatus }) {
  const { user, logout } = useAuth()
  const imports = useBlockingImports(Boolean(user && ['admin', 'importador', 'revisor'].includes(user.role)))
  return <div className="app"><aside className="app-rail"><div className="rail-brand"><b>h</b><small>HELENCE</small></div><nav>{nav.filter((item) => user && (item.roles as readonly UserRole[]).includes(user.role)).map((item) => <NavLink key={item.to} to={item.to} end={item.to === '/'} className={({ isActive }) => `rail-link${isActive ? ' is-active' : ''}`}><span className="rail-icon">{item.icon}</span><span>{item.label}</span>{item.to === '/importacoes' && imports > 0 && <em>{imports}</em>}</NavLink>)}</nav><div className="rail-user">{user && <><button title="Sair" onClick={() => void logout()}>{initials(user.name)}</button><small>{user.name.split(' ')[0]}</small></>}</div></aside><main className="app-main"><Outlet /></main>{apiStatus === 'error' && <div className="offline">Sem conexão com o servidor. Suas alterações não estão sendo salvas.</div>}</div>
}
