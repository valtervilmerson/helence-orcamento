import { useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { getHealth } from './api/client'
import { useAuth } from './context/useAuth'
import { AppShell } from './layout/AppShell'
import { CatalogPage } from './pages/catalog/CatalogPage'
import { ConsultaPage } from './pages/catalog/consulta/ConsultaPage'
import { LoginPage } from './pages/auth/LoginPage'
import { ImportsPage } from './pages/imports/upload/ImportsPage'
import { QuotesPage } from './pages/quotes/QuotesPage'

type ApiStatus = 'loading' | 'ok' | 'error'

function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>('loading')
  const { user, loading } = useAuth()

  useEffect(() => {
    getHealth()
      .then(() => setApiStatus('ok'))
      .catch(() => setApiStatus('error'))
  }, [])

  if (loading) {
    return null
  }

  if (!user) {
    return (
      <Routes>
        <Route path="*" element={<LoginPage />} />
      </Routes>
    )
  }

  return (
    <Routes>
      <Route path="/" element={<AppShell apiStatus={apiStatus} />}>
        <Route index element={<Navigate to="/orcamentos" replace />} />
        <Route path="orcamentos" element={<QuotesPage />} />
        <Route path="catalogo" element={<CatalogPage />} />
        <Route path="consulta" element={<ConsultaPage />} />
        <Route path="importacoes" element={<ImportsPage />} />
        <Route path="*" element={<Navigate to="/orcamentos" replace />} />
      </Route>
    </Routes>
  )
}

export default App
