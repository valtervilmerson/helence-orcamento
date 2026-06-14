import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
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

const TABS: { to: string; label: string; end?: boolean }[] = [
  { to: '/catalogo', label: 'Visão geral', end: true },
  { to: '/catalogo/familias', label: 'Famílias' },
  { to: '/catalogo/produtos', label: 'Produtos-base' },
  { to: '/catalogo/tipos-componente', label: 'Tipos de componente' },
  { to: '/catalogo/dimensoes', label: 'Dimensões' },
  { to: '/catalogo/acabamentos', label: 'Acabamentos' },
  { to: '/catalogo/variacoes', label: 'Variações vendáveis' },
]

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

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- carga inicial do catálogo
    void reload()
  }, [])

  const context: CatalogContextValue = {
    families,
    dimensions,
    finishes,
    componentTypes,
    products,
    reload,
  }

  return (
    <div>
      <h1>Catálogo</h1>
      <p className="catalog-layout__intro">
        Cadastro e organização dos itens do catálogo: famílias, produtos-base, tipos de
        componente, dimensões, acabamentos e as variações vendáveis (com SKU e preço).
      </p>
      <ErrorMessage error={error} />
      <nav className="catalog-tabs">
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) => `catalog-tabs__item${isActive ? ' is-active' : ''}`}
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>
      {loading ? <p>Carregando catálogo…</p> : <Outlet context={context} />}
    </div>
  )
}
