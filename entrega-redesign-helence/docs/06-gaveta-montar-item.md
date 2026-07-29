# 06 · Gaveta "Montar item"

**Arquivo:** `editor/GavetaMontarItem.tsx` (substitui `NewItemForm`,
`ComponentPicker`, `VariantCombobox`, `ProductCompositionLoader`,
`EditItemPanel`)
**DC:** `telaInicial: 'montar'`

Esta é a dor número 1 relatada pelo usuário. Hoje o fluxo é: escolher modo
(avulso/composto) → três `<select>` de filtro → um combobox cujo item lê
`"Produto — Componente — descritor — acabamento — SKU — preço"` numa única
string → botão "Selecionar" → repetir para cada complemento. O usuário não
sabe o que está montando enquanto monta.

## Forma

`<Gaveta>` de **780 px**, encostada à direita, sobre um véu
`rgba(23,55,42,.34)`, sombra `-20px 0 50px -20px rgba(23,55,42,.4)`.
Fundo `--papel`. Três regiões fixas: cabeçalho, corpo rolável, rodapé de ação.

## Cabeçalho

- Sobrelinha mono "Adicionar ao ORC-2026-0184".
- `<h2>` serif 23px "Montar item" · botão ✕ 40×40 à direita.
- `<Passos>` interno: **1 Peça base · 2 Complementos · 3 Confirmar**.

O seletor "Item avulso / Produto montado" **desaparece**. O sistema deduz:
se o usuário confirmar com apenas a peça base, é um item avulso; se houver
complementos, é um produto montado. Uma decisão a menos.

## Passo 1 — Peça base

Corpo: busca + filtros + resultados (mesma malha do passo 2, descrita
abaixo), sem o cartão de base no topo.

Acima da busca, um atalho: **"Carregar um produto pronto"** — um
`<select>` de `listProducts()` que chama `getProductComposition(id)` e
salta direto para o passo 3 com todos os componentes preenchidos. É o
`ProductCompositionLoader` atual, promovido a caminho de primeira classe
em vez de ficar escondido no fim do formulário composto.

## Passo 2 — Complementos

### Cartão da base (fixo no topo do corpo)
Fundo `--verde-900`, raio 14, `padding:15px 18px`:
selo `BASE` 40×40 (`rgba(233,201,122,.18)` / `--ouro-500`) · nome da peça
15px 600 branco · `SKU · R$ preço` em mono 11.5px `#8FAA9C` · botão
"Trocar" com borda `rgba(255,255,255,.28)`.

Logo abaixo, fora do cartão, a frase que explica a regra RN-03:

> ▪ A base fixa a dimensão **2400×1200** — só mostramos peças que encaixam nela.

(quadrado 6px `--ouro-500` antes, texto 12.5px `--tinta-3`, dimensão em mono)

### "Já adicionados · N"
Lista de cartões brancos, borda `--borda`, raio 12, `padding:12px 14px`:
ponto 7px `--verde-600` · nome · SKU mono `--tinta-4` · preço mono ·
botão ✕ 32×32 que remove. Peça sem custo mostra "incluso" em vez de R$ 0,00.

### Busca e filtros
- Campo 46px, borda `--borda-forte`, raio 12, placeholder
  "Buscar peça, SKU ou acabamento…", e à direita, em mono 11.5px
  `--tinta-5`, **"142 compatíveis"** — o contador de resultados.
- Chips de 34px, `gap:7px`: `Sugeridas` (ativo: `--verde-900`/branco),
  `Estruturas`, `Elétrica & dados`, `Apoio / credenza`, `Acústica`.
  As categorias vêm de `listComponentTypes()`.
- Chip de filtro herdado (ex.: `Nogueira ✕`) em `--verde-100`/`--verde-600`
  com borda `--verde-200` — clicável para remover.

Chamada: `searchComponents({ family, dimension, finish, finish_group, q,
page_size })`. Manter o debounce de 300 ms só para texto; filtros disparam
na hora (comportamento atual, está correto).

### Resultados — **grade de cartões, não combobox**

`grid-template-columns: 1fr 1fr; gap:10px`. Cada cartão (`--superficie`,
borda `--borda`, raio 13, `padding:13px 14px`, hover borda `--verde-200`):

```
Estrutura Pórtico P900 — Branco          [Combina]
EST-P900-BRC
R$ 3.980,00                          [ + Adicionar ]
```

- Nome 14px 600, `line-height:1.3`.
- Etiqueta: `Combina` (`--verde-100`/`--verde-600`) quando passa nas regras
  de compatibilidade; `Popular` (`--atencao-bg`/`--atencao`) para os mais
  usados; `Sem preço` (`--erro-bg`/`--erro`) — e neste caso o cartão fica
  com opacidade .55 e o botão desabilitado, com tooltip *"Sem preço na
  tabela vigente. Peça a revisão do catálogo antes de orçar."*
- SKU mono 11.5px `--tinta-4`; preço mono 14.5px.

Isso substitui `describeVariant()`, que concatenava seis campos numa
string. **Apagar essa função.**

## Passo 3 — Confirmar

- Campo "Nome do item" pré-preenchido com o nome do produto ou o descritor
  da base (regra atual, manter).
- Resumo das peças com o total unitário.
- Bloco de congelamento, obrigatório, em `--verde-050` raio 10:
  > **R$ 12.480,00** · Este valor é congelado agora e não muda se o catálogo
  > for atualizado depois.

## Rodapé fixo

```
4 peças · preço congelado ao adicionar          Qtd. [− 2 +]   [Adicionar ao orçamento]
R$ 12.480,00  (serif 22px --verde-900)
```

Botão primário 46px. Desabilitado enquanto não houver peça base.
Ao confirmar: `addItem(quoteId, { label, quantity, components })` — mesma
API de hoje — fecha a gaveta e destaca a linha nova por 1,2 s
(`background: --verde-050` esmaecendo).

## Modo "editar composição"

A mesma gaveta abre com os componentes carregados quando o usuário escolhe
"Editar composição" no menu `⋯` de um item. Diferenças:
- usa `addComponent` / `removeComponent` / `swapComponent` por peça;
- ao trocar uma peça, se `swap.price_changed`, mostrar **antes de aplicar**
  um `<ConfirmDialog>`: *"O preço desta peça mudou de R$ 3.980,00 para
  R$ 4.210,00 desde que o item foi adicionado. Recongelar com o valor
  novo?"*;
- remover a última peça pergunta se deve remover a linha inteira (erro
  `ULTIMO_COMPONENTE_DA_LINHA`), agora via `<ConfirmDialog>`, não
  `window.confirm`;
- se `missing_required_components` não estiver vazio, o passo 2 abre com um
  bloco `--erro-bg` no topo listando o que falta e um campo de
  justificativa (`updateItem` → `composition_justification`), exatamente
  como hoje, mas visualmente integrado.

## Critérios de aceite

- [ ] Nenhum `<select>` de família/acabamento/dimensão solto no formulário.
- [ ] O resultado de busca mostra nome, SKU e preço em campos separados.
- [ ] Peça sem preço nunca pode ser adicionada, e o motivo aparece.
- [ ] A dimensão da base filtra os complementos automaticamente (RN-03).
- [ ] `describeVariant` e `VariantCombobox` não existem mais.
