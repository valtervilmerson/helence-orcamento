import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listQuotes, type Quote } from '../../api/quotes'
import { Botao, Card, Esqueleto, Selo, Vazio } from '../../components/ui'
import { STATUS_LABEL, STATUS_TOM } from '../../labels'
import './PainelPage.css'

export function PainelPage() {
  const [quotes, setQuotes] = useState<Quote[] | null>(null); const [error, setError] = useState(false); const navigate = useNavigate()
  useEffect(() => { void listQuotes().then(setQuotes).catch(() => setError(true)) }, [])
  const hour = new Date().getHours(); const greeting = hour < 12 ? 'Bom dia' : hour < 18 ? 'Boa tarde' : 'Boa noite'
  const groups = [['rascunho', 'Em rascunho'], ['enviado', 'Com o cliente'], ['aprovado', 'Aprovados'], ['expirado', 'Expira em 7 dias']] as const
  return <div className="page painel"><header className="page-head"><div><span className="eyebrow">{new Intl.DateTimeFormat('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date())}</span><h1>{greeting}</h1></div><Botao tamanho="lg" onClick={() => navigate('/orcamentos')}>+ Novo orçamento</Botao></header>{error && <p className="feedback-error">Não foi possível carregar o painel.</p>}{!quotes ? <Esqueleto linhas={5} /> : <><div className="metric-grid">{groups.map(([status, label]) => <Card key={status} className={status === 'expirado' ? 'metric metric--warning' : 'metric'}><span>{label}</span><strong>{quotes.filter((q) => q.status === status).length}</strong><small>orçamentos</small></Card>)}</div><div className="panel-grid"><Card title="Precisa de você"><div className="quote-mini-list">{quotes.filter((q) => q.status === 'rascunho').slice(0, 5).map((q) => <button key={q.id} onClick={() => navigate(`/orcamentos/${q.id}/itens`)}><span><b>{q.quote_number} · {q.customer.name}</b><small>Continue a montagem do orçamento</small></span>Resolver →</button>)}{quotes.every((q) => q.status !== 'rascunho') && <Vazio titulo="Nada parado com você" descricao="Todos os orçamentos estão com o cliente ou finalizados." />}</div></Card><Card title="Atividade recente" action={<Link to="/orcamentos">Ver todos</Link>}><div className="quote-mini-list">{quotes.slice(-3).reverse().map((q) => <Link key={q.id} to={`/orcamentos/${q.id}/itens`}><b>{q.quote_number} · {q.customer.name}</b><Selo tom={STATUS_TOM[q.status]}>{STATUS_LABEL[q.status]}</Selo></Link>)}</div></Card></div></>}</div>
}
