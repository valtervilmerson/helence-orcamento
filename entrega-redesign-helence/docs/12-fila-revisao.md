# 12 · Fila de revisão (`/importacoes/:id/revisao`)

**Arquivo:** `pages/importacoes/FilaRevisaoPage.tsx`
(reescrita de `pages/imports/review/ReviewPage.tsx`, 1011 linhas)
**DC:** `telaInicial: 'fila'`

Tela do revisor. Princípio do produto: *nenhum preço entra no catálogo sem
decisão humana, e toda decisão fica registrada.* O layout precisa deixar
óbvio **o que a máquina leu** × **o que vai ser gravado**.

## Layout

`display:flex`: lista de 396 px à esquerda (fundo `--superficie`, borda
direita) + painel de detalhe à direita (`padding:22px 26px 26px`).

## Coluna esquerda

### Cabeçalho (`padding:22px 20px 14px`)
- botão voltar 34×34 → `/importacoes`;
- sobrelinha mono com o nome do arquivo; `<h1>` serif 20px "Fila de revisão";
- barra de progresso 6px + `124/131` em mono;
- busca 40px "Buscar SKU ou descrição…";
- chips de filtro: **Pendentes (n) · Baixa (n) · Média (n) · Decididos**
  (`review_status` e `confidence_level` já existem na API).

### Lista
Cada item é um cartão `padding:12px 13px`, raio 12, `margin-bottom:8px`:
- checkbox 18×18 (seleção múltipla para lote);
- SKU em mono 12px;
- descrição 13px `--tinta-2`;
- **motivo** 12px `--atencao` — a frase que explica por que caiu na fila
  ("Sem preço e acabamento novo", "Dimensão não reconhecida", "Preço fora
  do padrão da linha (+62%)"). Derivar de `import_warnings` /
  `extraction_notes`; nunca deixar em branco.
- selo de confiança à direita: `baixa` `--erro-bg`/`--erro`,
  `média` `--atencao-bg`/`--atencao`, `alta` `--ok-bg`/`--ok`;
  10.5px 700 uppercase.
- Item selecionado: borda 1.5px `--verde-900`, fundo `--verde-050`.

### Rodapé de lote
"N selecionados" à esquerda; à direita `Botao secundario` **"Rejeitar"**
(texto `--erro`) e `Botao primario` **"Aprovar em lote"**.
Rejeitar em lote **exige justificativa** (regra existente) — abre diálogo
com campo obrigatório.

## Painel de detalhe

### Cabeçalho
SKU em serif 22px + selo de confiança; abaixo, em 13px `--tinta-3`:
"Página 14 da planilha · linha 218 · item 128 de 131".
À direita, navegação `‹` `›` entre itens (40×40).

### Faixa "Por que caiu na revisão"
Bloco `#FFFDF7`, borda `--atencao-borda`, raio 13, com ponto `--atencao`,
título 13.5px 600 e explicação 13px em linguagem natural:
> *"A célula de preço estava vazia na planilha e o acabamento 'CRV' não
> existe no catálogo. Nada entra no catálogo enquanto isso não for decidido
> por uma pessoa."*

### Comparação lado a lado (`grid: 1fr 1fr; gap:16px`)

**Esquerda — "COMO VEIO DA PLANILHA"** (fundo `#F1F0EA`, borda `--borda`,
raio 14, marcado "somente leitura" em mono 11px):
linhas `campo (118px, 12.5px --tinta-4)` + `valor (mono 12.5px)`.
Campos: Descrição, SKU, Preço, Acabamento, Dimensão, Tipo — os
`*_raw` de `ExtractedItem`. Valor problemático é colorido:
`(célula vazia)` em `--erro`, valor desconhecido em `--atencao`.

**Direita — "COMO VAI PARA O CATÁLOGO"** (fundo `--superficie`, rótulo em
`--verde-600`, marcado "editável"):
campos de formulário 42px de altura, raio 10, borda `--borda-forte`, na
ordem Tipo de componente · Descrição · [Dimensão | Acabamento] ·
[SKU | Preço]. Campos em estado especial:
- **acabamento novo** → borda 1.5px `#D8BE7C`, fundo `#FFFDF7`, rótulo
  "Acabamento · novo" em `--atencao`, com a ação "criar" à direita;
- **preço faltando** → borda 1.5px `--erro-borda`, fundo `#FFFBFA`, rótulo
  "Preço · faltando" em `--erro`.

Rodapé do card direito, faixa `--papel-alt` — **a correção em lote**, que
hoje é um modal separado (`BatchCorrectionModal`) e passa a ser uma caixa
de seleção sempre visível:
> ✓ Aplicar a mesma correção de acabamento aos **14 itens** com "CRV" nesta
> importação. Itens já decididos por alguém não serão tocados.

O número vem de `previewBatchCorrection(itemId, field, scope)`.
O escopo (`page` / `page_profile` / `import`) vira um pequeno seletor
inline dentro dessa frase — "nesta página / neste tipo de página / nesta
importação". Manter a proteção de `already_decided_count`; o texto acima
é a explicação dela.

### Barra de ações
```
[Rejeitar item]                Toda decisão fica registrada com seu nome e horário.   [Pular]  [Aprovar corrigido →]
```
- "Rejeitar item" → `--erro`, abre campo de justificativa obrigatória.
- "Aprovar corrigido →" → `reviewExtractedItem` com `corrigido` se houve
  edição, `aprovado` se não. Após aprovar, **avançar automaticamente** para
  o próximo item pendente — o revisor não deve voltar à lista a cada item.

## Critérios de aceite

- [ ] O bruto e o normalizado ficam visíveis ao mesmo tempo, lado a lado.
- [ ] Todo item na fila mostra em uma frase por que está lá.
- [ ] A correção em lote mostra a contagem antes de aplicar e diz que itens
      já decididos são preservados.
- [ ] Aprovar avança para o próximo item sem cliques extras.
