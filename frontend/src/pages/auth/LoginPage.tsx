import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { AuthApiError } from '../../api/auth'
import { Botao } from '../../components/ui'
import { useAuth } from '../../context/useAuth'
import './LoginPage.css'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(email, password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(
        err instanceof AuthApiError
          ? 'E-mail ou senha incorretos.'
          : 'Não foi possível entrar. Tente novamente.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return <main className="login-page">
    <aside className="login-promise" aria-label="Helence Orçamento">
      <div className="login-brand"><b>h</b><span>Helence</span></div>
      <div className="login-promise-copy"><h1>Do catálogo à proposta assinada, sem retrabalho.</h1><p>Preços congelados no instante em que entram no orçamento. O que você mostrou ao cliente continua valendo.</p></div>
    </aside>
    <section className="login-form-panel" aria-labelledby="login-title">
      <form onSubmit={handleSubmit} className="login-form">
        <header><h1 id="login-title">Entrar</h1><p>Use o e-mail da Helence.</p></header>
        <label htmlFor="login-email">E-mail<input id="login-email" type="email" autoComplete="email" required autoFocus value={email} onChange={(event) => setEmail(event.target.value)} /></label>
        <label htmlFor="login-password">Senha<input id="login-password" type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
        {error && <p className="login-error" role="alert">{error}</p>}
        <Botao className="login-submit" type="submit" disabled={submitting}>{submitting ? 'Entrando…' : 'Entrar'}</Botao>
        <p className="login-help">Esqueceu a senha? Fale com o administrador.</p>
      </form>
    </section>
  </main>
}
