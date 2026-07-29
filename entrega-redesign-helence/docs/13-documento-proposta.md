# 13 · Documento da proposta (`/orcamentos/:id/documento` + PDF)

**Arquivos:** `pages/orcamentos/DocumentoPage.tsx` (visualização web) e o
gerador de PDF do backend (`backend/app/quotes/`)
**DC:** `telaInicial: 'doc'`

> "O resultado importante é o documento de orçamento para o cliente aceitar
> a proposta." — este documento é o produto final. Ele é a única peça que
> sai da empresa e precisa parecer feita por uma fabricante de mobiliário
> de alto padrão, não por um sistema interno.

## Barra superior (só na web, não no PDF)

Faixa 58px `--verde-900`:
"‹ Voltar ao orçamento" · "Proposta ORC-2026-0184 · página 1 de 2" em mono
`#8FAA9C` · à direita "Baixar PDF" (contorno claro) e **"Enviar ao cliente"**
com fundo `--ouro-500` e texto `--verde-900` — o único CTA dourado do
sistema.

## A folha

Largura 794 px (A4 a 96 dpi), fundo branco, sombra `--sombra-lg`,
`padding: 56px 60px 48px`, centralizada sobre `#DEDCD5`.

### 1. Cabeçalho — borda inferior **2px `--verde-900`**
Esquerda: marca 40×40 raio 11 `--verde-900` com "h" em serif 22px
`--ouro-500`; ao lado "Helence Mobiliário" serif 19px 600 e, abaixo,
"Mesas de reunião sob medida · desde 1998" 11.5px `--tinta-3`.
Direita: "PROPOSTA" mono 11px uppercase `--tinta-4`, número em mono 16px
`--verde-900`, "Emitida em 28/07/2026" 11.5px.

### 2. Duas colunas (`gap:30px`, `padding:24px 0 26px`, borda inferior 1px)

**PREPARADA PARA** — nome do cliente em serif 19px 600 `--verde-900`;
CNPJ, endereço e contato em 12.5px `--tinta-2`, `line-height:1.55`.

**CONDIÇÕES** — 12.5px, `line-height:1.75`, valores em negrito `--tinta`:
Validade da proposta · Prazo de entrega · Pagamento · Consultora
(nome e e-mail do vendedor).

### 3. Itens

Rótulo "ITENS DA PROPOSTA" (10.5px 600 uppercase `letter-spacing:.11em`).
Cabeçalho de tabela com borda inferior **1px `--verde-900`**, texto 10.5px
uppercase `--verde-900`: Descrição · Qtd · Unitário · Total.
Grid `1fr 54px 118px 128px`, `gap:14px`.

Cada linha (`padding:15px 0 14px`, divisória `#EFEEE8`):
- **nome em serif 15px 600** — nunca o rótulo interno com códigos;
- **descrição comercial em 12px `--tinta-2`, `line-height:1.6`**, montada a
  partir dos componentes: *"Tampo em MDF revestido Nogueira, 25 mm, borda
  reta · estrutura metálica Pórtico P900 em pintura eletrostática preta ·
  caixa de tomadas embutida com 4 posições (2 elétricas + 2 USB-C) ·
  passa-fio vertical duplo."*
- números em mono 13px.

**Regra absoluta:** o documento **não** mostra SKU, código de tabela de
preço, custo, margem, confiança de extração, nem a linha por componente com
preço individual. Só o preço de venda da linha. (Documentado em
`AGENTS.md`: dados de auditoria nunca vão para o PDF do cliente.)

⚠ A "descrição comercial" não existe hoje. Implementar como
`descricaoComercial(item)`: concatenar `component.description` de cada
componente na ordem base → complementos, separados por ` · `, com a
primeira letra maiúscula. Se um componente não tiver `description`, usar
`descriptor`. Prever no futuro um campo editável por item.

### 4. Totais (bloco de 330 px alinhado à direita)

```
Subtotal                       R$ 42.501,60
Desconto comercial           − R$  4.581,98    (--verde-600)
──────────────────────────────────────────    (1px --verde-900)
Total da proposta              R$ 37.919,62    (ambos em serif; valor 25px)

┌ bloco --verde-050, raio 8 ──────────────┐
│ Entrada de R$ 10.000,00 e mais          │
│ 6 × R$ 4.653,27         (mono 15px)     │
│ sem juros · primeira parcela 30 dias    │
│ após a entrega                          │
└─────────────────────────────────────────┘
```

Os dois descontos (item + orçamento) são **somados em uma única linha
"Desconto comercial"** — a separação interna não interessa ao cliente.

### 5. Rodapé
Borda superior 1px `--borda`. À esquerda, 11px `--tinta-4`, máx. 380px:
*"Valores em reais, impostos inclusos. Instalação em Curitiba e região
metropolitana inclusa. Esta proposta perde a validade em 27/08/2026."*
À direita, linha de assinatura de 210px com a legenda
"Aceite do cliente · data e assinatura".

## Backend / PDF

O PDF deve ser gerado a partir **do snapshot congelado**, nunca recalculando
(regra atual, manter). Se o gerador for HTML→PDF, reaproveitar exatamente o
markup de `DocumentoPage` com `@page { size: A4; margin: 0 }` e
`padding` da folha convertido para `mm` (56px ≈ 15mm, 60px ≈ 16mm).
As três fontes IBM Plex precisam ser embutidas.

## Critérios de aceite

- [ ] Nenhum SKU, custo, margem ou código de tabela na folha.
- [ ] Cada item tem uma descrição em português comercial, não um rótulo interno.
- [ ] O PDF sai idêntico à visualização web.
- [ ] Há espaço de assinatura para aceite.
