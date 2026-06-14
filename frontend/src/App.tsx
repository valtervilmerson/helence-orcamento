import { useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { getHealth } from './api/client'
import { useAuth } from './context/useAuth'
import { AppShell } from './layout/AppShell'
import { CatalogHomePage } from './pages/catalog/CatalogHomePage'
import { CatalogLayout } from './pages/catalog/CatalogLayout'
import { ConsultaPage } from './pages/catalog/consulta/ConsultaPage'
import { ComponentTypesPage } from './pages/catalog/componentTypes/ComponentTypesPage'
import { DimensionsPage } from './pages/catalog/dimensions/DimensionsPage'
import { FamiliesPage } from './pages/catalog/families/FamiliesPage'
import { FinishesPage } from './pages/catalog/finishes/FinishesPage'
import { ProductsPage } from './pages/catalog/products/ProductsPage'
import { VariantsPage } from './pages/catalog/variants/VariantsPage'
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
        <Route path="catalogo" element={<CatalogLayout />}>
          <Route index element={<CatalogHomePage />} />
          <Route path="familias" element={<FamiliesPage />} />
          <Route path="produtos" element={<ProductsPage />} />
          <Route path="tipos-componente" element={<ComponentTypesPage />} />
          <Route path="dimensoes" element={<DimensionsPage />} />
          <Route path="acabamentos" element={<FinishesPage />} />
          <Route path="variacoes" element={<VariantsPage />} />
        </Route>
        <Route path="consulta" element={<ConsultaPage />} />
        <Route path="importacoes" element={<ImportsPage />} />
        <Route path="*" element={<Navigate to="/orcamentos" replace />} />
      </Route>
    </Routes>
  )
}

export default App
