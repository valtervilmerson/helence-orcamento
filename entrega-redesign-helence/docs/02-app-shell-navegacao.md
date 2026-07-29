# 02 · App shell e navegação

**Arquivos:** `frontend/src/layout/AppShell.tsx`, `AppShell.css`,
`frontend/src/App.tsx`
**Tela de referência:** qualquer uma (o rail é constante) — DC `telaInicial: 'painel'`

## O que muda conceitualmente

A navegação atual é uma sidebar de 240 px com três grupos de rótulos
(`Vendas`, `Catálogo & Preços`, `Gestão`) e sete links. Ela reflete a
estrutura do banco, não o trabalho do vendedor. Substituir por um **rail
vertical de 84 px, verde `--verde-900`, com 5 destinos**, ícone + rótulo
curto, que sobra espaço para conteúdo em tablet.

## Estrutura do rail (de cima para baixo)

```
[ marca ]   quadrado 34×34, raio 10, fundo --ouro-500,
            letra "h" em --fonte-serif 19px cor --verde-900
            legenda "HELENCE" mono 8px letterspacing .16em cor #7E9A8C

[ Painel      ]  ícone 4 retângulos      → /
[ Orçamentos  ]  ícone documento         → /orcamentos
[ Catálogo    ]  ícone lupa              → /catalogo
[ Importar    ]  ícone seta p/ cima      → /importacoes  + badge

--- espaçador flex ---

[ Ajustes     ]  ícone engrenagem        → /ajustes
[ divisória 1px rgba(255,255,255,.12) ]
[ avatar do usuário ]  círculo 30px, fundo --verde-600, iniciais 11px
                       legenda com primeiro nome 9px cor #7E9A8C
```

- Item **ativo**: fundo `rgba(255,255,255,.13)`, ícone e rótulo `#FFFFFF`.
- Item **inativo**: fundo transparente, cor `#8FAA9C`.
- Hover: `rgba(255,255,255,.07)`.
- Botão: `display:flex; flex-direction:column; align-items:center; gap:5px;
  padding:10px 0; border-radius:12px`. Ícone 20×20 stroke 1.4 `currentColor`.
- Rótulo 10px peso 500.
- **Badge de importação**: posicionado `absolute; top:6px; right:12px`,
  `min-width:17px; height:17px; border-radius:9px`, fundo `--ouro-500`,
  texto `--verde-900` 10px peso 700. Continua alimentado por
  `useImportsBlockingCount` (soma de `items_blocking_publication`) —
  **manter a lógica existente**, só mudar a aparência.
- Regra de visibilidade por papel: manter a mesma matriz de `NAV_GROUPS`,
  agora achatada:

| Destino | Papéis |
|---|---|
| Painel | todos |
| Orçamentos | vendedor, admin |
| Catálogo | todos |
| Importar | importador, revisor, admin |
| Ajustes | admin |

## Remoções

- **Topbar global (`.app-topbar`) e `PageHeaderProvider`/`usePageHeader`
  são eliminados.** Cada tela passa a desenhar o próprio cabeçalho, porque
  o editor de orçamento precisa de um cabeçalho com stepper que a topbar
  genérica não comporta. Apagar `pageHeaderContext.ts`,
  `PageHeaderProvider.tsx`, `usePageHeader.ts` e todas as chamadas.
- **Indicador "API conectada" sai do rail.** Vira um `<AvisoOffline>`
  fixo no rodapé da janela, visível **apenas** quando `apiStatus === 'error'`:
  faixa `--erro-bg`, borda `--erro-borda`, texto "Sem conexão com o
  servidor. Suas alterações não estão sendo salvas."

## Rotas novas (`App.tsx`)

