# 08 · Editor · Revisar e enviar (`/orcamentos/:id/revisao`)

**Arquivo:** `editor/EditorRevisaoPage.tsx`
**DC:** `telaInicial: 'revisao'`

Hoje "congelar total" e "exportar PDF" são dois botões cinzas no fim de um
card chamado "Resumo", e o checklist mora em outro card acima. O usuário
disse não entender *o que falta para poder congelar/exportar*. Esta tela
existe só para responder isso.

## Layout

`grid-template-columns: 1fr 400px; gap:22px`, `padding:22px 30px 30px`.

## Coluna esquerda

### 1. Faixa de veredito
Bloco `--verde-900`, raio 15, `padding:20px 22px`:
- quadrado 52×52 `rgba(233,201,122,.16)` com o número de itens OK em serif
  22px `--ouro-500`;
- título serif 20px branco e subtítulo 13.5px `#A9C2B4`.

| Situação | Título | Subtítulo |
|---|---|---|
| tudo OK | "Pronto para enviar" | "As 5 verificações passaram. O documento já reflete estes valores." |
| 1 pendência | "Falta uma coisa antes de enviar" | "4 de 5 verificações concluídas. Resolva a pendência abaixo e o envio libera sozinho." |
| 2+ | "Faltam N coisas antes de enviar" | idem, com o número |

### 2. Card do checklist
Uma linha por item de `getReviewChecklist`, `padding:15px 20px`, divisória
`--linha`:
- **OK**: bolinha 22px `--verde-600` com ✓, título 14.5px 600 e, embaixo,
  **a evidência** em 12.5px `--tinta-3` — não basta dizer que passou:
  - Cliente → "Grupo Sanders · CNPJ … · compras@…"
  - Preços → "Tabela 01-2026 vigente · congelada em 28/07/2026"
  - Desconto → "4% no orçamento + R$ 602,00 em itens · justificado"
  - Validade/pagamento → "Válido até 27/08/2026 · entrada + 6× sem juros"
- **Pendente**: fundo da linha `#FFFDF7`, círculo vazado `--atencao`,
  descrição do problema e **dois botões à direita**: `secundario`
  "Justificar" (abre campo de justificativa) e `Botao` `--atencao`
  "Completar" (leva ao ponto exato).

### 3. Card "Como enviar"
Três opções em cartões clicáveis de largura igual:

| Opção | Descrição | Efeito |
|---|---|---|
| **E-mail com link** | "O cliente abre, lê e aceita pelo navegador. Você vê quando ele abriu." | ⚠ NOVO ENDPOINT |
| **Baixar PDF** | "Para anexar você mesmo ou imprimir." | `exportQuotePdf` (já existe) |
| **Só congelar** | "Trava os valores e envia depois." | `freezeTotals` |

⚠ **"E-mail com link" depende de backend novo** (`POST /quotes/{id}/send`
+ rota pública de aceite). Se não for implementado agora, **esconder o
cartão** — não deixar um botão que não faz nada. As outras duas opções
cobrem o fluxo atual.

## Coluna direita (sticky)

### 1. Prévia do documento
Card com cabeçalho "PRÉVIA DO DOCUMENTO" + link "Abrir →".
Corpo: fundo `#EDECE6`, `padding:18px`, contendo uma miniatura de papel
branco com sombra — logo, número do orçamento, título "Proposta comercial",
faixas cinza representando o texto e o total em mono no canto. Clicar abre
`/orcamentos/:id/documento` (doc 13).

### 2. Card de fechamento
```
Total da proposta            R$ 37.919,62   (serif 26px --verde-900)
[      Congelar e enviar      ]   ← 50px, largura total
Libera quando as 5 verificações passarem.
```
Botão desabilitado enquanto `checklist.ready === false`: fundo `#C7CFC8`,
texto `--papel`, `cursor:not-allowed`, e a legenda explica o porquê.
Habilitado: `--verde-600`, e a legenda vira "Os valores serão congelados
neste momento."

Ao clicar: `freezeTotals(quoteId)` → `updateQuoteStatus(quoteId,
'enviado')` → toast "Orçamento enviado" → navegar para `/orcamentos`.

## Transições de status

A `status-bar` atual (uma fileira de botões com os nomes crus dos estados:
`rascunho → enviado → rejeitado → expirado`) **é removida**. Ela expunha a
máquina de estados do banco. Substituição:

- A transição `rascunho → enviado` acontece pelo botão desta tela.
- As demais (`aprovado`, `rejeitado`, `expirado`) viram um controle
  **"Registrar resposta do cliente"** no cabeçalho do editor, disponível só
  quando o status é `enviado`: três botões — "Cliente aprovou",
  "Cliente recusou", "Marcar como expirado" — cada um com confirmação e,
  para recusa, um campo opcional de motivo. Mantêm-se as mesmas chamadas a
  `updateQuoteStatus` e as mesmas regras de `STATUS_TRANSITIONS`.

## Critérios de aceite

- [ ] O usuário nunca vê a palavra "snapshot", "RN-18" ou "freeze".
- [ ] O botão de envio explica por que está desabilitado.
- [ ] Cada verificação aprovada mostra a evidência, não só um ✓.
- [ ] Não existe mais uma fileira de botões com nomes de status crus.
