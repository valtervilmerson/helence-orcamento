import {
  CatalogApiError,
  type Dimension,
  type Finish,
  type Product,
  type ProductComponentType,
  type ProductFamily,
} from '../../api/catalog'

export function describeError(err: unknown): string {
  if (err instanceof CatalogApiError) {
    return `${err.code}: ${err.message}`
  }
  return String(err)
}

export interface CatalogContextValue {
  families: ProductFamily[]
  dimensions: Dimension[]
  finishes: Finish[]
  componentTypes: ProductComponentType[]
  products: Product[]
  reload: () => Promise<void>
}
