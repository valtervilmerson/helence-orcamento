# 09 · Catálogo · consulta (`/catalogo`)

**Arquivo:** `frontend/src/pages/catalogo/CatalogoConsultaPage.tsx`
(evolução de `pages/catalog/consulta/ConsultaPage.tsx`)
**DC:** `telaInicial: 'catalogo'`

Esta é a tela de **consulta** — o que todo mundo usa. A administração das
entidades vai para `/catalogo/admin` (doc 10) e some do caminho do vendedor.

## Layout

`display:flex`: painel de filtros 234 px (fundo `--superficie`, borda
direita `--borda`) + área de resultados rolável (`padding:22px 26px 28px`).

## Painel de filtros

Título "REFINAR" (uppercase 12px 600 `--tinta-4`), depois quatro grupos
com `gap:18px`:

1. **Linha** — checkboxes de `listFamilies()`, cada um com a contagem em
   mono 11.5px `--tinta-5` alinhada à direita. Caixa 17×17 raio 5;
   marcada = `--verde-600` sólido.
2. **Tipo de peça** — checkboxes de `listComponentTypes()`.
3. **Acabamento** — **amostras de cor 30×30 raio 8**, não uma lista de
   texto. Selecionada ganha borda 2px `--verde-600` e um anel interno
   branco (`box-shadow: 0 0 0 2px #fff inset`). Abaixo, o nome do
   acabamento escolhido em 12.5px `--tinta-4`.
   ⚠ `Finish` não tem campo de cor hoje. Duas opções: (a) adicionar
   `hex` à tabela `finishes` (`⚠ MIGRAÇÃO`), ou (b) mapa estático
   `FINISH_HEX` em `labels.ts` cobrindo os acabamentos existentes, com
   cinza `#9BA39C` como padrão. Começar por (b).
4. **Dimensão** — chips com `raw_label` em mono 12px, borda `--borda-forte`;
   ativo `--verde-100` com borda `--verde-600`.

## Cabeçalho de resultados

- Sobrelinha mono: **"Tabela 01-2026 · vigente desde 12/01"** — o usuário
  precisa saber qual tabela está vendo. Vem de `getSettings`/price_table.
- `<h1>` serif 26px "Catálogo".
- Busca 340×44 à direita: "Buscar SKU, peça ou descritor…".
- Linha de contexto: **"28 variações em Nogueira · 2400×1200"** seguida dos
  chips de filtro ativo, cada um removível (`Nogueira ✕`).

## Tabela de resultados

Card raio 15, grid `1fr 168px 116px 132px 122px`:

| Coluna | Conteúdo |
|---|---|
| Peça | nome 14px 500 + tipo/descrição 12px `--tinta-4` em duas linhas |
| SKU | mono 12.5px |
| Dimensão | mono 12.5px |
| Preço tabela | mono 14px, direita |
| — | `Botao sm secundario` **"+ Orçamento"** |

Hover da linha: `--papel-alt`.

**"+ Orçamento"** é a ponte que hoje não existe direito: abre um seletor de
orçamento em rascunho (ou "criar novo") e chama `addItem`. Se o usuário
veio de um orçamento (`?voltarPara=/orcamentos/12/itens`), o botão adiciona
direto e volta.

Variação **sem preço**: preço em `--erro` com o texto "sem preço" e o botão
desabilitado com a explicação em tooltip. Regra de negócio existente: item
sem preço nunca entra em orçamento.

## Removido

- A edição inline de variação (`PATCH /components/{id}`) **sai desta tela**
  e vai para `/catalogo/admin` (doc 10). Consulta é leitura.
- O link de auditoria continua, agora no menu `⋯` de cada linha:
  "Ver origem do preço".

## Estados

- Sem filtro e sem busca: mostrar as variações da tabela vigente paginadas
  (25 por página), não uma tela vazia.
- Nenhum resultado: `<Vazio>` com "Nenhuma peça com estes filtros" +
  "Limpar filtros".

## Critérios de aceite

- [ ] O código da tabela de preço vigente é visível sem clique.
- [ ] Acabamento é escolhido por amostra de cor.
- [ ] Toda linha oferece um caminho de uma ação para o orçamento.
