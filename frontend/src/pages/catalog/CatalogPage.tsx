import { useEffect, useState } from 'react'
import {
  CatalogApiError,
  type ComponentVariant,
  type Dimension,
  type Finish,
  type PriceTable,
  type Product,
  type ProductComponentType,
  type ProductFamily,
  createComponent,
  createComponentType,
  createDimension,
  createFamily,
  createFinish,
  createProduct,
  deleteComponent,
  deleteComponentType,
  deleteDimension,
  deleteFamily,
  deleteFinish,
  deleteProduct,
  listComponentTypes,
  listDimensions,
  listFamilies,
  listFinishes,
  listPriceTables,
  listProducts,
  searchComponents,
} from '../../api/catalog'

function ErrorMessage({ error }: { error: string | null }) {
  if (!error) return null
  return <p style={{ color: 'crimson' }}>{error}</p>
}

function describeError(err: unknown): string {
  if (err instanceof CatalogApiError) {
    return `${err.code}: ${err.message}`
  }
  return String(err)
}

function FamiliesSection({
  families,
  onChange,
}: {
  families: ProductFamily[]
  onChange: () => void
}) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await createFamily({ name, description: description || null })
      setName('')
      setDescription('')
      onChange()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function handleDelete(id: number) {
    setError(null)
    try {
      await deleteFamily(id)
      onChange()
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <section>
      <h2>Famílias de produto</h2>
      <ul>
        {families.map((family) => (
          <li key={family.id}>
            #{family.id} — {family.name}
            {family.description ? ` (${family.description})` : ''}{' '}
            <button onClick={() => handleDelete(family.id)}>excluir</button>
          </li>
        ))}
      </ul>
      <form onSubmit={handleCreate}>
        <input placeholder="Nome" value={name} onChange={(e) => setName(e.target.value)} required />
        <input
          placeholder="Descrição (opcional)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <button type="submit">Adicionar família</button>
      </form>
      <ErrorMessage error={error} />
    </section>
  )
}

function DimensionsSection({
  dimensions,
  onChange,
}: {
  dimensions: Dimension[]
  onChange: () => void
}) {
  const [width, setWidth] = useState('')
  const [depth, setDepth] = useState('')
  const [diameter, setDiameter] = useState('')
  const [height, setHeight] = useState('')
  const [rawLabel, setRawLabel] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await createDimension({
        width_mm: width ? Number(width) : null,
        depth_mm: depth ? Number(depth) : null,
        diameter_mm: diameter ? Number(diameter) : null,
        height_mm: height ? Number(height) : null,
        raw_label: rawLabel || null,
      })
      setWidth('')
      setDepth('')
      setDiameter('')
      setHeight('')
      setRawLabel('')
      onChange()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function handleDelete(id: number) {
    setError(null)
    try {
      await deleteDimension(id)
      onChange()
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <section>
      <h2>Dimensões</h2>
      <ul>
        {dimensions.map((dimension) => (
          <li key={dimension.id}>
            #{dimension.id} — {dimension.raw_label ?? '—'} (L:{dimension.width_mm ?? '-'} P:
            {dimension.depth_mm ?? '-'} ⌀:{dimension.diameter_mm ?? '-'} A:
            {dimension.height_mm ?? '-'}){' '}
            <button onClick={() => handleDelete(dimension.id)}>excluir</button>
          </li>
        ))}
      </ul>
      <form onSubmit={handleCreate}>
        <input placeholder="Rótulo (ex.: 1200x900)" value={rawLabel} onChange={(e) => setRawLabel(e.target.value)} />
        <input placeholder="Largura (mm)" value={width} onChange={(e) => setWidth(e.target.value)} />
        <input placeholder="Profundidade (mm)" value={depth} onChange={(e) => setDepth(e.target.value)} />
        <input placeholder="Diâmetro (mm)" value={diameter} onChange={(e) => setDiameter(e.target.value)} />
        <input placeholder="Altura (mm)" value={height} onChange={(e) => setHeight(e.target.value)} />
        <button type="submit">Adicionar dimensão</button>
      </form>
      <ErrorMessage error={error} />
    </section>
  )
}

