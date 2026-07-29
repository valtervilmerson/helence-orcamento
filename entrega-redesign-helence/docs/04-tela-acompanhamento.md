# 04 · Acompanhamento de orçamentos (`/orcamentos`)

**Arquivo:** `frontend/src/pages/orcamentos/OrcamentosPage.tsx`
(substitui a metade "sidebar" de `QuotesPage.tsx`)
**DC:** `telaInicial: 'lista'`

## O que muda

Sai o layout `grid: 340px 1fr` com lista à esquerda e detalhe à direita.
A lista vira **tela cheia**, e abrir um orçamento é **navegar** para
`/orcamentos/:id/itens`. Motivo: no tablet a coluna de 340px espremia o
detalhe, e o `<details>` de "Finalizados" escondia informação que o usuário
disse ser importante ("acompanhamento de pendentes, finalizados, expirados").

## Cabeçalho

- Sobrelinha mono "Acompanhamento" + `<h1>` serif 28px "Orçamentos".
- À direita `Botao primario lg` "+ Novo orçamento".

## Filtros (linha única, `gap:10px`)

1. **Busca** — caixa 44px, borda `--borda`, raio 12, largura flexível até
   380px, ícone de lupa 16px. Filtra por `quote_number` e `customer.name`
   (mesma lógica de `matchesSearch` hoje).
2. **`<Segmentado>`** dentro de trilho `#EDECE6` raio 12 padding 4:
   `Todos · Rascunho · Com o cliente · Aprovado · Encerrado`, cada um com a
   contagem em mono 11.5px ao lado. Opção ativa: fundo branco, sombra
   `0 1px 2px rgba(0,0,0,.06)`, raio 9, peso 600.
   "Encerrado" agrupa `rejeitado` + `expirado`.

## Corpo — três seções, sempre visíveis

Cada seção tem um cabeçalho `uppercase 12px 600` seguido de uma régua 1px
que ocupa o resto da largura.

| Seção | Cor do cabeçalho/régua | Conteúdo |
|---|---|---|
| **Precisam de atenção** | `--atencao` / `--atencao-borda` | rascunho com pendência, ou enviado expirando em ≤5 dias |
| **Em andamento** | `--tinta-4` / `--borda` | demais rascunhos e enviados + aprovados recentes |
| **Encerrados** | `--tinta-4` / `--borda` | recusados e expirados |

### Linha de orçamento

`grid-template-columns: 152px 1fr 132px 150px 140px 44px`, `gap:12px`,
`padding:14px 16px`, raio 13, cursor pointer.

| Coluna | Conteúdo | Estilo |
|---|---|---|
| 1 | `quote_number` | mono 13px |
| 2 | nome do cliente + **linha de contexto** | 14.5px 600 / 12.5px |
| 3 | total | mono 14px, alinhado à direita |
| 4 | validade ("válido até 27 ago" / "expira em 3 dias") | 12.5px `--tinta-3` |
| 5 | `<Selo>` de status | direita |
| 6 | chevron `›` | 17px `--tinta-5` |

Variações por seção:
- **atenção**: fundo `#FFFDF7`, borda `--atencao-borda`, contexto em `--atencao`;
- **andamento**: fundo `--superficie`, borda `--borda`;
- **encerrados**: fundo `--papel-alt`, borda `#EAE8E1`, textos rebaixados
  para `--tinta-2`/`--tinta-4`.

A **linha de contexto** é gerada, não é campo do banco:
```
rascunho + pendência      → "1 linha incompleta — falta estrutura"
rascunho sem pendência    → "Em montagem — N itens"
enviado                   → "Enviado em 27 jul" ou "Sem resposta há N dias"
aprovado                  → "Aprovado em 26 jul"
rejeitado                 → motivo, se houver; senão "Recusado pelo cliente"
expirado                  → "Validade vencida sem retorno"
```

## Ações destrutivas

O botão "excluir" que hoje fica visível em cada linha **sai**. Excluir passa
a viver no menu `⋯` da tela do orçamento e usa `<ConfirmDialog>` com o
número do orçamento digitado? Não — basta confirmação simples, tom perigo,
texto: *"Excluir ORC-2026-0184? O histórico do orçamento é perdido e esta
ação não pode ser desfeita."* Continua chamando `deleteQuote`.

## Modal "Novo orçamento"

Substitui os dois formulários soltos (`NewQuoteForm` + `NewCustomerForm`)
que hoje ficam abertos na sidebar. Um único diálogo de 520px:

1. **Cliente** — combobox de busca sobre `listCustomers`. Se nada casar,
   a última opção da lista é **"+ Cadastrar «texto digitado»"**, que expande
   os campos Nome / CNPJ-CPF / E-mail / Telefone ali mesmo e chama
   `createCustomer` antes de `createQuote`. Nunca mais dois formulários.
2. **Validade** — `<input type="date">`, pré-preenchido com hoje + validade
   padrão de `getSettings` (doc 15).
3. **Observações** — opcional.
4. Ação primária "Criar e adicionar itens" → `createQuote` →
   `navigate('/orcamentos/' + id + '/itens')`.

## Estados

- **Vazio geral:** `<Vazio titulo="Nenhum orçamento ainda"
  descricao="Crie o primeiro para começar a montar propostas."
  acao="+ Novo orçamento">`.
- **Vazio por filtro:** "Nenhum orçamento com este filtro." + "Limpar filtros".
- **Carregando:** 5 linhas de `<Esqueleto>` na seção "Em andamento".

## Critérios de aceite

- [ ] Nenhum `<details>` escondendo orçamentos finalizados.
- [ ] Clicar em qualquer lugar da linha navega; só o chevron não é botão extra.
- [ ] Criar cliente e orçamento acontece em um único diálogo.
