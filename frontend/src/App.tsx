import { useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { getHealth } from './api/client'
import { AppShell } from './layout/AppShell'
import { CatalogPage } from './pages/catalog/CatalogPage'
import { ConsultaPage } from './pages/catalog/consulta/ConsultaPage'
import { ImportsPage } from './pages/imports/upload/ImportsPage'
import { QuotesPage } from './pages/quotes/QuotesPage'

type ApiStatus = 'loading' | 'ok' | 'error'

function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>('loading')

  useEffect(() => {
    getHealth()
      .then(() => setApiStatus('ok'))
      .catch(() => setApiStatus('error'))
  }, [])

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
