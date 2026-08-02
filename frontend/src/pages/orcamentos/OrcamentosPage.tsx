import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  createCustomer,
  createQuote,
  getTotals,
  listCustomers,
  listItems,
  listQuotes,
  type Customer,
  type Quote,
  type QuoteStatus,
} from '../../api/quotes'
import { getSettings } from '../../api/settings'
import { Botao, Esqueleto, Selo, Vazio } from '../../components/ui'
import { STATUS_LABEL, STATUS_TOM } from '../../labels'
import '../painel/PainelPage.css'
import './OrcamentosPage.css'

type Filter = 'todos' | QuoteStatus | 'encerrado'
type DraftContext = { itemCount: number; incompleteLines: number; missingComponents: string[] }

const money = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const TODAY = new Date()

function dateAfter(days: number) {
  const value = new Date()
  value.setDate(value.getDate() + days)
  return value.toISOString().slice(0, 10)
}

function daysUntil(date: string | null) {
  if (!date) return null
  const target = new Date(`${date}T00:00:00`)
  return Math.ceil((target.getTime() - TODAY.setHours(0, 0, 0, 0)) / 86_400_000)
}

function isClosed(status: QuoteStatus) {
  return status === 'rejeitado' || status === 'expirado'
}

function contextFor(quote: Quote, draft?: DraftContext) {
  if (quote.status === 'rascunho') {
    if (draft?.incompleteLines) {
      const prefix = `${draft.incompleteLines} ${draft.incompleteLines === 1 ? 'linha incompleta' : 'linhas incompletas'}`
      const missing = draft.missingComponents.slice(0, 2).join(' e ')
      return `${prefix} — falta${draft.incompleteLines === 1 ? '' : 'm'} ${missing}`
    }
    return `Em montagem — ${draft?.itemCount ?? 0} ${draft?.itemCount === 1 ? 'item' : 'itens'}`
  }
  if (quote.status === 'enviado') {
    const days = daysUntil(quote.valid_until)
    return days === null ? 'Aguardando resposta do cliente' : days < 0 ? 'Validade vencida' : days === 0 ? 'Expira hoje' : `Expira em ${days} dia${days === 1 ? '' : 's'}`
  }
  if (quote.status === 'aprovado') return 'Aprovado pelo cliente'
  if (quote.status === 'rejeitado') return 'Recusado pelo cliente'
  return 'Validade vencida sem retorno'
}

function sectionFor(quote: Quote, draft?: DraftContext) {
  const days = daysUntil(quote.valid_until)
  if (quote.status === 'rascunho' && draft?.incompleteLines) return 'attention'
  if (quote.status === 'enviado' && days !== null && days <= 5) return 'attention'
  if (isClosed(quote.status)) return 'closed'
  return 'active'
}

function QuoteRow({ quote, total, draft }: { quote: Quote; total: number | undefined; draft?: DraftContext }) {
  const navigate = useNavigate()
  return (
    <button className={`quote-row quote-row--${sectionFor(quote, draft)}`} onClick={() => navigate(`/orcamentos/${quote.id}/itens`)}>
      <span className="mono">{quote.quote_number}</span>
      <span><b>{quote.customer.name}</b><small>{contextFor(quote, draft)}</small></span>
      <strong className="mono">{total === undefined ? '—' : money.format(total)}</strong>
      <span className="quote-validity">{quote.valid_until ? `válido até ${quote.valid_until}` : 'Sem validade'}</span>
      <Selo tom={STATUS_TOM[quote.status]}>{STATUS_LABEL[quote.status]}</Selo>
      <i>›</i>
    </button>
  )
}

