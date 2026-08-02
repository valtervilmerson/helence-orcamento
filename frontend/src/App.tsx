import { useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { getHealth } from './api/client'
import { useAuth } from './context/useAuth'
import { AppShell } from './layout/AppShell'
import { CatalogLayout } from './pages/catalog/CatalogLayout'
import { CatalogAdminPage } from './pages/catalog/CatalogAdminPage'
import { ConsultaPage } from './pages/catalog/consulta/ConsultaPage'
import { LoginPage } from './pages/auth/LoginPage'
import { ImportsPage } from './pages/imports/upload/ImportsPage'
import { ImportReviewRoute } from './pages/imports/review/ImportReviewRoute'
import { SettingsPage } from './pages/settings/SettingsPage'
import { PainelPage } from './pages/painel/PainelPage'
import { OrcamentosPage } from './pages/orcamentos/OrcamentosPage'
import { EditorConditionsPage, EditorLayout } from './pages/orcamentos/editor/EditorPage'
import { EditorItemsWithComposition } from './pages/orcamentos/editor/EditorItemsWithComposition'
import { RedesignReviewPage } from './pages/orcamentos/editor/EditorReviewPage'
import { DocumentoPage } from './pages/orcamentos/DocumentoPage'

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
        <Route index element={<PainelPage />} />
        <Route path="orcamentos" element={<OrcamentosPage />} />
        <Route path="orcamentos/:id" element={<EditorLayout />}>
          <Route index element={<Navigate to="itens" replace />} />
          <Route path="itens" element={<EditorItemsWithComposition />} />
          <Route path="condicoes" element={<EditorConditionsPage />} />
          <Route path="revisao" element={<RedesignReviewPage />} />
        </Route>
        <Route path="orcamentos/:id/documento" element={<DocumentoPage />} />
        <Route path="catalogo/admin" element={<CatalogLayout />}>
          <Route index element={<CatalogAdminPage />} />
        </Route>
        <Route path="catalogo" element={<ConsultaPage />} />
        <Route path="importacoes" element={<ImportsPage />} />
        <Route path="importacoes/:id/revisao" element={<ImportReviewRoute />} />
        <Route path="ajustes" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export default App
