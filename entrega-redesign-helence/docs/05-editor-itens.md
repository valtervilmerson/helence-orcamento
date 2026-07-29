# 05 · Editor · Itens (`/orcamentos/:id/itens`)

**Arquivos:** `editor/EditorItensPage.tsx`, `editor/ItemCard.tsx`,
`editor/PainelResumo.tsx`
**DC:** `telaInicial: 'itens'`

Esta é a tela onde o vendedor passa mais tempo. Hoje ela é uma `<table>` de
5 colunas com formulários que abrem dentro de `<td colSpan={5}>`. O redesign
troca a tabela por **cards de linha** e move tudo que é edição para fora do
fluxo de leitura.

## Layout

`display:flex` — conteúdo flexível + `<PainelResumo>` fixo de 316 px com
borda esquerda `--borda` e fundo `--superficie`.

Conteúdo: `padding: 22px 26px 28px`, rolagem própria.

### Barra da lista
`<h2>` "N itens no orçamento" · à direita botão **"+ Adicionar item"**:
altura 42, raio 11, **borda tracejada** `1px dashed var(--verde-200)`,
fundo `--verde-050`, texto `--verde-600` 600. Abre a gaveta (doc 06).
Só existe quando `quote.status === 'rascunho'`.

## `<ItemCard>`

Card `--superficie`, borda `--borda`, raio 15, sem sombra.

### Cabeçalho do card (`padding:15px 18px`, `gap:14px`)

1. **Ficha de contagem** 44×44 raio 11: texto `"{n}pç"` em mono 12px.
   - montado → fundo `--verde-100`, texto `--verde-600`;
   - avulso → fundo `#F1F0EA`, texto `--tinta-3`;
   - incompleto → fundo `--erro-bg`, texto `--erro`.
2. **Título** 15.5px 600 + `<Selo>`: "Produto montado" (marca) /
   "Item avulso" (neutro) / "Incompleto" (erro).
3. **Subtítulo** 12.5px `--tinta-3`:
   - montado → "Dimensão travada em {dim} · acabamento {finish}";
   - avulso → o SKU em mono;
   - incompleto → em `--erro`: "Falta a estrutura — sem ela a linha não
     pode ser enviada ao cliente." (usar `missing_required_components`).
4. **Stepper de quantidade** — dois botões 36×36 e o número em mono 14px
   dentro de uma caixa borda `--borda` raio 10. Debounce 500 ms e então
   `updateItem(quoteId, itemId, { quantity })`.
5. **Preço** coluna alinhada à direita, largura mínima 118px:
   total da linha em mono 16px 500; abaixo, em 11.5px `--tinta-4`,
   "R$ X / un." — ou, havendo desconto, "−10% aplicado" em `--verde-600`.
6. **Menu `⋯`** 36×36: *Editar composição · Aplicar desconto · Duplicar
   linha · Remover*. Substitui os botões "Editar"/"Remover" soltos.
7. Quando incompleto, no lugar do preço: `Botao` fundo `--erro`
   **"Completar linha"** que abre a gaveta já no passo 2.

### Rodapé do card — só para produto montado

Faixa `--papel-alt`, borda superior `#EFEEE8`,
`padding: 10px 18px 12px 76px` (o recuo alinha com o título).

Uma linha por componente, grid `62px 1fr 150px 120px`:

| Coluna | Conteúdo |
|---|---|
| 1 | selo `BASE` (fundo `--verde-900`, texto `--ouro-500`, 10px 600) ou `+` (fundo `#EFEEE8`) |
| 2 | descrição da peça, 13.5px |
| 3 | SKU, mono 12px `--tinta-4` |
| 4 | `frozen_unit_price`, mono 13px, direita |

Última linha da faixa — **selo de congelamento**, e este texto é obrigatório:

```
[▪ PREÇO CONGELADO EM 28/07]  Tabela 01-2026 · não muda se o catálogo for atualizado
```

Selo: `--verde-100` / `--verde-600`, 11px 600 uppercase, com um quadrado
6px antes. Texto ao lado 12px `--tinta-4`. Isso resolve a dúvida recorrente
"por que o preço aqui é diferente do catálogo".

### Pendências de preço
`item.pricing_pendencias` continua sendo exibido, agora como faixa
`--erro-bg` de 1 linha logo abaixo do cabeçalho do card.

## `<PainelResumo>` (barra lateral 316 px)

### Bloco 1 — "RESUMO AO VIVO" (rótulo uppercase 12px `--tinta-4`)

```
Custo congelado                    R$ 30.380,00     ← só se mostrarCustoInterno
Margem de venda  32%              + R$  9.721,60    ← idem
Descontos                         −  R$    602,00   (em --verde-600)
────────────────────────────────────────────────
Total                              R$ 39.499,60     (serif 25px --verde-900)
6× sem juros                       R$  6.583,27
```

Dados de `getTotals(quoteId)`. Atualiza a cada mutação de item.
Botão `secundario` de largura total "Ajustar condições" → aba Condições.

> As duas primeiras linhas expõem custo e margem, que **nunca** podem
> aparecer no documento do cliente. Se houver perfil de usuário que não deva
> ver custo, esconder as duas linhas (equivalente à prop
> `mostrarCustoInterno` do DC).

### Bloco 2 — "FALTA PARA ENVIAR"

Cabeçalho com contador `3 de 5` em mono `--atencao`, barra de progresso
5px (`--verde-600` sobre `#EFEEE8`), e a lista do
`getReviewChecklist(quoteId)` — **este endpoint já existe e hoje aparece
enterrado no fim da página como "Checklist de revisão final (RN-18)"**.

- Item OK: bolinha 19px `--verde-600` com "✓", texto `--tinta-3`.
- Item pendente: **destacado** — caixa `#FFFDF7`, borda `--atencao-borda`,
  raio 10, com título 13.5px 600, explicação 12.5px e um link de ação
  "Completar agora →" em `--atencao` que leva ao ponto exato do problema.
- Item futuro (ex.: "Congelar o total"): círculo vazado `--tinta-5`.

Rótulos exigidos (traduzir os `code` do checklist):

| code do backend | Texto na tela |
|---|---|
| cliente/validade | Cliente e validade definidos |
| precos | Todos os itens têm preço na tabela vigente |
| markup/alçada | Margem dentro do limite aprovado |
| linhas incompletas | N linha(s) incompleta(s) |
| snapshot | Congelar o total e gerar o documento |

## Estado "somente leitura"

Quando `quote.status !== 'rascunho'`: esconder "+ Adicionar item", steppers
de quantidade e menu `⋯`; o painel lateral troca o botão por "Duplicar para
editar" (chama `duplicateQuote` — manter o aviso atual de que os preços
serão os de hoje, agora dentro de `<ConfirmDialog>`).

## Critérios de aceite

- [ ] Nenhum formulário abre dentro de uma célula de tabela.
- [ ] O checklist está sempre visível na lateral, não no fim da página.
- [ ] O selo de preço congelado aparece em toda linha montada.
- [ ] Alterar quantidade não recarrega a lista inteira (só os totais).
