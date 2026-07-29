# 01 · Fundação — tokens, tipografia e primitivos

## 1. Substituir `frontend/src/styles/tokens.css`

Apagar todo o conteúdo atual e escrever:

```css
:root {
  /* ── Marca ───────────────────────────────────────── */
  --verde-900: #17372A;   /* rail, títulos, cabeçalho do documento */
  --verde-700: #245840;   /* hover de botão primário */
  --verde-600: #2F6F4F;   /* botão primário, links, sucesso de marca */
  --verde-200: #9BB5A6;   /* bordas de destaque suave */
  --verde-100: #E7F0EA;   /* chips e realces */
  --verde-050: #F1F7F3;   /* fundo de bloco informativo */
  --ouro-500:  #E9C97A;   /* acento — logo, CTA sobre verde escuro */

  /* ── Neutros quentes (papel) ─────────────────────── */
  --papel:      #F6F5F1;  /* fundo da aplicação */
  --papel-alt:  #FAF9F6;  /* faixa interna de card, hover de linha */
  --superficie: #FFFFFF;
  --borda:      #E3E1DA;
  --borda-forte:#D6D4CC;  /* bordas de campo de formulário */
  --linha:      #F4F3EE;  /* divisória de linha de tabela */
  --tinta:      #1C211E;  /* texto principal */
  --tinta-2:    #5C635E;  /* texto secundário */
  --tinta-3:    #6E7873;  /* texto de apoio */
  --tinta-4:    #8A8F88;  /* rótulos, metadados */
  --tinta-5:    #B9BDB6;  /* placeholders, chevrons */

  /* ── Estados ─────────────────────────────────────── */
  --ok:        #2F6F4F;  --ok-bg:     #E4EFE7;
  --atencao:   #A9761B;  --atencao-bg:#FBF2E0;  --atencao-borda:#E9D9B0;
  --erro:      #A63A2B;  --erro-bg:   #FBEAE7;  --erro-borda:   #E4B9B0;

  /* ── Layout ──────────────────────────────────────── */
  --rail-largura: 84px;
  --raio-sm: 8px;   --raio-md: 11px;  --raio-lg: 15px;  --raio-xl: 20px;
  --sombra-sm: 0 1px 2px rgba(23,55,42,0.06);
  --sombra-md: 0 6px 16px -8px rgba(23,55,42,0.35);
  --sombra-lg: 0 20px 50px -20px rgba(23,55,42,0.40);

  /* ── Espaçamento (escala 4) ──────────────────────── */
  --e-1: 4px;  --e-2: 8px;  --e-3: 12px; --e-4: 16px;
  --e-5: 20px; --e-6: 26px; --e-7: 34px;

  /* ── Tipografia ──────────────────────────────────── */
  --fonte-ui:    'IBM Plex Sans', system-ui, sans-serif;
  --fonte-serif: 'IBM Plex Serif', Georgia, serif;
  --fonte-mono:  'IBM Plex Mono', ui-monospace, monospace;

  --t-rotulo:  11px;   /* uppercase, letter-spacing .09em */
  --t-micro:   12px;
  --t-apoio:   12.5px;
  --t-corpo:   13.5px;
  --t-base:    14px;
  --t-forte:   15.5px;
  --t-titulo:  20px;
  --t-tela:    28px;
  --t-numero:  34px;
}
```

## 2. Carregar as fontes

