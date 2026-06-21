import { useContext, useEffect } from 'react'
import {
  PageHeaderSetterContext,
  PageHeaderValueContext,
  type PageHeaderValue,
} from './pageHeaderContext'

// Registra o título/breadcrumb/ações da página atual na topbar do AppShell.
// Chamar uma vez por página, próximo ao topo do componente.
export function usePageHeader(value: PageHeaderValue) {
  const setHeader = useContext(PageHeaderSetterContext)
  useEffect(() => {
    setHeader(value)
    return () => setHeader(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- value.actions é um nó React recriado a cada render; reaplicar é barato e intencional
  }, [value.title, value.narrow, JSON.stringify(value.breadcrumb), value.actions])
}

export function useCurrentPageHeader() {
  return useContext(PageHeaderValueContext)
}
