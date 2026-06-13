import { NavLink, Outlet } from 'react-router-dom'
import './AppShell.css'

type ApiStatus = 'loading' | 'ok' | 'error'

const NAV_ITEMS = [
  { to: '/orcamentos', label: 'Orçamentos', icon: '\u{1F4CB}' },
  { to: '/catalogo', label: 'Catálogo', icon: '\u{1F4E6}' },
  { to: '/consulta', label: 'Consulta', icon: '\u{1F50D}' },
  { to: '/importacoes', label: 'Importações', icon: '\u{1F4E5}' },
]

function statusLabel(status: ApiStatus): string {
  if (status === 'loading') return 'Verificando API…'
  if (status === 'ok') return 'API conectada'
  return 'API indisponível'
}

export function AppShell({ apiStatus }: { apiStatus: ApiStatus }) {
  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="app-sidebar__brand">Helence Orçamento</div>
        <nav className="app-sidebar__nav">
          {NAV_ITEMS.map((item) => (
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
