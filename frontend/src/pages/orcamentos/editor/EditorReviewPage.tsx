import { useState } from 'react'
import { Link, useNavigate, useOutletContext } from 'react-router-dom'
import { freezeTotals, updateQuoteStatus } from '../../../api/quotes'
import { Botao, Card } from '../../../components/ui'
import type { OrcamentoData } from './useOrcamento'

const money = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

function evidence(code: string, customer: string, total: number, installments: number) {
  if (code === 'COMPOSICAO_COMPLETA') return 'Todas as linhas têm os componentes obrigatórios ou uma justificativa registrada.'
  if (code === 'COMPONENTES_COM_PRECO_E_SKU') return `Os componentes possuem preço congelado. Total atual: ${money.format(total)}.`
  if (code === 'CLIENTE_E_ITENS') return `${customer} está associado ao orçamento e as linhas foram conferidas.`
  if (code === 'DESCONTOS_JUSTIFICADOS') return installments > 1 ? `Condições de pagamento em ${installments} parcelas registradas.` : 'Descontos e condições comerciais estão justificados.'
  return 'Verificação concluída.'
}

export function RedesignReviewPage() {
  const { quoteId, quote, totals, checklist } = useOutletContext<OrcamentoData>()
  const navigate = useNavigate(); const [busy, setBusy] = useState(false); const [error, setError] = useState('')
  if (!quote || !totals || !checklist) return null
  const pending = checklist.items.filter((item) => !item.ok)
  const completed = checklist.items.length - pending.length
  const title = pending.length === 0 ? 'Pronto para enviar' : pending.length === 1 ? 'Falta uma coisa antes de enviar' : `Faltam ${pending.length} coisas antes de enviar`
  const subtitle = pending.length === 0 ? 'As verificações passaram. O documento já reflete estes valores.' : `${completed} de ${checklist.items.length} verificações concluídas. Resolva as pendências abaixo para liberar o envio.`
  const send = async () => { setBusy(true); setError(''); try { await freezeTotals(quoteId); await updateQuoteStatus(quoteId, 'enviado'); navigate('/orcamentos') } catch (err) { setError(err instanceof Error ? err.message : 'Não foi possível enviar o orçamento.') } finally { setBusy(false) } }
  return <div className="editor-body review-body"><section className="review-main"><div className="review-verdict"><span>{completed}</span><div><h2>{title}</h2><p>{subtitle}</p></div></div><Card title="Verificações antes do envio" className="review-checklist">{checklist.items.map((item) => <div className={item.ok ? 'review-check review-check--ok' : 'review-check review-check--pending'} key={item.code}><i>{item.ok ? '✓' : '○'}</i><div><b>{item.label}</b><small>{item.ok ? evidence(item.code, quote.customer.name, totals.total, totals.installment_count) : item.pendencias.join(' ')}</small></div>{!item.ok && <Link to={item.code === 'DESCONTOS_JUSTIFICADOS' ? '../condicoes' : '../itens'}>Completar →</Link>}</div>)}</Card><Card title="Como enviar"><div className="review-actions"><button type="button" onClick={() => navigate(`/orcamentos/${quoteId}/documento`)}><b>Pré-visualizar documento</b><small>Confira a proposta antes do envio.</small></button><button type="button" onClick={() => navigate(`/orcamentos/${quoteId}/documento`)}><b>Baixar PDF</b><small>Disponível depois de congelar os valores.</small></button></div></Card></section><aside className="review-sidebar"><Card title="Prévia do documento"><Link to={`/orcamentos/${quoteId}/documento`} className="document-preview"><div><span>HELENCE</span><b>{quote.quote_number}</b><h3>Proposta comercial</h3><i /><i /><i /><strong>{money.format(totals.total)}</strong></div></Link></Card><Card title="Fechamento"><p>Total da proposta</p><strong className="review-total">{money.format(totals.total)}</strong><Botao className="review-send" disabled={!checklist.ready || busy} onClick={() => void send()}>{busy ? 'Enviando…' : 'Congelar e enviar'}</Botao><small>{checklist.ready ? 'Os valores serão congelados neste momento.' : `Libera quando as ${checklist.items.length} verificações passarem.`}</small>{error && <p className="feedback-error">{error}</p>}</Card></aside></div>
}
