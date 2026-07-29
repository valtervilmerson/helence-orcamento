import type { ButtonHTMLAttributes, ReactNode } from 'react'
import './ui.css'

export function Botao({ variante = 'primario', tamanho = 'md', className = '', ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variante?: 'primario' | 'secundario' | 'perigo' | 'fantasma'; tamanho?: 'sm' | 'md' | 'lg' }) {
  return <button {...props} className={`botao botao--${variante} botao--${tamanho} ${className}`} />
}
export function Card({ title, action, children, padding = 'md', className = '' }: { title?: ReactNode; action?: ReactNode; children: ReactNode; padding?: 'none' | 'md'; className?: string }) {
  return <section className={`card card--${padding} ${className}`}>{(title || action) && <header className="card__header"><h2>{title}</h2>{action}</header>}{children}</section>
}
export function Selo({ tom = 'neutro', children }: { tom?: 'neutro' | 'ok' | 'atencao' | 'erro' | 'marca'; children: ReactNode }) { return <span className={`selo selo--${tom}`}>{children}</span> }
export function Vazio({ titulo, descricao, acao }: { titulo: string; descricao: string; acao?: ReactNode }) { return <div className="vazio"><h2>{titulo}</h2><p>{descricao}</p>{acao}</div> }
export function Esqueleto({ linhas = 3 }: { linhas?: number }) { return <div className="esqueleto">{Array.from({ length: linhas }, (_, i) => <i key={i} />)}</div> }
export function ConfirmDialog({ aberta, titulo, descricao, confirmarLabel = 'Confirmar', tom = 'perigo', onConfirmar, onFechar }: { aberta: boolean; titulo: string; descricao: string; confirmarLabel?: string; tom?: 'primario' | 'perigo'; onConfirmar: () => void; onFechar: () => void }) {
  if (!aberta) return null
  return <div className="dialog-backdrop" role="presentation"><div className="dialog" role="dialog" aria-modal="true"><h2>{titulo}</h2><p>{descricao}</p><footer><Botao variante="secundario" onClick={onFechar}>Cancelar</Botao><Botao variante={tom} onClick={onConfirmar}>{confirmarLabel}</Botao></footer></div></div>
}
