import { useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'
import {
  type Dimension,
  type Finish,
  type Product,
  type ProductComponentType,
  type ProductFamily,
  listComponentTypes,
  listDimensions,
  listFamilies,
  listFinishes,
  listProducts,
} from '../../api/catalog'
import { ErrorMessage } from './shared'
import { describeError, type CatalogContextValue } from './catalogContext'
import './CatalogLayout.css'

export function CatalogLayout() {
  const [families, setFamilies] = useState<ProductFamily[]>([])
  const [dimensions, setDimensions] = useState<Dimension[]>([])
  const [finishes, setFinishes] = useState<Finish[]>([])
  const [componentTypes, setComponentTypes] = useState<ProductComponentType[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  async function reload() {
    try {
      const [familiesData, dimensionsData, finishesData, componentTypesData, productsData] =
        await Promise.all([
          listFamilies(),
          listDimensions(),
          listFinishes(),
          listComponentTypes(),
          listProducts(),
        ])
      setFamilies(familiesData)
      setDimensions(dimensionsData)
      setFinishes(finishesData)
      setComponentTypes(componentTypesData)
      setProducts(productsData)
      setError(null)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void reload() }, [])

  const context: CatalogContextValue = {
    families, dimensions, finishes, componentTypes, products, reload,
  }

  return <div><ErrorMessage error={error} />{loading ? <p>Carregando catálogo…</p> : <Outlet context={context} />}</div>
}
