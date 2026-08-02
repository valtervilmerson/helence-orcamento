import { useEffect, useRef, useState } from 'react'
import { Link, Outlet, useNavigate, useOutletContext, useParams } from 'react-router-dom'
import { addItem, freezeTotals, removeItem, updateItem, updateQuoteSettings, updateQuoteStatus, type QuoteItem, type QuoteTotals } from '../../../api/quotes'
import { getSettings, type AppSettings } from '../../../api/settings'
import { Botao, Card, ConfirmDialog, Esqueleto, Selo } from '../../../components/ui'
import { STATUS_LABEL, STATUS_TOM } from '../../../labels'
import { useOrcamento, type OrcamentoData } from './useOrcamento'
import '../../painel/PainelPage.css'

type EditorData = OrcamentoData & { setSaveStatus: (status: string) => void }
const money = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
function Money({ value }: { value: number }) { return <>{money.format(value)}</> }
function useData() { return useOutletContext<EditorData>() }

export function EditorLayout() {
  const { id = '' } = useParams()
  const data = useOrcamento(Number(id))
  const { quote, quoteId, items, loading, error } = data
  const navigate = useNavigate()
  const [saveStatus, setSaveStatus] = useState('')
  const [response, setResponse] = useState<'aprovado' | 'rejeitado' | 'expirado' | null>(null)
  const [responseBusy, setResponseBusy] = useState(false)

  if (loading) return <div className="page"><Esqueleto linhas={6} /></div>
  if (!quote) return <div className="page"><p className="feedback-error">{error ?? 'Orçamento não encontrado.'}</p></div>

  const responseCopy = response === 'aprovado'
    ? { title: 'Registrar aprovação?', description: 'O orçamento será marcado como aprovado pelo cliente.', label: 'Cliente aprovou', tom: 'primario' as const }
    : response === 'rejeitado'
      ? { title: 'Registrar recusa?', description: 'O orçamento será marcado como recusado pelo cliente.', label: 'Cliente recusou', tom: 'perigo' as const }
      : { title: 'Marcar como expirado?', description: 'O orçamento será encerrado por validade vencida.', label: 'Marcar expirado', tom: 'perigo' as const }

  const registerResponse = async () => {
    if (!response) return
    setResponseBusy(true)
    try {
      await updateQuoteStatus(quoteId, response)
      navigate('/orcamentos')
    } finally {
      setResponseBusy(false)
    }
  }

  return <div className="editor"><header className="editor-head"><div><Link to="/orcamentos">← Orçamentos</Link><span className="eyebrow">{quote.quote_number} · {quote.valid_until ? `válido até ${quote.valid_until}` : 'sem validade'}</span><h1>{quote.customer.name} <Selo tom={STATUS_TOM[quote.status]}>{STATUS_LABEL[quote.status]}</Selo></h1></div><div>{saveStatus && <span className="editor-save-status" aria-live="polite">{saveStatus}</span>}<Botao variante="secundario" onClick={() => navigate(`/orcamentos/${quoteId}/documento`)}>Pré-visualizar</Botao>{quote.status === 'rascunho' && <Botao onClick={() => navigate('revisao')}>Revisar e enviar</Botao>}{quote.status === 'enviado' && <div className="editor-response-actions"><span>Registrar resposta do cliente</span><Botao tamanho="sm" variante="secundario" onClick={() => setResponse('aprovado')}>Aprovou</Botao><Botao tamanho="sm" variante="secundario" onClick={() => setResponse('rejeitado')}>Recusou</Botao><Botao tamanho="sm" variante="fantasma" onClick={() => setResponse('expirado')}>Expirou</Botao></div>}</div></header><nav className="editor-steps"><Link to="itens">1 Cliente ✓</Link><Link to="itens">2 Itens ({items.length})</Link><Link to="condicoes">3 Condições comerciais</Link><Link to="revisao">4 Revisar e enviar</Link></nav><Outlet context={{ ...data, setSaveStatus }} /><ConfirmDialog aberta={response !== null} titulo={responseCopy.title} descricao={responseCopy.description} confirmarLabel={responseBusy ? 'Registrando…' : responseCopy.label} tom={responseCopy.tom} onConfirmar={() => void registerResponse()} onFechar={() => !responseBusy && setResponse(null)} /></div>
}

