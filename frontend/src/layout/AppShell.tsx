import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { listImports } from '../api/imports'
import type { UserRole } from '../api/auth'
import { useAuth } from '../context/useAuth'
import { PageHeaderProvider } from './PageHeaderProvider'
import { useCurrentPageHeader } from './usePageHeader'
import './AppShell.css'

type ApiStatus = 'loading' | 'ok' | 'error'

const IMPORTS_BADGE_ROLES: UserRole[] = ['importador', 'revisor', 'admin']

const NAV_GROUPS: {
  title: string
  items: { to: string; label: string; roles: UserRole[]; badge?: 'imports-blocking' }[]
}[] = [
  {
    title: 'Vendas',
    items: [{ to: '/orcamentos', label: 'Orçamentos', roles: ['vendedor', 'admin'] }],
  },
  {
    title: 'Catálogo & Preços',
    items: [
      { to: '/catalogo', label: 'Catálogo', roles: ['admin'] },
      {
        to: '/consulta',
        label: 'Consulta',
        roles: ['admin', 'importador', 'revisor', 'vendedor', 'colaborador'],
      },
      {
        to: '/importacoes',
        label: 'Importações',
        roles: ['importador', 'revisor', 'admin'],
        badge: 'imports-blocking',
      },
    ],
  },
  {
    title: 'Gestão',
    items: [{ to: '/configuracoes', label: 'Configurações', roles: ['admin'] }],
  },
]

const ROLE_LABELS: Record<UserRole, string> = {
  admin: 'Admin',
  importador: 'Importador',
  revisor: 'Revisor',
  vendedor: 'Vendedor',
  colaborador: 'Colaborador',
}

function statusLabel(status: ApiStatus): string {
  if (status === 'loading') return 'Verificando API…'
  if (status === 'ok') return 'API conectada'
  return 'API indisponível'
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/)
  const first = parts[0]?.[0] ?? ''
  const last = parts.length > 1 ? parts[parts.length - 1][0] : ''
  return (first + last).toUpperCase()
}

// Contagem de itens bloqueando publicação, somada entre todas as importações
// — usada no badge de "Importações" do menu (nunca um valor fixo).
function useImportsBlockingCount(enabled: boolean): number {
  const [count, setCount] = useState(0)

  useEffect(() => {
    if (!enabled) return
    let cancelled = false
    async function load() {
      try {
        const result = await listImports({ page_size: 100 })
        if (!cancelled) {
          setCount(result.items.reduce((sum, item) => sum + item.items_blocking_publication, 0))
        }
      } catch {
        if (!cancelled) setCount(0)
      }
    }
    void load()
    const timer = setInterval(() => void load(), 30000)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [enabled])

  return count
}

function Topbar() {
  const header = useCurrentPageHeader()
  if (!header) return null
  return (
    <div className="app-topbar">
      <div className="app-topbar__titles">
        {header.breadcrumb && header.breadcrumb.length > 0 && (
          <div className="breadcrumb">
            {header.breadcrumb.map((item, index) => (
              <span key={`${item.label}-${index}`}>
                {item.to ? <NavLink to={item.to}>{item.label}</NavLink> : item.label}
                {index < header.breadcrumb!.length - 1 && (
                  <span className="breadcrumb__sep"> / </span>
                )}
              </span>
            ))}
          </div>
        )}
        <h1>{header.title}</h1>
      </div>
      <div className="app-topbar__spacer" />
      {header.actions}
    </div>
  )
}

function AppContent() {
  const header = useCurrentPageHeader()
  return (
    <div className={`app-content${header?.narrow ? ' app-content--narrow' : ''}`}>
      <Outlet />
    </div>
  )
}

export function AppShell({ apiStatus }: { apiStatus: ApiStatus }) {
  const { user, logout } = useAuth()
  const navGroups = NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => !user || item.roles.includes(user.role)),
  })).filter((group) => group.items.length > 0)

  const importsBadgeCount = useImportsBlockingCount(
    Boolean(user && IMPORTS_BADGE_ROLES.includes(user.role)),
  )

  return (
    <PageHeaderProvider>
      <div className="app">
        <aside className="app-nav">
          <div className="app-brand">
            <span className="app-brand__mark" aria-hidden="true" />
            <span>
              Helence
              <small>Orçamento</small>
            </span>
          </div>
          <div className="app-nav__scroll">
            {navGroups.map((group) => (
              <div className="nav-group" key={group.title}>
                <div className="nav-group__title">{group.title}</div>
                {group.items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) => `nav-link${isActive ? ' is-active' : ''}`}
                  >
                    {item.label}
                    {item.badge === 'imports-blocking' && importsBadgeCount > 0 && (
                      <span className="nav-link__count badge badge-warning">
                        {importsBadgeCount}
                      </span>
                    )}
                  </NavLink>
                ))}
              </div>
            ))}
          </div>
          {user && (
            <div className="app-user">
              <span className="app-user__avatar" aria-hidden="true">
                {initials(user.name)}
              </span>
              <span className="app-user__meta">
                <strong>{user.name}</strong>
                <span>{ROLE_LABELS[user.role]}</span>
              </span>
              <button type="button" className="secondary" onClick={() => void logout()}>
                Sair
              </button>
            </div>
          )}
          <div className="app-status">
            <span
              className={`app-status__dot ${
                apiStatus === 'ok' ? 'app-status__dot--ok' : apiStatus === 'error' ? 'app-status__dot--error' : ''
              }`}
              aria-hidden="true"
            />
            {statusLabel(apiStatus)}
          </div>
        </aside>
        <div className="app-main">
          <Topbar />
          <AppContent />
        </div>
      </div>
    </PageHeaderProvider>
  )
}
