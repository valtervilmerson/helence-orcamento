import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createQuote, listCustomers, listQuotes, type Customer, type Quote } from '../../api/quotes'
import { Botao, Card, Esqueleto, Selo, Vazio } from '../../components/ui'
import { STATUS_LABEL, STATUS_TOM } from '../../labels'
import '../painel/PainelPage.css'
import './OrcamentosPage.css'

export function OrcamentosPage() {
  const [quotes, setQuotes] = useState<Quote[] | null>(null); const [customers, setCustomers] = useState<Customer[]>([]); const [search, setSearch] = useState(''); const [creating, setCreating] = useState(false); const [customerId, setCustomerId] = useState(''); const navigate = useNavigate()
  const load = () => void Promise.all([listQuotes(), listCustomers()]).then(([q,c]) => { setQuotes(q); setCustomers(c) })
  useEffect(load, []); const filtered = quotes?.filter((q) => `${q.quote_number} ${q.customer.name}`.toLowerCase().includes(search.toLowerCase()))
  async function create() { if (!customerId) return; const quote = await createQuote({ customer_id: Number(customerId), valid_until: null, notes: null }); navigate(`/orcamentos/${quote.id}/itens`) }
  return <div className="page"><header className="page-head"><div><span className="eyebrow">Acompanhamento</span><h1>Orçamentos</h1></div><Botao tamanho="lg" onClick={() => setCreating(true)}>+ Novo orçamento</Botao></header>{creating && <Card title="Novo orçamento" className="new-quote"><select value={customerId} onChange={(e) => setCustomerId(e.target.value)}><option value="">Selecione o cliente</option>{customers.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select><Botao onClick={() => void create()} disabled={!customerId}>Criar e adicionar itens</Botao><Botao variante="fantasma" onClick={() => setCreating(false)}>Cancelar</Botao></Card>}<input className="page-search" placeholder="Buscar número ou cliente…" value={search} onChange={(e) => setSearch(e.target.value)} />{!filtered ? <Esqueleto linhas={5} /> : filtered.length === 0 ? <Vazio titulo="Nenhum orçamento encontrado" descricao="Crie o primeiro para começar a montar propostas." /> : <div className="quote-rows">{filtered.map((q) => <button key={q.id} onClick={() => navigate(`/orcamentos/${q.id}/itens`)}><span className="mono">{q.quote_number}</span><b>{q.customer.name}</b><span>{q.valid_until ? `válido até ${q.valid_until}` : 'Sem validade definida'}</span><Selo tom={STATUS_TOM[q.status]}>{STATUS_LABEL[q.status]}</Selo><i>›</i></button>)}</div>}</div>
}
