import { useState, type ReactNode } from 'react'
import {
  PageHeaderSetterContext,
  PageHeaderValueContext,
  type PageHeaderValue,
} from './pageHeaderContext'

export function PageHeaderProvider({ children }: { children: ReactNode }) {
  const [header, setHeader] = useState<PageHeaderValue | null>(null)
  return (
    <PageHeaderSetterContext.Provider value={setHeader}>
      <PageHeaderValueContext.Provider value={header}>{children}</PageHeaderValueContext.Provider>
    </PageHeaderSetterContext.Provider>
  )
}
