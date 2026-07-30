import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getQuoteSummary, listQuotes, type Quote, type QuoteSummary } from '../../api/quotes'
import { Botao, Card, Esqueleto, Selo, Vazio } from '../../components/ui'
import { useAuth } from '../../context/useAuth'
import { STATUS_LABEL, STATUS_TOM } from '../../labels'
import './PainelPage.css'

const money = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const dateFormatter = new Intl.DateTimeFormat('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })

function relativeDate(value: string) {
  const diff = Date.now() - new Date(value).getTime()
  const minutes = Math.max(0, Math.floor(diff / 60_000))
  if (minutes < 1) return 'agora'
  if (minutes < 60) return `há ${minutes} min`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `há ${hours} h`
  return `há ${Math.floor(hours / 24)} d`
}

function daysUntil(value: string | null) {
  if (!value) return null
  return Math.ceil((new Date(`${value}T00:00:00`).getTime() - Date.now()) / 86_400_000)
}

export function PainelPage() {
  const [quotes, setQuotes] = useState<Quote[] | null>(null)
  const [summary, setSummary] = useState<QuoteSummary | null>(null)
  const [error, setError] = useState(false)
  const { user } = useAuth()
  const navigate = useNavigate()

  const load = () => {
    setError(false)
    void Promise.all([listQuotes(), getQuoteSummary()])
      .then(([quotesData, summaryData]) => { setQuotes(quotesData); setSummary(summaryData) })
      .catch(() => setError(true))
  }

  useEffect(load, [])

  const greeting = new Date().getHours() < 12 ? 'Bom dia' : new Date().getHours() < 18 ? 'Boa tarde' : 'Boa noite'
  const firstName = user?.name.trim().split(/\s+/)[0] ?? ''
  const byId = useMemo(() => new Map(quotes?.map((quote) => [quote.id, quote])), [quotes])
  const isSeller = user?.role === 'vendedor' || user?.role === 'admin' || user?.role === 'colaborador'

  if (!quotes || !summary) {
    return <div className="page painel"><header className="page-head"><div><span className="eyebrow">Painel</span><h1>{greeting}{firstName ? `, ${firstName}` : ''}</h1></div></header>{error ? <p className="feedback-error">Não foi possível carregar o painel. <button onClick={load}>Tentar novamente</button></p> : <Esqueleto linhas={7} />}</div>
  }

  const pendingQuotes = summary.pendencias.map((id) => byId.get(id)).filter((quote): quote is Quote => Boolean(quote))
  const expiringQuotes = summary.expirando_7d.map((id) => byId.get(id)).filter((quote): quote is Quote => Boolean(quote))
  const needsYou = [
    ...pendingQuotes.map((quote) => ({ quote, text: 'Há itens ou dados comerciais que precisam de revisão.', tone: 'erro' as const, route: 'itens' })),
    ...expiringQuotes.filter((quote) => !summary.pendencias.includes(quote.id)).map((quote) => ({ quote, text: `Vence ${daysUntil(quote.valid_until) === 0 ? 'hoje' : `em ${daysUntil(quote.valid_until)} dias`} — acompanhe o retorno do cliente.`, tone: 'atencao' as const, route: 'revisao' })),
  ].slice(0, 5)
  const funnel = [
    ['Rascunho', 'rascunho', '#C9CFC9'], ['Com o cliente', 'enviado', '#7FA891'], ['Aprovado', 'aprovado', 'var(--verde-600)'], ['Perdido / expirado', 'expirado', '#D9B7B0'],
  ] as const
  const funnelMax = Math.max(1, ...funnel.map(([, status]) => summary.por_status[status].count))
  const finalThisMonth = summary.por_status.aprovado.count + summary.por_status.rejeitado.count + summary.por_status.expirado.count
  const approvalRate = finalThisMonth ? Math.round(summary.por_status.aprovado.count / finalThisMonth * 100) : 0
  const metrics = [
    ['Em rascunho', 'rascunho'], ['Com o cliente', 'enviado'], ['Aprovados', 'aprovado'], ['Expira em 7 dias', 'expirado'],
  ] as const

  return <div className="page painel">
    <header className="page-head"><div><span className="eyebrow">{dateFormatter.format(new Date())}</span><h1>{greeting}{firstName ? `, ${firstName}` : ''}</h1></div><Botao tamanho="lg" onClick={() => navigate('/orcamentos')}>+ Novo orçamento</Botao></header>
    {error && <p className="feedback-error">Os dados podem estar desatualizados. <button onClick={load}>Tentar novamente</button></p>}
    {isSeller && <div className="metric-grid">{metrics.map(([label, status]) => {
      const bucket = status === 'expirado' ? { count: summary.expirando_7d.length, total: 0 } : summary.por_status[status]
      return <Card key={status} className={status === 'expirado' ? 'metric metric--warning' : 'metric'}><span>{label}</span><strong>{bucket.count}</strong><small>{status === 'expirado' ? 'orçamentos enviados' : money.format(bucket.total)}</small></Card>
    })}</div>}
    <div className="panel-grid">
      <Card title="Precisa de você" action={<span className="painel-count">{needsYou.length}</span>}><div className="quote-mini-list">{needsYou.map(({ quote, text, tone, route }) => <button key={quote.id} onClick={() => navigate(`/orcamentos/${quote.id}/${route}`)}><span className="painel-action"><i className={`painel-dot painel-dot--${tone}`} /><span><b>{quote.quote_number} · {quote.customer.name}</b><small>{text}</small></span></span>Resolver →</button>)}{needsYou.length === 0 && <Vazio titulo="Nada parado com você" descricao="Todos os orçamentos estão com o cliente ou finalizados." />}</div></Card>
      {isSeller && <Card title="Funil do mês"><div className="funnel">{funnel.map(([label, status, color]) => <div key={status}><span>{label}</span><b>{summary.por_status[status].count}</b><i><em style={{ width: `${summary.por_status[status].count / funnelMax * 100}%`, backgroundColor: color }} /></i></div>)}</div><footer className="approval-rate"><span>Taxa de aprovação</span><strong>{approvalRate}%</strong></footer></Card>}
    </div>
    <Card title="Atividade recente" action={<Link to="/orcamentos">Ver todos</Link>} className="recent-card"><div className="recent-head"><span>Número</span><span>Cliente</span><span>Total</span><span>Atualizado</span><span>Status</span></div><div className="recent-list">{quotes.slice().sort((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, 3).map((quote) => <Link key={quote.id} to={`/orcamentos/${quote.id}/itens`}><span className="mono">{quote.quote_number}</span><b>{quote.customer.name}</b><span className="mono">—</span><span>{relativeDate(quote.created_at)}</span><Selo tom={STATUS_TOM[quote.status]}>{STATUS_LABEL[quote.status]}</Selo></Link>)}</div></Card>
  </div>
}