function FinishesSection({ finishes, onChange }: { finishes: Finish[]; onChange: () => void }) {
  const [name, setName] = useState('')
  const [group, setGroup] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await createFinish({
        name,
        finish_group: (group || null) as Finish['finish_group'],
      })
      setName('')
      setGroup('')
      onChange()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function handleDelete(id: number) {
    setError(null)
    try {
      await deleteFinish(id)
      onChange()
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <section>
      <h2>Acabamentos</h2>
      <ul>
        {finishes.map((finish) => (
          <li key={finish.id}>
            #{finish.id} — {finish.name} {finish.finish_group ? `(${finish.finish_group})` : ''}{' '}
            <button onClick={() => handleDelete(finish.id)}>excluir</button>
          </li>
        ))}
      </ul>
      <form onSubmit={handleCreate}>
        <input placeholder="Nome" value={name} onChange={(e) => setName(e.target.value)} required />
        <select value={group} onChange={(e) => setGroup(e.target.value)}>
          <option value="">(grupo)</option>
          <option value="madeirado">madeirado</option>
          <option value="metalico">metálico</option>
          <option value="pe_estrutura">pé/estrutura</option>
          <option value="outro">outro</option>
        </select>
        <button type="submit">Adicionar acabamento</button>
      </form>
      <ErrorMessage error={error} />
    </section>
  )
}

function ComponentTypesSection({
  componentTypes,
  onChange,
}: {
  componentTypes: ProductComponentType[]
  onChange: () => void
}) {
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await createComponentType({ name })
      setName('')
      onChange()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function handleDelete(id: number) {
    setError(null)
    try {
      await deleteComponentType(id)
      onChange()
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <section>
      <h2>Tipos de componente</h2>
      <ul>
        {componentTypes.map((type) => (
          <li key={type.id}>
            #{type.id} — {type.name} <button onClick={() => handleDelete(type.id)}>excluir</button>
          </li>
        ))}
      </ul>
      <form onSubmit={handleCreate}>
        <input placeholder="Nome (ex.: Tampo)" value={name} onChange={(e) => setName(e.target.value)} required />
        <button type="submit">Adicionar tipo de componente</button>
      </form>
      <ErrorMessage error={error} />
    </section>
  )
}

function ProductsSection({
  products,
  families,
  dimensions,
  onChange,
}: {
  products: Product[]
  families: ProductFamily[]
  dimensions: Dimension[]
  onChange: () => void
}) {
  const [name, setName] = useState('')
  const [familyId, setFamilyId] = useState('')
  const [dimensionId, setDimensionId] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await createProduct({
        family_id: Number(familyId),
        name,
        dimension_id: dimensionId ? Number(dimensionId) : null,
      })
      setName('')
      onChange()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function handleDelete(id: number) {
    setError(null)
    try {
      await deleteProduct(id)
      onChange()
    } catch (err) {
      setError(describeError(err))
    }
  }

  function familyName(id: number) {
    return families.find((f) => f.id === id)?.name ?? `#${id}`
  }

  return (
    <section>
      <h2>Produtos-base</h2>
      <ul>
        {products.map((product) => (
          <li key={product.id}>
            #{product.id} — {product.name} ({familyName(product.family_id)}){' '}
            <button onClick={() => handleDelete(product.id)}>excluir</button>
          </li>
        ))}
      </ul>
      <form onSubmit={handleCreate}>
        <select value={familyId} onChange={(e) => setFamilyId(e.target.value)} required>
          <option value="">(família)</option>
          {families.map((family) => (
            <option key={family.id} value={family.id}>
              {family.name}
            </option>
          ))}
        </select>
        <input placeholder="Nome (ex.: Reunião 1200x900)" value={name} onChange={(e) => setName(e.target.value)} required />
        <select value={dimensionId} onChange={(e) => setDimensionId(e.target.value)}>
          <option value="">(dimensão)</option>
          {dimensions.map((dimension) => (
            <option key={dimension.id} value={dimension.id}>
              {dimension.raw_label ?? `#${dimension.id}`}
            </option>
          ))}
        </select>
        <button type="submit">Adicionar produto</button>
      </form>
      <ErrorMessage error={error} />
    </section>
  )
}

function ComponentVariantsSection({
  families,
  products,
  dimensions,
  finishes,
  componentTypes,
  priceTables,
  onChange,
}: {
  families: ProductFamily[]
  products: Product[]
  dimensions: Dimension[]
  finishes: Finish[]
  componentTypes: ProductComponentType[]
  priceTables: PriceTable[]
  onChange: () => void
}) {
  const [familyFilter, setFamilyFilter] = useState('')
  const [results, setResults] = useState<ComponentVariant[]>([])
  const [total, setTotal] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const [productId, setProductId] = useState('')
  const [componentId, setComponentId] = useState('')
  const [dimensionId, setDimensionId] = useState('')
  const [finishId, setFinishId] = useState('')
  const [descriptor, setDescriptor] = useState('')
  const [description, setDescription] = useState('')
  const [skuCode, setSkuCode] = useState('')
  const [priceAmount, setPriceAmount] = useState('')
  const [priceTableId, setPriceTableId] = useState('')

  async function runSearch() {
    try {
      const result = await searchComponents({ family: familyFilter || undefined })
      setResults(result.items)
      setTotal(result.total)
      setError(null)
    } catch (err) {
      setError(describeError(err))
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- busca de dados ao montar/filtrar
    void runSearch()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [familyFilter])

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await createComponent({
        product_id: productId ? Number(productId) : null,
        component_id: Number(componentId),
        dimension_id: dimensionId ? Number(dimensionId) : null,
        finish_id: finishId ? Number(finishId) : null,
        descriptor: descriptor || null,
        description: description || null,
        sku: skuCode ? { code: skuCode } : null,
        price:
          priceAmount && priceTableId
            ? { amount: Number(priceAmount), currency: 'BRL', price_table_id: Number(priceTableId) }
            : null,
      })
      setDescriptor('')
      setDescription('')
      setSkuCode('')
      setPriceAmount('')
      onChange()
      await runSearch()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function handleDelete(id: number) {
    setError(null)
    try {
      await deleteComponent(id)
      await runSearch()
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <section>
      <h2>Variações vendáveis (componentes)</h2>

      <div>
        <label>
          Filtrar por família:{' '}
          <select value={familyFilter} onChange={(e) => setFamilyFilter(e.target.value)}>
            <option value="">(todas)</option>
            {families.map((family) => (
              <option key={family.id} value={family.name}>
                {family.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <p>{total} variação(ões) encontrada(s).</p>

      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Família</th>
            <th>Produto</th>
            <th>Componente</th>
            <th>Descritor</th>
            <th>Dimensão</th>
            <th>Acabamento</th>
            <th>SKU</th>
            <th>Preço</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {results.map((item) => (
            <tr key={item.component_variant_id}>
              <td>{item.component_variant_id}</td>
              <td>{item.family ?? '—'}</td>
              <td>{item.product ?? '—'}</td>
              <td>{item.component}</td>
              <td>{item.descriptor ?? '—'}</td>
              <td>{item.dimension?.raw_label ?? '—'}</td>
              <td>{item.finish ?? '—'}</td>
              <td>{item.sku ?? '—'}</td>
              <td>
                {item.price ? `${item.price.currency} ${item.price.amount.toFixed(2)}` : '—'}
              </td>
              <td>
                <button onClick={() => handleDelete(item.component_variant_id)}>excluir</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Nova variação</h3>
      <form onSubmit={handleCreate}>
        <select value={componentId} onChange={(e) => setComponentId(e.target.value)} required>
          <option value="">(tipo de componente)</option>
          {componentTypes.map((type) => (
            <option key={type.id} value={type.id}>
              {type.name}
            </option>
          ))}
        </select>
        <select value={productId} onChange={(e) => setProductId(e.target.value)}>
          <option value="">(produto-base)</option>
          {products.map((product) => (
            <option key={product.id} value={product.id}>
              {product.name}
            </option>
          ))}
        </select>
        <select value={dimensionId} onChange={(e) => setDimensionId(e.target.value)}>
          <option value="">(dimensão)</option>
          {dimensions.map((dimension) => (
            <option key={dimension.id} value={dimension.id}>
              {dimension.raw_label ?? `#${dimension.id}`}
            </option>
          ))}
        </select>
        <select value={finishId} onChange={(e) => setFinishId(e.target.value)}>
          <option value="">(acabamento)</option>
          {finishes.map((finish) => (
            <option key={finish.id} value={finish.id}>
              {finish.name}
            </option>
          ))}
        </select>
        <input placeholder="Descritor (ex.: Inteiro Simples)" value={descriptor} onChange={(e) => setDescriptor(e.target.value)} />
        <input placeholder="Descrição" value={description} onChange={(e) => setDescription(e.target.value)} />
        <input placeholder="Código SKU" value={skuCode} onChange={(e) => setSkuCode(e.target.value)} />
        <input placeholder="Preço (R$)" value={priceAmount} onChange={(e) => setPriceAmount(e.target.value)} />
        <select value={priceTableId} onChange={(e) => setPriceTableId(e.target.value)}>
          <option value="">(tabela de preço)</option>
          {priceTables.map((table) => (
            <option key={table.id} value={table.id}>
              {table.code} ({table.status})
            </option>
          ))}
        </select>
        <button type="submit">Adicionar variação</button>
      </form>
      <ErrorMessage error={error} />
    </section>
  )
}

export function CatalogPage() {
  const [families, setFamilies] = useState<ProductFamily[]>([])
  const [dimensions, setDimensions] = useState<Dimension[]>([])
  const [finishes, setFinishes] = useState<Finish[]>([])
  const [componentTypes, setComponentTypes] = useState<ProductComponentType[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [priceTables, setPriceTables] = useState<PriceTable[]>([])
  const [error, setError] = useState<string | null>(null)

  async function reload() {
    try {
      const [familiesData, dimensionsData, finishesData, componentTypesData, productsData, priceTablesData] =
        await Promise.all([
          listFamilies(),
          listDimensions(),
          listFinishes(),
          listComponentTypes(),
          listProducts(),
          listPriceTables(),
        ])
      setFamilies(familiesData)
      setDimensions(dimensionsData)
      setFinishes(finishesData)
      setComponentTypes(componentTypesData)
      setProducts(productsData)
      setPriceTables(priceTablesData)
      setError(null)
    } catch (err) {
      setError(describeError(err))
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- carga inicial do catálogo
    void reload()
  }, [])

  return (
    <div>
      <h1>Catálogo — cadastro manual</h1>
      <ErrorMessage error={error} />
      <FamiliesSection families={families} onChange={reload} />
      <DimensionsSection dimensions={dimensions} onChange={reload} />
      <FinishesSection finishes={finishes} onChange={reload} />
      <ComponentTypesSection componentTypes={componentTypes} onChange={reload} />
      <ProductsSection products={products} families={families} dimensions={dimensions} onChange={reload} />
      <ComponentVariantsSection
        families={families}
        products={products}
        dimensions={dimensions}
        finishes={finishes}
        componentTypes={componentTypes}
        priceTables={priceTables}
        onChange={reload}
      />
    </div>
  )
}