Em `frontend/index.html`, dentro de `<head>`:

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Serif:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet" />
```

## 3. Reescrever `frontend/src/index.css`

**Remover obrigatoriamente** (são a causa do "visual genérico"):

- a regra que transforma `section` em card;
- a regra que transforma qualquer `td button` / `li button` em secundário;
- `ul { padding-left: var(--space-5) }`;
- todas as classes `.quotes-*`, `.mode-toggle`, `.metric*`, `.status-bar`,
  `.add-item-panel`, `.totals-card*` — as telas novas não as usam.

**Manter e migrar** (renomeando as variáveis para as novas): `.combobox*`,
`.table-responsive`, `.progress*`.

Base nova:

```css
*, *::before, *::after { box-sizing: border-box; }
html, body, #root { height: 100%; }
body {
  margin: 0;
  font-family: var(--fonte-ui);
  font-size: var(--t-base);
  color: var(--tinta);
  background: var(--papel);
  -webkit-font-smoothing: antialiased;
}
a { color: var(--verde-600); text-decoration: none; }
a:hover { color: var(--verde-900); }
h1, h2, h3 { margin: 0; font-weight: 600; line-height: 1.25; }
h1 { font-family: var(--fonte-serif); font-size: var(--t-tela); color: var(--verde-900); }
h2 { font-size: var(--t-forte); }
h3 { font-size: var(--t-base); }
.mono { font-family: var(--fonte-mono); font-variant-numeric: tabular-nums; }
```

## 4. Primitivos novos (criar em `frontend/src/components/`)

Todos com CSS module ou arquivo `.css` irmão. Nomes exatos:

| Componente | Arquivo | Props | Onde é usado |
|---|---|---|---|
| `Card` | `ui/Card.tsx` | `title?`, `action?`, `padding?: 'none'\|'md'` | todas |
| `Botao` | `ui/Botao.tsx` | `variante: 'primario'\|'secundario'\|'perigo'\|'fantasma'`, `tamanho: 'md'(42px)\|'lg'(46px)\|'sm'(34px)` | todas |
| `Selo` | `ui/Selo.tsx` | `tom: 'neutro'\|'ok'\|'atencao'\|'erro'\|'marca'` | 03,04,05,11,12 |
| `Campo` | `ui/Campo.tsx` | `rotulo`, `sufixo?`, `estado?: 'ok'\|'atencao'\|'erro'` | 06,07,12 |
| `Segmentado` | `ui/Segmentado.tsx` | `opcoes`, `valor`, `onChange` | 04,07 |
| `Passos` | `ui/Passos.tsx` | `passos: {id,label,estado}[]`, `atual` | 05,06,07,08 |
| `Gaveta` | `ui/Gaveta.tsx` | `aberta`, `largura`, `onFechar` | 06 |
| `ConfirmDialog` | `ui/ConfirmDialog.tsx` | `titulo`, `descricao`, `confirmarLabel`, `tom` | 04,05,10 |
| `Vazio` | `ui/Vazio.tsx` | `titulo`, `descricao`, `acao?` | 03,04,09,11 |
| `Esqueleto` | `ui/Esqueleto.tsx` | `linhas` | todas |

### Especificação do `Botao`

| variante | fundo | texto | borda | hover |
|---|---|---|---|---|
| primario | `--verde-600` | #fff | none | `--verde-700` |
| secundario | `--superficie` | `--tinta` | 1px `--borda-forte` | `--papel` |
| perigo | `--erro` | #fff | none | `#8F3024` |
| fantasma | transparent | `--verde-600` | none | `--verde-050` |

Raio `--raio-md`, peso 600, `cursor: pointer`, `:disabled { opacity:.45;
cursor: not-allowed }`.

## 5. Vocabulário

Trocar em **toda a UI** (o banco continua igual — a tradução é só na camada
de apresentação, em um único mapa `labels.ts`):

| Valor no banco | Texto na tela |
|---|---|
| `rascunho` | Rascunho |
| `enviado` | Com o cliente |
| `aprovado` | Aprovado |
| `rejeitado` | Recusado |
| `expirado` | Expirado |
| "markup" | **Margem de venda** |
| "congelar total" | **Congelar valores** |
| "item avulso" | Item avulso |
| "item composto" | **Produto montado** |
| "componente base" | **Peça base** |
| "componente adicional" | **Complemento** |
| "variação" (no fluxo do vendedor) | **Peça** |
| "extracted_item pendente" | Item aguardando revisão |

Criar `frontend/src/labels.ts` exportando `STATUS_LABEL`, `STATUS_TOM`,
`CONFIANCA_LABEL`. Nenhum componente deve escrever esses textos inline.

## Critérios de aceite

- [ ] Nenhum arquivo importa `--color-*` (tokens antigos) — busca global limpa.
- [ ] Nenhum `<section>` depende de estilo implícito.
- [ ] As três famílias IBM Plex carregam (verificar no Network).
- [ ] `Botao` cobre 100% dos botões da aplicação; não sobrou `<button>` cru.