```tsx
<Route path="/"              element={<PainelPage />} />          {/* NOVO */}
<Route path="/orcamentos"    element={<OrcamentosPage />} />      {/* lista */}
<Route path="/orcamentos/:id"          element={<EditorLayout />}>
  <Route index                element={<Navigate to="itens" replace />} />
  <Route path="itens"         element={<EditorItensPage />} />
  <Route path="condicoes"     element={<EditorCondicoesPage />} />
  <Route path="revisao"       element={<EditorRevisaoPage />} />
</Route>
<Route path="/orcamentos/:id/documento" element={<DocumentoPage />} />
<Route path="/catalogo"      element={<CatalogoConsultaPage />} />   {/* era /consulta */}
<Route path="/catalogo/admin" element={<CatalogoAdminLayout />}>...</Route>
<Route path="/importacoes"   element={<ImportacoesPage />} />
<Route path="/importacoes/:id/revisao" element={<FilaRevisaoPage />} />
<Route path="/ajustes"       element={<AjustesPage />} />
```

**Mudança estrutural importante:** hoje o orçamento selecionado vive em
`useState` dentro de `QuotesPage` (arquivo único de 1857 linhas). Passa a
viver **na URL** (`/orcamentos/:id/itens`). Isso é o que permite voltar,
compartilhar link, recarregar sem perder o lugar e separar o arquivo.

## Divisão obrigatória de `QuotesPage.tsx`

O arquivo atual deve ser quebrado em:

```
pages/orcamentos/
  OrcamentosPage.tsx          → doc 04
  editor/EditorLayout.tsx     → cabeçalho + stepper (este doc)
  editor/EditorItensPage.tsx  → doc 05
  editor/ItemCard.tsx         → doc 05
  editor/GavetaMontarItem.tsx → doc 06
  editor/EditorCondicoesPage.tsx → doc 07
  editor/EditorRevisaoPage.tsx   → doc 08
  editor/PainelResumo.tsx     → doc 05 (barra lateral)
  editor/useOrcamento.ts      → hook que carrega quote+itens+totais+checklist
```

`useOrcamento(id)` centraliza o que hoje é o `reload()` de `QuoteDetail`:
`Promise.all([listItems, listFamilies, listFinishes, listDimensions,
getTotals, getReviewChecklist])`. Expor `{ quote, itens, totais, checklist,
carregando, erro, recarregar }`.

## Cabeçalho do editor (`EditorLayout.tsx`)

Fundo `--superficie`, borda inferior `--borda`, `padding: 16px 30px 0`.

Linha 1:
- botão voltar 40×40 raio 11 borda `--borda` → `/orcamentos`;
- coluna: `ORC-2026-0184 · válido até 27 ago` em mono 11.5px cor `--tinta-4`;
  abaixo `<h1>` serif 24px com o **nome do cliente** + `<Selo>` de status;
- à direita: "salvo há 1 min" (mono 12.5px `--tinta-4`), `Botao secundario`
  "Pré-visualizar" → `/documento`, `Botao primario` "Revisar e enviar".

Linha 2 — `<Passos>`:

`1 Cliente (✓) — 2 Itens (n) — 3 Condições comerciais — 4 Revisar e enviar`

- Passo concluído: bolinha 24px `--verde-600` com "✓" branco, rótulo `--tinta-2`.
- Passo atual: bolinha `--verde-900` com número branco, rótulo `--verde-900`
  peso 600, `border-bottom: 2px solid var(--verde-900)` no botão inteiro.
- Passo futuro: bolinha `#EDECE6` com número `--tinta-4`, rótulo `--tinta-4`.
- Conector: linha 34×1px `#DDDBD3`, margem `0 12px 12px`.
- Passo 1 "Cliente" abre um modal de edição de cliente/validade (não é rota).

## Critérios de aceite

- [ ] `usePageHeader` não existe mais no repositório.
- [ ] Recarregar em `/orcamentos/12/condicoes` abre o orçamento 12 na aba certa.
- [ ] O rail tem exatamente 84 px e 5 destinos.
- [ ] O badge de importações continua somando `items_blocking_publication`.
