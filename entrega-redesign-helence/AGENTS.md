# Redesign Helence Orçamento — pacote de entrega

Leia este arquivo primeiro. Ele diz o que existe aqui e em que ordem usar.

## O que é

O sistema **Helence Orçamento** (FastAPI + SQLite no backend, React +
TypeScript + Vite no frontend) foi redesenhado: nova identidade visual e um
fluxo de orçamento reorganizado em etapas. Este pacote contém **a referência
visual** e **as instruções de implementação tela a tela**, suficientes para
aplicar o redesign no repositório existente sem acesso ao designer.

O redesign não altera o modelo de dados nem as regras de negócio. Salvo os
poucos pontos marcados com `⚠ NOVO ENDPOINT` / `⚠ MIGRAÇÃO`, todos os dados
necessários já são servidos pelos módulos em `frontend/src/api/`.

## Conteúdo

```
entrega-redesign-helence/
├── AGENTS.md                        ← este arquivo
├── referencia-visual/
│   ├── Helence Orçamento.dc.html    ← FONTE DA VERDADE VISUAL
│   └── support.js                   ← runtime necessário para abrir o arquivo acima
└── docs/
    ├── README.md                    ← índice + ordem de implementação
    ├── 01-fundacao-tokens.md        ← tokens, tipografia, primitivos, vocabulário
    ├── 02-app-shell-navegacao.md    ← rail, rotas, quebra de QuotesPage.tsx
    ├── 03-tela-painel.md
    ├── 04-tela-acompanhamento.md
    ├── 05-editor-itens.md
    ├── 06-gaveta-montar-item.md
    ├── 07-editor-condicoes.md
    ├── 08-editor-revisar-enviar.md
    ├── 09-catalogo-consulta.md
    ├── 10-catalogo-admin.md
    ├── 11-importacoes.md
    ├── 12-fila-revisao.md
    ├── 13-documento-proposta.md
    ├── 14-login.md
    └── 15-ajustes.md
```

## Como abrir a referência visual

`referencia-visual/Helence Orçamento.dc.html` abre direto no navegador
(mantenha `support.js` na mesma pasta). Todas as telas estão no mesmo
arquivo; a fileira de botões no topo troca de tela.

O desenho é para **tablet em paisagem**, 1194 × 834 px — o dispositivo de
uso principal. As medidas dos documentos referem-se a essa base.

**Sempre que este pacote e o arquivo divergirem, o arquivo vence.** Compare
visualmente cada tela antes de considerar a implementação concluída.

## Como executar o trabalho

1. Leia `docs/README.md` — ele traz a tabela de dependências.
2. Implemente `docs/01` e `docs/02` **antes de qualquer tela**. Eles
   substituem os tokens, removem o CSS implícito de `index.css` (a regra que
   transforma todo `<section>` em card), criam os primitivos de UI e
   reorganizam as rotas. Nenhuma tela funciona corretamente sem eles.
3. Depois, siga a ordem 03 → 15. Cada documento é autossuficiente e termina
   com uma lista de critérios de aceite — use-a como definição de pronto.
4. Ao final de cada tela, abra a tela correspondente na referência visual e
   compare lado a lado.

## Decisões que já estão tomadas (não reabrir)

- **A navegação foi repensada do zero**: cinco destinos em um rail de 84 px,
  no lugar dos três grupos e sete links atuais.
- **O orçamento selecionado passa a viver na URL** (`/orcamentos/:id/itens`),
  não em `useState`. `QuotesPage.tsx` (1857 linhas) é dividido em oito
  arquivos — ver `docs/02`.
- **A montagem de item vira uma gaveta guiada em três passos**, e o seletor
  "avulso / composto" deixa de existir: o sistema deduz pelo número de peças.
- **Condições comerciais viram uma etapa do fluxo**, com a cascata de cálculo
  visível ao lado dos controles.
- **O checklist de revisão fica permanentemente na lateral do editor**, e o
  botão de envio explica por que está desabilitado.
- **O documento do cliente não mostra SKU, custo, margem, código de tabela de
  preço nem dados de confiança de extração.**

## Pontos que dependem de backend

Estão marcados nos documentos e concentrados aqui para planejamento:

| Item | Documento | Situação |
|---|---|---|
| `GET /quotes/summary` (contagens e somas por status) | 03 | tem fallback no cliente |
| `POST /quotes/{id}/send` + página pública de aceite | 08 | opcional; esconder o cartão se não houver |
| `settings.discount_limit_percent` | 07, 15 | usar constante provisória (8%) |
| `settings.default_validity_days` | 04, 15 | usar constante provisória (30 dias) |
| `finishes.hex` (cor do acabamento) | 09 | usar mapa estático provisório |
| Motivo obrigatório no `PATCH /components/{id}` | 10 | registrar no log de auditoria existente |

Nenhum deles bloqueia a implementação visual.
