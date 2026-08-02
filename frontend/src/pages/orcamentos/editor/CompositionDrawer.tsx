import { useEffect, useState } from 'react'
import {
  getProductComposition,
  listProducts,
  searchComponents,
  type ComponentVariant,
  type Product,
  type ProductCompositionExpandedItem,
} from '../../../api/catalog'
import {
  addComponent,
  addItem,
  removeComponent,
  removeItem,
  swapComponent,
  type QuoteItem,
  type QuoteItemComponent,
} from '../../../api/quotes'
import { Botao, ConfirmDialog } from '../../../components/ui'

const money = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

export function CompositionDrawer({
  quoteId,
  item,
  onClose,
  onChanged,
}: {
  quoteId: number
  item: QuoteItem | null
  onClose: () => void
  onChanged: () => Promise<void>
}) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<ComponentVariant[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState<number | null>(null)
  const [replaceTarget, setReplaceTarget] = useState<QuoteItemComponent | null>(null)
  const [replacement, setReplacement] = useState<ComponentVariant | null>(null)
  const [removeLine, setRemoveLine] = useState(false)
  const [products, setProducts] = useState<Product[]>([])
  const [productId, setProductId] = useState('')
  const [productComponents, setProductComponents] = useState<ProductCompositionExpandedItem[]>([])
  const [loadingProduct, setLoadingProduct] = useState(false)
  const [createStep, setCreateStep] = useState<1 | 2 | 3>(1)
  const [baseVariant, setBaseVariant] = useState<ComponentVariant | null>(null)
  const [addedVariants, setAddedVariants] = useState<ComponentVariant[]>([])
  const [newItemLabel, setNewItemLabel] = useState('')
  const [newItemQuantity, setNewItemQuantity] = useState(1)

  // A primeira peça com dimensão é a base da composição. A busca leva seu ID
  // ao servidor, evitando inferências por texto e opções incompatíveis (RN-03).
  const baseComponent = item?.components.find((component) => component.dimension_id !== null) ?? item?.components[0]
  const baseDimensionId = baseComponent?.dimension_id ?? undefined

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setLoading(true)
      void searchComponents({
        q: query || undefined,
        component: replaceTarget?.component ?? undefined,
        dimension_id: item ? baseDimensionId : createStep > 1 ? baseVariant?.dimension?.id : undefined,
        page_size: 24,
      })
        .then((result) => setResults(result.items))
        .catch(() => setError('Não foi possível buscar peças.'))
        .finally(() => setLoading(false))
    }, 300)

    return () => window.clearTimeout(timer)
  }, [baseDimensionId, baseVariant?.dimension?.id, createStep, item, query, replaceTarget])

  useEffect(() => {
    if (item) return
    void listProducts()
      .then(setProducts)
      .catch(() => setError('Não foi possível carregar os produtos prontos.'))
  }, [item])

  useEffect(() => {
    if (!productId) return
    void getProductComposition(Number(productId))
      .then(setProductComponents)
      .catch(() => setError('Não foi possível carregar a composição do produto.'))
      .finally(() => setLoadingProduct(false))
  }, [productId])

  const product = products.find((candidate) => candidate.id === Number(productId))
  const productHasPrice = productComponents.length > 0 && productComponents.every(({ variant }) => variant.price)

  if (!item) {
    const manualVariants = baseVariant ? [baseVariant, ...addedVariants] : []
    const manualTotal = manualVariants.reduce((total, variant) => total + (variant.price?.amount ?? 0), 0)
    const selectBase = (variant: ComponentVariant) => {
      if (!variant.price) return
      setProductId('')
      setBaseVariant(variant)
      setAddedVariants([])
      setNewItemLabel(variant.description ?? variant.descriptor ?? variant.component)
      setQuery('')
      setCreateStep(2)
    }
    const prepareReadyProduct = () => {
      if (!product || !productHasPrice) return
      const variants = productComponents.flatMap(({ variant, quantity }) => Array.from({ length: quantity }, () => variant))
      const [base, ...complements] = variants
      if (!base) return
      setBaseVariant(base)
      setAddedVariants(complements)
      setNewItemLabel(product.name)
      setNewItemQuantity(1)
      setQuery('')
      setCreateStep(3)
    }
    const addManualComponent = (variant: ComponentVariant) => {
      if (!variant.price) return
      setAddedVariants((current) => [...current, variant])
    }
    const addManualItem = async () => {
      if (!baseVariant || !newItemLabel.trim()) return
      setBusy(baseVariant.component_variant_id)
      setError('')
      try {
        await addItem(quoteId, {
          label: newItemLabel.trim(),
          quantity: Math.max(1, newItemQuantity),
          product_id: productId ? Number(productId) : undefined,
          components: manualVariants.map((variant) => ({ component_variant_id: variant.component_variant_id })),
        })
        await onChanged()
        onClose()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Não foi possível adicionar este item.')
      } finally {
        setBusy(null)
      }
    }
    const changeProduct = (value: string) => {
      setProductId(value)
      setProductComponents([])
      setLoadingProduct(Boolean(value))
    }
    return (
      <div className="composition-drawer-backdrop">
        <aside className="composition-drawer" role="dialog" aria-modal="true" aria-label="Montar item">
          <header>
            <div>
              <span className="eyebrow">Adicionar ao orçamento</span>
              <h2>Montar item</h2>
              <ol className="composition-steps"><li className={createStep === 1 ? 'is-active' : ''}>1 Peça base</li><li className={createStep === 2 ? 'is-active' : ''}>2 Complementos</li><li className={createStep === 3 ? 'is-active' : ''}>3 Confirmar</li></ol>
            </div>
            <button onClick={onClose}>×</button>
          </header>
          {createStep === 1 && <section className="composition-create-step"><div className="composition-ready-product"><h3>Carregar um produto pronto</h3><select value={productId} onChange={(event) => changeProduct(event.target.value)}><option value="">Ou escolha uma composição do catálogo</option>{products.map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.name}</option>)}</select></div>{productId && <div className="composition-ready-preview"><b>{loadingProduct ? 'Carregando composição…' : `${productComponents.length} peças no produto`}</b>{!loadingProduct && productComponents.length > 0 && !productHasPrice && <p className="feedback-error">Uma ou mais peças estão sem preço e não podem ser adicionadas.</p>}{!loadingProduct && productComponents.length === 0 && <p className="feedback-warning">Este produto não possui peças cadastradas.</p>}<Botao tamanho="sm" disabled={loadingProduct || !productHasPrice} onClick={prepareReadyProduct}>Revisar antes de adicionar</Botao></div>}</section>}
          {createStep < 3 && <section className="composition-search"><h3>{createStep === 1 ? 'Escolha a peça base' : 'Adicionar complementos'}</h3>{createStep === 2 && baseVariant && <div className="composition-base"><span>BASE</span><div><b>{baseVariant.component}{baseVariant.descriptor ? ` · ${baseVariant.descriptor}` : ''}</b><small>{baseVariant.sku ?? 'Sem SKU'} · {money.format(baseVariant.price?.amount ?? 0)}</small></div><button type="button" onClick={() => setCreateStep(1)}>Trocar</button></div>}{createStep === 2 && baseVariant?.dimension?.raw_label && <p className="composition-dimension">A base fixa a dimensão <span className="mono">{baseVariant.dimension.raw_label}</span>; só mostramos peças que encaixam nela.</p>}{createStep === 2 && addedVariants.length > 0 && <div className="composition-selected"><h3>Já adicionados · {addedVariants.length}</h3>{addedVariants.map((variant, index) => <div className="composition-added" key={`${variant.component_variant_id}-${index}`}><span><b>{variant.component}{variant.descriptor ? ` · ${variant.descriptor}` : ''}</b><small>{variant.sku ?? 'Sem SKU'} · {money.format(variant.price?.amount ?? 0)}</small></span><Botao tamanho="sm" variante="fantasma" onClick={() => setAddedVariants((current) => current.filter((_, currentIndex) => currentIndex !== index))}>Remover</Botao></div>)}</div>}<input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar peça, SKU ou acabamento…" /><small className="composition-result-count">{loading ? 'Buscando peças…' : `${results.length} opções compatíveis`}</small><div className="composition-result-grid">{results.map((variant) => <article className={!variant.price ? 'is-unpriced' : ''} key={variant.component_variant_id}><span><b>{variant.component}{variant.descriptor ? ` · ${variant.descriptor}` : ''}</b><small>{variant.sku ?? 'Sem SKU'}</small></span><strong>{variant.price ? money.format(variant.price.amount) : 'Sem preço'}</strong><Botao tamanho="sm" disabled={!variant.price} onClick={() => createStep === 1 ? selectBase(variant) : addManualComponent(variant)}>{createStep === 1 ? 'Usar como base' : '+ Adicionar'}</Botao></article>)}</div>{!loading && results.length === 0 && <p className="helper-text">Nenhuma peça encontrada com estes filtros.</p>}</section>}
          {createStep === 3 && baseVariant && <section className="composition-confirm"><h3>Confirmar item</h3><label>Nome do item<input value={newItemLabel} onChange={(event) => setNewItemLabel(event.target.value)} /></label><div className="composition-confirm-list">{manualVariants.map((variant, index) => <p key={`${variant.component_variant_id}-${index}`}><span>{index === 0 ? 'BASE' : '+'} {variant.component}{variant.descriptor ? ` · ${variant.descriptor}` : ''}</span><strong>{money.format(variant.price?.amount ?? 0)}</strong></p>)}</div><p className="composition-freeze"><strong>{money.format(manualTotal)}</strong> · Este valor é congelado agora e não muda se o catálogo for atualizado.</p></section>}
          {error && <p className="feedback-error">{error}</p>}
          <footer><span className="composition-total">{money.format(manualTotal * newItemQuantity)}</span><label className="composition-quantity">Qtd.<input type="number" min="1" value={newItemQuantity} onChange={(event) => setNewItemQuantity(Math.max(1, Number(event.target.value) || 1))} /></label>{createStep === 2 && <Botao disabled={!baseVariant} onClick={() => setCreateStep(3)}>Confirmar item</Botao>}{createStep === 3 && <Botao disabled={!baseVariant || !newItemLabel.trim() || busy === baseVariant?.component_variant_id} onClick={() => void addManualItem()}>Adicionar ao orçamento</Botao>}{createStep === 1 && <Botao variante="secundario" onClick={onClose}>Cancelar</Botao>}</footer>
        </aside>
      </div>
    )
  }

  const add = async (variant: ComponentVariant) => {
    setBusy(variant.component_variant_id)
    setError('')
    try {
      await addComponent(quoteId, item.id, { component_variant_id: variant.component_variant_id })
      await onChanged()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'A peça não é compatível com esta composição.')
    } finally {
      setBusy(null)
    }
  }

  const remove = async (componentId: number) => {
    if (item.components.length === 1) {
      setRemoveLine(true)
      return
    }

    setBusy(componentId)
    try {
      await removeComponent(quoteId, item.id, componentId)
      await onChanged()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível remover a peça.')
    } finally {
      setBusy(null)
    }
  }

  const confirmRemoveLine = async () => {
    setBusy(item.id)
    try {
      await removeItem(quoteId, item.id)
      setRemoveLine(false)
      await onChanged()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível remover a linha.')
    } finally {
      setBusy(null)
    }
  }

  const confirmSwap = async () => {
    if (!replaceTarget || !replacement) return

    setBusy(replaceTarget.id)
    try {
      await swapComponent(quoteId, item.id, replaceTarget.id, {
        component_variant_id: replacement.component_variant_id,
      })
      setReplaceTarget(null)
      setReplacement(null)
      await onChanged()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'A nova peça não é compatível.')
    } finally {
      setBusy(null)
    }
  }

  const swapDescription =
    replaceTarget && replacement?.price
      ? `A peça atual está congelada em R$ ${replaceTarget.frozen_unit_price.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}. A nova peça será congelada em R$ ${replacement.price.amount.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}.`
      : 'A peça atual será substituída e o preço congelado da nova peça passará a valer neste orçamento.'

  return (
    <div className="composition-drawer-backdrop">
      <aside className="composition-drawer" role="dialog" aria-modal="true" aria-label="Editar composição">
        <header>
          <div>
            <span className="eyebrow">Composição do item</span>
            <h2>{item.label}</h2>
          </div>
          <button onClick={onClose}>×</button>
        </header>

        <section>
          <h3>Peças já adicionadas · {item.components.length}</h3>
          {item.components.map((component) => (
            <div className="composition-added" key={component.id}>
              <span>
                <b>{component.component ?? 'Peça'}</b>
                <small>{component.sku ?? 'Sem SKU'}</small>
              </span>
              <Botao tamanho="sm" variante="fantasma" onClick={() => setReplaceTarget(component)}>
                Trocar
              </Botao>
              <Botao
                tamanho="sm"
                variante="fantasma"
                disabled={busy === component.id}
                onClick={() => void remove(component.id)}
              >
                Remover
              </Botao>
            </div>
          ))}
        </section>

        <section>
          {baseComponent?.dimension_label && (
            <p className="composition-dimension">
              A peça-base fixa a dimensão <span className="mono">{baseComponent.dimension_label}</span>; só mostramos peças que encaixam nela.
            </p>
          )}
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar peça, SKU ou acabamento…"
          />
          <h3>
            {replaceTarget
              ? `Escolha a substituição para ${replaceTarget.component ?? 'a peça'}`
              : loading
                ? 'Buscando…'
                : 'Peças disponíveis'}
          </h3>
          {results.map((variant) => (
            <div className="composition-result" key={variant.component_variant_id}>
              <span>
                <b>{variant.component}{variant.descriptor ? ` · ${variant.descriptor}` : ''}</b>
                <small>
                  {variant.sku ?? 'Sem SKU'} · {variant.price ? `R$ ${variant.price.amount.toFixed(2)}` : 'Sem preço'}
                </small>
              </span>
              <Botao
                tamanho="sm"
                disabled={!variant.price || busy === variant.component_variant_id}
                onClick={() => (replaceTarget ? setReplacement(variant) : void add(variant))}
              >
                {replaceTarget ? 'Selecionar' : 'Adicionar'}
              </Botao>
            </div>
          ))}
        </section>

        {error && <p className="feedback-error">{error}</p>}
        <footer><Botao variante="secundario" onClick={onClose}>Concluir</Botao></footer>
      </aside>
      <ConfirmDialog
        aberta={Boolean(replacement)}
        titulo="Trocar e recongelar preço?"
        descricao={swapDescription}
        confirmarLabel="Trocar peça"
        tom="primario"
        onConfirmar={() => void confirmSwap()}
        onFechar={() => setReplacement(null)}
      />
      <ConfirmDialog
        aberta={removeLine}
        titulo="Remover item inteiro?"
        descricao="Esta é a última peça da linha. Para removê-la, o item inteiro será excluído do orçamento."
        confirmarLabel="Remover item"
        onConfirmar={() => void confirmRemoveLine()}
        onFechar={() => setRemoveLine(false)}
      />
    </div>
  )
}
