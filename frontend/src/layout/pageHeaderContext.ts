import { createContext, type ReactNode } from 'react'

export interface BreadcrumbItem {
  label: string
  to?: string
}

export interface PageHeaderValue {
  title: string
  breadcrumb?: BreadcrumbItem[]
  actions?: ReactNode
  narrow?: boolean
}

export const PageHeaderSetterContext = createContext<(value: PageHeaderValue | null) => void>(
  () => {},
)
export const PageHeaderValueContext = createContext<PageHeaderValue | null>(null)
