# 07 · Editor · Condições comerciais (`/orcamentos/:id/condicoes`)

**Arquivo:** `editor/EditorCondicoesPage.tsx` (substitui `QuoteSettingsForm`)
**DC:** `telaInicial: 'condicoes'`

Hoje isto é um formulário que só aparece depois de clicar em "Ajustar
markup, descontos e parcelas", no fim da página, com 4 blocos de `<select>`
e `<input>` sem explicação. O usuário relatou que "descontos/markup/
parcelamento são escondidos e confusos". Vira uma **etapa própria do fluxo**,
com o cálculo mostrado ao lado em tempo real.

## Layout

`grid-template-columns: 1fr 372px; gap:20px; align-items:start`,
`padding:22px 30px 30px`. A coluna direita é `position:sticky; top:0`.

## Coluna esquerda — três cards

### Card 1 · Margem de venda
- `<h2>` "Margem de venda" + à direita, mono 12px `--tinta-4`:
  "aplicada sobre o custo congelado".
- Parágrafo 13px `--tinta-3`: *"É o que transforma o custo de catálogo no
  preço de venda. O padrão da empresa é 32%."* (o número vem de
  `getSettings().global_markup_percent`).
- Duas opções lado a lado (rádio grande, 100% clicável):
  - **Padrão da empresa · 32%** — "Acompanha mudanças de política"
    (= `markup_uses_global: true`);
  - **Margem específica** — "Só para este orçamento" — ao selecionar,
    revela um campo numérico com sufixo %.
  Opção ativa: borda 1.5px `--verde-600`, fundo `--verde-050`, marcador
  com anel de 5px.

### Card 2 · Desconto
- Parágrafo dinâmico: *"Você já concedeu **R$ 602,00** em descontos de item.
  Este é o desconto sobre o orçamento inteiro."* (soma de
  `totals.item_discount_amount`) — isso resolve a confusão entre os dois
  níveis de desconto.
- `<Segmentado>` **Nenhum · Percentual · Valor R$** → mapeia para
  `quote_discount_percent` / `quote_discount_amount`.
- Campo de valor (120px) com sufixo % ou prefixo R$.
- Campo **"Motivo (fica no histórico)"** ocupando o resto da linha →
  `quote_discount_reason`.
- Faixa de alçada, calculada contra `settings`:
  - dentro do limite → `--verde-050`, ponto `--verde-600`:
    *"Dentro do seu limite de alçada (até 8%). Acima disso, precisa da
    aprovação do gestor."*;
  - acima → `--atencao-bg`, borda `--atencao-borda`:
    *"18% ultrapassa seu limite de 8%. O orçamento vai para aprovação do
    gestor antes de poder ser enviado."* e o campo de motivo passa a ser
    **obrigatório** (borda `--erro-borda` se vazio).

### Card 3 · Pagamento
- **Entrada** — campo com prefixo R$ (ou %, via um pequeno toggle) →
  `entrada_amount` / `entrada_percent`.
- **Parcelas** — botões rápidos `1× 3× 6× 10×` (44×42, raio 10) + "outro"
  que abre input numérico. Ativo: borda 1.5px `--verde-600`, fundo
  `--verde-100`. → `installment_count`.
- **Juros ao mês** — só aparece quando `parcelas > 1` →
  `installment_interest_percent`.

## Coluna direita — "COMO O NÚMERO SE FORMA"

Card sticky. **A cascata inteira, sempre visível**, sem esconder linhas
zeradas de custo/margem (só descontos zerados somem):

```
Custo congelado · 3 itens             R$ 30.380,00
Margem 32%                          + R$  9.721,60
──────────────────────────────────────────────────
Preço de tabela                       R$ 40.101,60
Descontos de item                   −  R$    602,00   (verde)
Desconto do orçamento · 4%          −  R$  1.579,98   (verde)
──────────────────────────────────────────────────
Total                                 R$ 37.919,62   (serif 27px --verde-900)
```

Rodapé do card, faixa `--papel-alt`: **"COMO O CLIENTE VAI PAGAR"**
```
Entrada                               R$ 10.000,00
Saldo em 6×                           R$  4.653,27   (mono 15px --verde-900)
Sem juros · primeira parcela 30 dias após a entrega.
```

Dois botões no fim: `secundario` "Voltar" → `/itens`; `primario`
"Revisar" → `/revisao`.

## Salvamento

Autosave com debounce de 600 ms chamando `updateQuoteSettings(quote.id, …)`
com o payload atual (mesmos campos de hoje). Indicador "salvo há N" no
cabeçalho do editor. **Remover o botão "Salvar configurações"** — não há
nada a confirmar aqui, e o cálculo já dá o feedback.

## Critérios de aceite

- [ ] Condições é uma etapa navegável, não um painel colapsado.
- [ ] A cascata mostra as duas camadas de desconto separadamente.
- [ ] Desconto acima da alçada exige justificativa e avisa o que acontece.
- [ ] Nenhum campo muda de posição ao alternar tipo de desconto.