function Summary({ totals, checklist }: { totals: QuoteTotals; checklist: OrcamentoData['checklist'] }) {
  const completed = checklist?.items.filter((item) => item.ok).length ?? 0
  const actionFor = (code: string) => code === 'DESCONTOS_JUSTIFICADOS' ? '../condicoes' : '../itens'
  return <aside><Card title="Resumo ao vivo" className="editor-summary"><dl><dt>Subtotal</dt><dd><Money value={totals.subtotal} /></dd>{totals.item_discount_amount > 0 && <><dt>Descontos de item</dt><dd className="editor-summary__discount">− <Money value={totals.item_discount_amount} /></dd></>}{totals.quote_discount_amount > 0 && <><dt>Desconto do orçamento</dt><dd className="editor-summary__discount">− <Money value={totals.quote_discount_amount} /></dd></>}<dt className="editor-summary__total">Total</dt><dd className="editor-summary__total"><Money value={totals.total} /></dd>{totals.installment_count > 1 && <><dt>{totals.installment_count}× {totals.installment_interest_percent ? 'com juros' : 'sem juros'}</dt><dd><Money value={totals.installment_value} /></dd></>}</dl><Link className="editor-summary__link" to="../condicoes">Ajustar condições comerciais →</Link></Card>{checklist && <Card title="Falta para enviar" className="editor-checklist"><header><span>{completed} de {checklist.items.length} concluídas</span><div><i style={{ width: `${checklist.items.length ? completed / checklist.items.length * 100 : 0}%` }} /></div></header>{checklist.items.map((item) => <div className={item.ok ? 'editor-check editor-check--ok' : 'editor-check editor-check--pending'} key={item.code}><i>{item.ok ? '✓' : '○'}</i><span><b>{item.label}</b>{!item.ok && <small>{item.pendencias[0] ?? 'Complete esta verificação antes de enviar.'}</small>}</span>{!item.ok && <Link to={actionFor(item.code)}>Completar →</Link>}</div>)}</Card>}</aside>
}

