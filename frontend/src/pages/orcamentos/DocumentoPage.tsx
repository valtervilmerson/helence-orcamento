import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { exportQuotePdf, getQuote, getTotals, listItems, type Quote, type QuoteItem, type QuoteTotals } from '../../api/quotes'
import { Botao, Esqueleto } from '../../components/ui'
import './DocumentoPage.css'

const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const date = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium' })

function formatDate(value: string | null) {
  return value ? date.format(new Date(value.replace(' ', 'T'))) : null
}

function commercialDescription(item: QuoteItem) {
  const parts = item.components
    .map((component) => component.description ?? component.descriptor ?? component.component)
    .filter((value): value is string => Boolean(value))
  if (parts.length === 0) return 'Composição personalizada Helence.'
  const text = parts.join(' · ')
  return `${text.slice(0, 1).toUpperCase()}${text.slice(1)}.`
}

function paymentDescription(totals: QuoteTotals) {
  if (totals.installment_count <= 1) return 'Pagamento à vista.'
  const interest = totals.installment_interest_percent > 0
    ? `com juros de ${totals.installment_interest_percent.toLocaleString('pt-BR')}%`
    : 'sem juros'
  if (totals.entrada_amount > 0) {
    return `Entrada de ${currency.format(totals.entrada_amount)} e mais ${totals.installment_count} × ${currency.format(totals.installment_value)} ${interest}.`
  }
  return `${totals.installment_count} × ${currency.format(totals.installment_value)} ${interest}.`
}

export function DocumentoPage() {
  const { id = '' } = useParams()
  const [data, setData] = useState<[Quote, QuoteItem[], QuoteTotals] | null>(null)
  const [downloadError, setDownloadError] = useState('')

  useEffect(() => {
    void Promise.all([getQuote(Number(id)), listItems(Number(id)), getTotals(Number(id))]).then(setData)
  }, [id])

  if (!data) return <div className="page"><Esqueleto linhas={8} /></div>
  const [quote, items, totals] = data
  const discount = totals.item_discount_amount + totals.quote_discount_amount

  async function download() {
    setDownloadError('')
    try {
      const blob = await exportQuotePdf(quote.id)
      const href = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = href
      link.download = `${quote.quote_number}.pdf`
      link.click()
      URL.revokeObjectURL(href)
    } catch {
      setDownloadError('O PDF fica disponível depois de congelar os valores na revisão.')
    }
  }

  return <div className="document-view">
    <header className="document-toolbar">
      <Link to={`/orcamentos/${id}/revisao`}>‹ Voltar ao orçamento</Link>
      <span>Proposta {quote.quote_number} · página 1 de 1</span>
      <Botao tamanho="sm" variante="secundario" onClick={() => void download()}>Baixar PDF</Botao>
    </header>
    <article className="proposal">
      <header className="proposal-brand">
        <b>h</b>
        <span><strong>Helence Mobiliário</strong><small>Mesas de reunião sob medida · desde 1998</small></span>
        <aside><small>PROPOSTA</small><b>{quote.quote_number}</b><span>Emitida em {formatDate(quote.created_at)}</span></aside>
      </header>
      <div className="proposal-meta">
        <section><small>PREPARADA PARA</small><h1>{quote.customer.name}</h1><p>Proposta comercial preparada especialmente para este projeto.</p></section>
        <section><small>CONDIÇÕES</small><p><b>Validade:</b> {formatDate(quote.valid_until) ?? 'a definir'}<br /><b>Pagamento:</b> {paymentDescription(totals)}<br /><b>Consultora:</b> {quote.created_by?.name ?? 'Equipe comercial Helence'}</p></section>
      </div>
      <section className="proposal-items">
        <h2>Itens da proposta</h2>
        <div className="proposal-table"><header><span>Descrição</span><span>Qtd</span><span>Unitário</span><span>Total</span></header>{items.map((item) => <div key={item.id}><span><b>{item.label}</b><small>{commercialDescription(item)}</small></span><span>{item.quantity}</span><span>{currency.format(item.line_subtotal / item.quantity)}</span><b>{currency.format(item.line_subtotal)}</b></div>)}</div>
      </section>
      <section className="proposal-total"><p>Subtotal <b>{currency.format(totals.subtotal)}</b></p>{discount > 0 && <p className="proposal-discount">Desconto comercial <b>− {currency.format(discount)}</b></p>}<h2>Total da proposta <b>{currency.format(totals.total)}</b></h2>{totals.installment_count > 1 && <p className="payment">{paymentDescription(totals)}</p>}</section>
      {quote.notes && <section className="proposal-notes"><small>OBSERVAÇÕES</small><p>{quote.notes}</p></section>}
      <footer><p>Valores em reais, impostos inclusos. Instalação em Curitiba e região metropolitana inclusa. Esta proposta perde a validade em {formatDate(quote.valid_until) ?? 'data a definir'}.</p><span>________________________________<br />Aceite do cliente · data e assinatura</span></footer>
    </article>
    {downloadError && <p className="document-download-error" role="alert">{downloadError}</p>}
  </div>
}