export function OrcamentosPage() {
  const [quotes, setQuotes] = useState<Quote[] | null>(null)
  const [customers, setCustomers] = useState<Customer[]>([])
  const [totals, setTotals] = useState<Record<number, number>>({})
  const [draftContexts, setDraftContexts] = useState<Record<number, DraftContext>>({})
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<Filter>('todos')
  const [creating, setCreating] = useState(false)
  const [customerMode, setCustomerMode] = useState<'existing' | 'new'>('existing')
  const [customerId, setCustomerId] = useState('')
  const [customerName, setCustomerName] = useState('')
  const [customerEmail, setCustomerEmail] = useState('')
  const [customerPhone, setCustomerPhone] = useState('')
  const [validUntil, setValidUntil] = useState(dateAfter(30))
  const [notes, setNotes] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [defaultValidity, setDefaultValidity] = useState(30)
  const navigate = useNavigate()

  const load = async () => {
    try {
      const [quoteList, customerList, settings] = await Promise.all([listQuotes(), listCustomers(), getSettings()])
      setQuotes(quoteList)
      setCustomers(customerList)
      setDefaultValidity(settings.default_validity_days)
      const [totalEntries, draftEntries] = await Promise.all([
        Promise.all(quoteList.map(async (quote) => [quote.id, (await getTotals(quote.id)).total] as const)),
        Promise.all(quoteList.filter((quote) => quote.status === 'rascunho').map(async (quote) => {
          const items = await listItems(quote.id)
          const incomplete = items.filter((item) => item.missing_required_components.length > 0)
          return [quote.id, {
            itemCount: items.length,
            incompleteLines: incomplete.length,
            missingComponents: [...new Set(incomplete.flatMap((item) => item.missing_required_components))],
          }] as [number, DraftContext]
        })),
      ])
      setTotals(Object.fromEntries(totalEntries))
      setDraftContexts(Object.fromEntries(draftEntries))
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível carregar os orçamentos.')
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => { void load() }, 0)
    return () => window.clearTimeout(timer)
  }, [])

  const filtered = useMemo(() => {
    if (!quotes) return null
    const query = search.trim().toLowerCase()
    return quotes.filter((quote) => {
      const matchesSearch = !query || `${quote.quote_number} ${quote.customer.name}`.toLowerCase().includes(query)
      const matchesFilter = filter === 'todos' || (filter === 'encerrado' ? isClosed(quote.status) : quote.status === filter)
      return matchesSearch && matchesFilter
    })
  }, [filter, quotes, search])

  const counts = useMemo(() => {
    const result: Record<Filter, number> = { todos: 0, rascunho: 0, enviado: 0, aprovado: 0, rejeitado: 0, expirado: 0, encerrado: 0 }
    for (const quote of quotes ?? []) {
      result.todos += 1
      result[quote.status] += 1
      if (isClosed(quote.status)) result.encerrado += 1
    }
    return result
  }, [quotes])

  const openCreate = () => {
    setCustomerMode('existing')
    setCustomerId('')
    setCustomerName('')
    setCustomerEmail('')
    setCustomerPhone('')
    setValidUntil(dateAfter(defaultValidity))
    setNotes('')
    setError('')
    setCreating(true)
  }

  const create = async () => {
    if (customerMode === 'existing' && !customerId) return
    if (customerMode === 'new' && !customerName.trim()) return

    setBusy(true)
    setError('')
    try {
      const customer = customerMode === 'new'
        ? await createCustomer({ name: customerName.trim(), email: customerEmail || null, phone: customerPhone || null })
        : customers.find((candidate) => candidate.id === Number(customerId))
      if (!customer) throw new Error('Selecione um cliente válido.')
      const quote = await createQuote({ customer_id: customer.id, valid_until: validUntil || null, notes: notes || null })
      navigate(`/orcamentos/${quote.id}/itens`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível criar o orçamento.')
    } finally {
      setBusy(false)
    }
  }

  const sections = filtered && {
    attention: filtered.filter((quote) => sectionFor(quote, draftContexts[quote.id]) === 'attention'),
    active: filtered.filter((quote) => sectionFor(quote, draftContexts[quote.id]) === 'active'),
    closed: filtered.filter((quote) => sectionFor(quote, draftContexts[quote.id]) === 'closed'),
  }

  return (
    <div className="page quotes-page">
      <header className="page-head">
        <div><span className="eyebrow">Acompanhamento</span><h1>Orçamentos</h1></div>
        <Botao tamanho="lg" onClick={openCreate}>+ Novo orçamento</Botao>
      </header>

      {error && !creating && <p className="feedback-error">{error}</p>}
      <div className="quote-filters">
        <input className="page-search" placeholder="Buscar número ou cliente…" value={search} onChange={(event) => setSearch(event.target.value)} />
        <div className="quote-segments">
          {([['todos', 'Todos'], ['rascunho', 'Rascunho'], ['enviado', 'Com o cliente'], ['aprovado', 'Aprovado'], ['encerrado', 'Encerrado']] as const).map(([value, label]) => <button className={filter === value ? 'is-active' : ''} key={value} onClick={() => setFilter(value)}>{label} <span>{counts[value]}</span></button>)}
        </div>
      </div>

      {!sections ? <Esqueleto linhas={5} /> : sections.attention.length + sections.active.length + sections.closed.length === 0 ? <Vazio titulo={quotes?.length ? 'Nenhum orçamento com este filtro' : 'Nenhum orçamento ainda'} descricao={quotes?.length ? 'Tente limpar a busca ou os filtros.' : 'Crie o primeiro para começar a montar propostas.'} acao={quotes?.length ? <Botao variante="secundario" onClick={() => { setFilter('todos'); setSearch('') }}>Limpar filtros</Botao> : <Botao onClick={openCreate}>+ Novo orçamento</Botao>} /> : <div className="quote-sections">
        {([['attention', 'Precisam de atenção'], ['active', 'Em andamento'], ['closed', 'Encerrados']] as const).map(([key, title]) => sections[key].length > 0 && <section className={`quote-section quote-section--${key}`} key={key}><header><h2>{title}</h2></header>{sections[key].map((quote) => <QuoteRow key={quote.id} quote={quote} total={totals[quote.id]} draft={draftContexts[quote.id]} />)}</section>)}
      </div>}

      {creating && <div className="new-quote-backdrop" role="presentation"><div className="new-quote-dialog" role="dialog" aria-modal="true" aria-label="Novo orçamento"><header><div><span className="eyebrow">Acompanhamento</span><h2>Novo orçamento</h2></div><button onClick={() => setCreating(false)} aria-label="Fechar">×</button></header><div className="new-quote-body"><div className="new-quote-mode"><button className={customerMode === 'existing' ? 'is-active' : ''} onClick={() => setCustomerMode('existing')}>Cliente existente</button><button className={customerMode === 'new' ? 'is-active' : ''} onClick={() => setCustomerMode('new')}>Cadastrar cliente</button></div>{customerMode === 'existing' ? <label>Cliente<select value={customerId} onChange={(event) => setCustomerId(event.target.value)}><option value="">Selecione o cliente</option>{customers.map((customer) => <option key={customer.id} value={customer.id}>{customer.name}</option>)}</select></label> : <><label>Nome*<input value={customerName} onChange={(event) => setCustomerName(event.target.value)} autoFocus /></label><label>E-mail<input type="email" value={customerEmail} onChange={(event) => setCustomerEmail(event.target.value)} /></label><label>Telefone<input value={customerPhone} onChange={(event) => setCustomerPhone(event.target.value)} /></label></>}<label>Validade<input type="date" value={validUntil} onChange={(event) => setValidUntil(event.target.value)} /></label><label>Observações<textarea value={notes} onChange={(event) => setNotes(event.target.value)} /></label>{error && <p className="feedback-error">{error}</p>}</div><footer><Botao variante="secundario" onClick={() => setCreating(false)}>Cancelar</Botao><Botao disabled={busy || (customerMode === 'existing' ? !customerId : !customerName.trim())} onClick={() => void create()}>{busy ? 'Criando…' : 'Criar e adicionar itens'}</Botao></footer></div></div>}
    </div>
  )
}
