# 14 · Login (`/login`)

**Arquivos:** `pages/auth/LoginPage.tsx`, `LoginPage.css`
**DC:** `telaInicial: 'login'`

Tela cheia, sem rail. `display:flex`.

## Painel esquerdo — 46% da largura

Fundo `--verde-900`, `padding:46px 44px`, `justify-content:space-between`:

1. **Topo** — marca: quadrado 36×36 raio 10 `--ouro-500` com "h" serif 20px
   `--verde-900`, ao lado "Helence" serif 18px 600 branco.
2. **Meio** — a promessa do produto:
   - serif 34px 600 branco, `line-height:1.25`, `text-wrap:pretty`:
     **"Do catálogo à proposta assinada, sem retrabalho."**
   - 14.5px `#A9C2B4`, `line-height:1.6`, máx. 380px:
     *"Preços congelados no instante em que entram no orçamento. O que você
     mostrou ao cliente continua valendo."*
3. **Rodapé** — mono 11px `letter-spacing:.1em` `#567A69`:
   **"TABELA VIGENTE 01-2026"** (buscar de `/health` ou de um endpoint
   público; se não houver, omitir — não inventar).

## Painel direito

Fundo `--papel`, formulário centralizado de 340px, `gap:18px`:
- `<h1>` serif 25px "Entrar" + 13.5px `--tinta-3` "Use o e-mail da Helence.";
- campos E-mail e Senha: rótulo uppercase 12px 600 `--tinta-4`, caixa 48px,
  borda `--borda-forte`, raio 11, fonte 15px;
- `Botao primario` 50px de largura total "Entrar";
- 13px `--tinta-4` centralizado: "Esqueceu a senha? Fale com o administrador."

## Comportamento

- Erro de credencial: faixa `--erro-bg` acima do botão, texto
  *"E-mail ou senha incorretos."* — nunca revelar qual dos dois.
- `Enter` submete; o botão mostra "Entrando…" e fica desabilitado.
- Após entrar, ir para `/` (Painel), não para `/orcamentos`.

## Critérios de aceite

- [ ] Nenhuma menção a papéis/usuários de seed na tela.
- [ ] Os dois painéis funcionam em tablet retrato (o esquerdo vira uma
      faixa de 160px de altura no topo abaixo de 900px de largura).