export function EditorItemsPage({
  onEditComposition,
  onAddReadyProduct,
}: {
  onEditComposition?: (item: QuoteItem) => void
  onAddReadyProduct?: () => void
}) {
  const { quote, quoteId, items, totals, checklist, recarregar } = useData(); const [busy, setBusy] = useState<number | null>(null); const [discountItem, setDiscountItem] = useState<QuoteItem | null>(null); const [discountMode, setDiscountMode] = useState<'percent' | 'amount'>('percent'); const [discount, setDiscount] = useState(''); const [reason, setReason] = useState(''); const [removing, setRemoving] = useState<QuoteItem | null>(null); const [openItemMenu, setOpenItemMenu] = useState<number | null>(null)
  if (!quote || !totals) return null
  const changeQuantity = async (itemId: number, quantity: number) => { if (quantity < 1) return; setBusy(itemId); try { await updateItem(quoteId, itemId, { quantity }); await recarregar() } finally { setBusy(null) } }
  const openDiscount = (item: QuoteItem) => { setDiscountItem(item); setDiscountMode(item.discount_percent != null ? 'percent' : 'amount'); setDiscount(String(item.discount_percent ?? item.discount_amount ?? '')); setReason(item.discount_reason ?? '') }
  const saveDiscount = async () => { if (!discountItem || !reason.trim()) return; setBusy(discountItem.id); try { await updateItem(quoteId, discountItem.id, { discount_percent: discountMode === 'percent' ? Number(discount) || 0 : null, discount_amount: discountMode === 'amount' ? Number(discount) || 0 : null, discount_reason: reason.trim() }); setDiscountItem(null); await recarregar() } finally { setBusy(null) } }
  const clearDiscount = async (item: QuoteItem) => { setBusy(item.id); try { await updateItem(quoteId, item.id, { discount_percent: null, discount_amount: null, discount_reason: null }); await recarregar() } finally { setBusy(null) } }
  const confirmRemove = async () => { if (!removing) return; setBusy(removing.id); try { await removeItem(quoteId, removing.id); setRemoving(null); await recarregar() } finally { setBusy(null) } }
  const duplicateItem = async (item: QuoteItem) => { setBusy(item.id); setOpenItemMenu(null); try { await addItem(quoteId, { label: `${item.label} — cópia`, quantity: item.quantity, components: item.components.map((component) => ({ component_variant_id: component.component_variant_id })) }); await recarregar() } finally { setBusy(null) } }
  const itemCard = (item: QuoteItem) => {
    const incomplete = item.missing_required_components.length > 0
    const kind = incomplete ? 'Incompleto' : item.components.length > 1 ? 'Produto montado' : 'Item avulso'
    const frozenAt = item.components[0]?.frozen_at
      ? new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit' }).format(new Date(item.components[0].frozen_at))
      : null
    return <Card key={item.id} className={`item-card${incomplete ? ' item-card--incomplete' : ''}${openItemMenu === item.id ? ' item-card--menu-open' : ''}`}><header><span className={`piece-count${incomplete ? ' piece-count--error' : ''}`}>{item.components.length}pç</span><span><b>{item.label}</b><small className={incomplete ? 'item-card__warning' : ''}>{incomplete ? `Falta ${item.missing_required_components.join(' e ')} — complete a linha antes de enviar.` : kind}</small></span><Selo tom={incomplete ? 'erro' : item.components.length > 1 ? 'marca' : 'neutro'}>{kind}</Selo><div className="item-quantity"><Botao tamanho="sm" variante="secundario" disabled={busy === item.id || quote.status !== 'rascunho'} onClick={() => void changeQuantity(item.id, item.quantity - 1)}>−</Botao><b>{item.quantity}</b><Botao tamanho="sm" variante="secundario" disabled={busy === item.id || quote.status !== 'rascunho'} onClick={() => void changeQuantity(item.id, item.quantity + 1)}>+</Botao></div>{incomplete ? <Botao tamanho="sm" variante="perigo" disabled={quote.status !== 'rascunho'} onClick={() => onEditComposition?.(item)}>Completar linha</Botao> : <span className="item-price"><strong><Money value={item.line_subtotal} /></strong><small>{item.discount_percent != null ? `−${item.discount_percent}% aplicado` : item.discount_amount != null ? `−${money.format(item.discount_amount)} aplicado` : <><Money value={item.line_subtotal / item.quantity} /> / un.</>}</small></span>}{quote.status === 'rascunho' && <div className="item-menu"><button type="button" aria-label={`Ações para ${item.label}`} aria-expanded={openItemMenu === item.id} onClick={() => setOpenItemMenu((current) => current === item.id ? null : item.id)}>⋯</button>{openItemMenu === item.id && <div className="item-menu__popover"><button type="button" onClick={() => { setOpenItemMenu(null); onEditComposition?.(item) }}>Editar composição</button><button type="button" onClick={() => { setOpenItemMenu(null); openDiscount(item) }}>Aplicar desconto</button>{(item.discount_percent != null || item.discount_amount != null) && <button type="button" disabled={busy === item.id} onClick={() => void clearDiscount(item)}>Limpar desconto</button>}<button type="button" disabled={busy === item.id} onClick={() => void duplicateItem(item)}>Duplicar linha</button><button className="item-menu__danger" type="button" onClick={() => { setOpenItemMenu(null); setRemoving(item) }}>Remover</button></div>}</div>}</header>{item.pricing_pendencias.length > 0 && <p className="item-pending">{item.pricing_pendencias.join(' ')}</p>}{item.components.length > 1 && <footer>{item.components.map((component) => <p key={component.id}><span>{component.component ?? 'Peça'} · {component.description ?? component.descriptor ?? 'sem descrição'}</span><span className="mono">{component.sku ?? '—'}</span><span className="mono"><Money value={component.frozen_unit_price} /></span></p>)}<small><span className="item-frozen-badge">▪ PREÇO CONGELADO{frozenAt ? ` EM ${frozenAt}` : ''}</span> não muda se o catálogo for atualizado</small></footer>}</Card>
  }
  return <div className="editor-body"><section><div className="items-title"><h2>{items.length} {items.length === 1 ? 'item' : 'itens'} no orçamento</h2>{quote.status === 'rascunho' && <div className="items-title-actions"><Botao tamanho="sm" variante="secundario" onClick={onAddReadyProduct}>Carregar produto pronto</Botao><button className="add-item" type="button" onClick={onAddReadyProduct}>+ Adicionar item</button></div>}</div>{items.length === 0 ? <Card><p>Nenhum item adicionado. Consulte o catálogo para montar a proposta.</p></Card> : <div className="item-cards">{items.map(itemCard)}</div>}</section><Summary totals={totals} checklist={checklist} />{discountItem && <div className="item-discount-panel" role="dialog" aria-modal="true" aria-label="Aplicar desconto"><Card title={`Desconto em ${discountItem.label}`}><div className="field-row"><select value={discountMode} onChange={(event) => setDiscountMode(event.target.value as typeof discountMode)}><option value="percent">Percentual</option><option value="amount">Valor R$</option></select><input type="number" min="0" value={discount} onChange={(event) => setDiscount(event.target.value)} placeholder={discountMode === 'percent' ? '%' : 'R$'} /><input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Motivo do desconto" /></div><footer><Botao variante="secundario" onClick={() => setDiscountItem(null)}>Cancelar</Botao><Botao disabled={!reason.trim() || busy === discountItem.id} onClick={() => void saveDiscount()}>Aplicar desconto</Botao></footer></Card></div>}<ConfirmDialog aberta={Boolean(removing)} titulo="Remover item?" descricao={removing ? `“${removing.label}” será removido deste orçamento.` : ''} confirmarLabel="Remover" onConfirmar={() => void confirmRemove()} onFechar={() => setRemoving(null)} /></div>
}

export function EditorConditionsPage() {
  const { quote, quoteId, totals, recarregar, setSaveStatus } = useData()
  const [settings, setSettings] = useState<AppSettings | null>(null)
  useEffect(() => { void getSettings().then(setSettings) }, [])
  if (!quote || !totals) return null
  return <ConditionsForm key={quote.id} quote={quote} quoteId={quoteId} totals={totals} settings={settings} recarregar={recarregar} setSaveStatus={setSaveStatus} />
}

type DiscountMode = 'none' | 'percent' | 'amount'
type EntryMode = 'none' | 'amount' | 'percent'

function ConditionsForm({ quote, quoteId, totals, settings, recarregar, setSaveStatus }: {
  quote: NonNullable<OrcamentoData['quote']>
  quoteId: number
  totals: QuoteTotals
  settings: AppSettings | null
  recarregar: OrcamentoData['recarregar']
  setSaveStatus: (status: string) => void
}) {
  const [markup, setMarkup] = useState(() => String(quote.markup_percent))
  const [usesGlobal, setUsesGlobal] = useState(() => quote.markup_uses_global)
  const [discountMode, setDiscountMode] = useState<DiscountMode>(() => quote.quote_discount_percent != null ? 'percent' : quote.quote_discount_amount != null ? 'amount' : 'none')
  const [discount, setDiscount] = useState(() => String(quote.quote_discount_percent ?? quote.quote_discount_amount ?? ''))
  const [reason, setReason] = useState(() => quote.quote_discount_reason ?? '')
  const [installments, setInstallments] = useState(() => String(quote.installment_count))
  const [interest, setInterest] = useState(() => String(quote.installment_interest_percent))
  const [entradaMode, setEntradaMode] = useState<EntryMode>(() => quote.entrada_percent ? 'percent' : quote.entrada_amount ? 'amount' : 'none')
  const [entrada, setEntrada] = useState(() => String(quote.entrada_percent || quote.entrada_amount || ''))
  const initialized = useRef(false)
  const limit = settings?.discount_limit_percent ?? 8
  const needsReason = discountMode === 'percent' && Number(discount) > limit
  const effectiveMarkup = usesGlobal ? settings?.global_markup_percent ?? quote.markup_percent : Number(markup) || 0
  const frozenCost = totals.subtotal / (1 + effectiveMarkup / 100)
  const entryValue = entradaMode === 'percent' ? totals.total * (Number(entrada) || 0) / 100 : Number(entrada) || 0

  useEffect(() => {
    const timer = window.setTimeout(() => { initialized.current = true }, 0)
    return () => window.clearTimeout(timer)
  }, [])

  useEffect(() => {
    if (!initialized.current || quote.status !== 'rascunho') return
    if (needsReason && !reason.trim()) {
      setSaveStatus('Informe o motivo do desconto')
      return
    }
    const timer = window.setTimeout(() => {
      setSaveStatus('Salvando…')
      void updateQuoteSettings(quoteId, {
        markup_uses_global: usesGlobal,
        markup_percent: usesGlobal ? undefined : Number(markup) || 0,
        quote_discount_percent: discountMode === 'percent' ? Number(discount) || 0 : null,
        quote_discount_amount: discountMode === 'amount' ? Number(discount) || 0 : null,
        quote_discount_reason: reason || null,
        installment_count: Math.max(1, Number(installments) || 1),
        installment_interest_percent: Number(interest) || 0,
        entrada_amount: entradaMode === 'amount' ? Number(entrada) || 0 : null,
        entrada_percent: entradaMode === 'percent' ? Number(entrada) || 0 : null,
      }).then(async () => { await recarregar(); setSaveStatus('Salvo agora') }).catch(() => setSaveStatus('Não foi possível salvar'))
    }, 600)
    return () => window.clearTimeout(timer)
  }, [discount, discountMode, entrada, entradaMode, installments, interest, markup, needsReason, quote.status, quoteId, reason, recarregar, setSaveStatus, usesGlobal])

  return <div className="editor-body conditions-layout"><section className="conditions">
    <Card title="Margem de venda" className="conditions-card"><p>Aplicada sobre o custo congelado. O padrão atual da empresa é {settings?.global_markup_percent ?? '…'}%.</p><div className="conditions-choices" role="radiogroup" aria-label="Origem da margem"><label className={usesGlobal ? 'is-selected' : ''}><input type="radio" name="markup-source" checked={usesGlobal} onChange={() => setUsesGlobal(true)} /><span><b>Padrão da empresa</b><small>{settings?.global_markup_percent ?? '…'}% · acompanha a política comercial</small></span></label><label className={!usesGlobal ? 'is-selected' : ''}><input type="radio" name="markup-source" checked={!usesGlobal} onChange={() => setUsesGlobal(false)} /><span><b>Margem específica</b><small>Use apenas para esta proposta</small></span><input aria-label="Margem específica" type="number" min="0" disabled={usesGlobal} value={markup} onChange={(event) => setMarkup(event.target.value)} /><em>%</em></label></div></Card>
    <Card title="Desconto da proposta" className="conditions-card"><p>Os descontos aplicados aos itens já aparecem separadamente no resumo.</p><div className="conditions-segment" role="radiogroup" aria-label="Tipo de desconto"><button className={discountMode === 'none' ? 'is-selected' : ''} type="button" onClick={() => setDiscountMode('none')}>Nenhum</button><button className={discountMode === 'percent' ? 'is-selected' : ''} type="button" onClick={() => setDiscountMode('percent')}>Percentual</button><button className={discountMode === 'amount' ? 'is-selected' : ''} type="button" onClick={() => setDiscountMode('amount')}>Valor R$</button></div>{discountMode !== 'none' && <div className="conditions-discount-fields"><label>Valor<input type="number" min="0" value={discount} onChange={(event) => setDiscount(event.target.value)} placeholder={discountMode === 'percent' ? '0,0' : '0,00'} /><span>{discountMode === 'percent' ? '%' : 'R$'}</span></label><label className={needsReason && !reason.trim() ? 'has-error' : ''}>Motivo{needsReason && <b> obrigatório</b>}<input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Ex.: negociação comercial" /></label></div>}{discountMode === 'percent' && <p className={needsReason ? 'conditions-authority conditions-authority--warning' : 'conditions-authority'}>{needsReason ? `Acima da alçada de ${limit}%. Registre o motivo para continuar.` : `Dentro da alçada comercial de até ${limit}%.`}</p>}</Card>
    <Card title="Pagamento" className="conditions-card"><div className="conditions-payment"><div><span className="conditions-field-label">Entrada</span><div className="conditions-segment conditions-segment--small"><button type="button" className={entradaMode === 'none' ? 'is-selected' : ''} onClick={() => setEntradaMode('none')}>Sem entrada</button><button type="button" className={entradaMode === 'amount' ? 'is-selected' : ''} onClick={() => setEntradaMode('amount')}>R$</button><button type="button" className={entradaMode === 'percent' ? 'is-selected' : ''} onClick={() => setEntradaMode('percent')}>%</button></div>{entradaMode !== 'none' && <label className="conditions-inline-input">{entradaMode === 'percent' ? '%' : 'R$'}<input type="number" min="0" value={entrada} onChange={(event) => setEntrada(event.target.value)} /></label>}</div><div><span className="conditions-field-label">Parcelamento</span><div className="conditions-installments">{[1, 3, 6, 10].map((number) => <button key={number} type="button" className={Number(installments) === number ? 'is-selected' : ''} onClick={() => setInstallments(String(number))}>{number}×</button>)}<label>Outro<input type="number" min="1" value={installments} onChange={(event) => setInstallments(event.target.value)} /></label></div>{Number(installments) > 1 && <label className="conditions-inline-input">Juros ao mês<input type="number" min="0" value={interest} onChange={(event) => setInterest(event.target.value)} /><span>%</span></label>}</div></div></Card>
    <footer className="conditions-navigation"><Link to="../itens">← Voltar aos itens</Link><Link className="conditions-primary-link" to="../revisao">Revisar proposta →</Link></footer>
  </section><aside className="conditions-cascade"><Card title="Como o número se forma"><dl><dt>Custo congelado</dt><dd><Money value={frozenCost} /></dd><dt>Margem de venda · {effectiveMarkup}%</dt><dd><Money value={totals.subtotal - frozenCost} /></dd><dt>Preço antes de descontos</dt><dd><Money value={totals.subtotal} /></dd>{totals.item_discount_amount > 0 && <><dt>Descontos dos itens</dt><dd>− <Money value={totals.item_discount_amount} /></dd></>}{totals.quote_discount_amount > 0 && <><dt>Desconto da proposta</dt><dd>− <Money value={totals.quote_discount_amount} /></dd></>}<dt className="conditions-total">Total da proposta</dt><dd className="conditions-total"><Money value={totals.total} /></dd></dl><footer>{entryValue > 0 && <p>Entrada: <strong><Money value={entryValue} /></strong></p>}<p>{totals.installment_count > 1 ? `${totals.installment_count}× de ` : 'À vista · '}<strong><Money value={totals.installment_value} /></strong>{totals.installment_interest_percent > 0 && ` · juros de ${totals.installment_interest_percent}%`}</p></footer></Card><p className="conditions-autosave">As alterações são salvas automaticamente.</p></aside></div>
}

export function EditorReviewPage() { const { quoteId, quote, totals, checklist } = useData(); const navigate = useNavigate(); const [busy, setBusy] = useState(false); if (!quote || !totals || !checklist) return null; const send = async () => { setBusy(true); try { await freezeTotals(quoteId); await updateQuoteStatus(quoteId, 'enviado'); navigate('/orcamentos') } finally { setBusy(false) } }; return <div className="editor-body"><Card title={checklist.ready ? 'Pronto para enviar' : 'Faltam verificações'}>{checklist.items.map((item) => <p key={item.code}>{item.ok ? '✓' : '○'} <b>{item.label}</b>{!item.ok && ` — ${item.pendencias.join('; ')}`}</p>)}<Botao disabled={!checklist.ready || busy} onClick={() => void send()}>{busy ? 'Enviando…' : 'Congelar e enviar'}</Botao></Card><Summary totals={totals} checklist={checklist} /></div> }
