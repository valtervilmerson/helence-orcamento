import { NavLink, Outlet } from 'react-router-dom'
import type { UserRole } from '../api/auth'
import { useAuth } from '../context/useAuth'
import './AppShell.css'

type ApiStatus = 'loading' | 'ok' | 'error'

const NAV_ITEMS: { to: string; label: string; icon: string; roles: UserRole[] }[] = [
  { to: '/orcamentos', label: 'Orçamentos', icon: '\u{1F4CB}', roles: ['vendedor', 'admin'] },
  { to: '/catalogo', label: 'Catálogo', icon: '\u{1F4E6}', roles: ['admin'] },
  {
    to: '/consulta',
    label: 'Consulta',
    icon: '\u{1F50D}',
    roles: ['admin', 'importador', 'revisor', 'vendedor', 'colaborador'],
  },
  {
    to: '/importacoes',
    label: 'Importações',
    icon: '\u{1F4E5}',
    roles: ['importador', 'revisor', 'admin'],
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

export function AppShell({ apiStatus }: { apiStatus: ApiStatus }) {
  const { user, logout } = useAuth()
  const navItems = NAV_ITEMS.filter((item) => !user || item.roles.includes(user.role))

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="app-sidebar__brand">Helence Orçamento</div>
        <nav className="app-sidebar__nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                isActive ? 'app-sidebar__link is-active' : 'app-sidebar__link'
              }
            >
              <span className="app-sidebar__icon" aria-hidden="true">
                {item.icon}
              </span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        {user && (
          <div className="app-sidebar__user">
            <div className="app-sidebar__user-info">
              <strong>{user.name}</strong>
              <span>{ROLE_LABELS[user.role]}</span>
            </div>
            <button type="button" className="secondary" onClick={() => void logout()}>
              Sair
            </button>
          </div>
        )}
        <div className="app-sidebar__status">
          <span
            className={`app-sidebar__status-dot ${
              apiStatus === 'ok'
                ? 'app-sidebar__status-dot--ok'
                : apiStatus === 'error'
                  ? 'app-sidebar__status-dot--error'
                  : ''
            }`}
            aria-hidden="true"
          />
          {statusLabel(apiStatus)}
        </div>
      </aside>
      <main className="app-main">
        <div className="app-main__content">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
