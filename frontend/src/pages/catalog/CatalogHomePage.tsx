import { Link, useOutletContext } from 'react-router-dom'
import type { CatalogContextValue } from './catalogContext'

export function CatalogHomePage() {
  const ctx = useOutletContext<CatalogContextValue>()

  const cards: { to: string; label: string; description: string; count: number }[] = [
    {
      to: '/catalogo/familias',
      label: 'Famílias de produto',
      description: 'Agrupamentos de alto nível (ex.: Mesas de Reunião, Soluções Acústicas).',
      count: ctx.families.length,
    },
    {
      to: '/catalogo/produtos',
      label: 'Produtos-base',
      description: 'Produtos dentro de uma família, com uma dimensão associada.',
      count: ctx.products.length,
    },
    {
      to: '/catalogo/tipos-componente',
      label: 'Tipos de componente',
      description: 'Peças que compõem um produto (ex.: Tampo, Estrutura, Painel).',
      count: ctx.componentTypes.length,
    },
    {
      to: '/catalogo/dimensoes',
      label: 'Dimensões',
      description: 'Medidas (largura, profundidade, diâmetro, altura) reutilizadas pelos produtos.',
      count: ctx.dimensions.length,
    },
    {
      to: '/catalogo/acabamentos',
      label: 'Acabamentos',
      description: 'Cores e materiais de acabamento, agrupados por tipo.',
      count: ctx.finishes.length,
    },
    {
      to: '/catalogo/variacoes',
      label: 'Variações vendáveis',
      description: 'Combinações finais (produto + componente + dimensão + acabamento) com SKU e preço.',
      count: -1,
    },
  ]

  return (
    <div className="catalog-grid">
      {cards.map((card) => (
        <Link key={card.to} to={card.to} className="catalog-card">
          {card.count >= 0 && <span className="catalog-card__count">{card.count}</span>}
          <span className="catalog-card__label">{card.label}</span>
          <span className="catalog-card__description">{card.description}</span>
        </Link>
      ))}
    </div>
  )
}
