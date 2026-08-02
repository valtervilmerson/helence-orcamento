# Redesign Helence Orçamento — pacote de implementação

Este diretório descreve, tela a tela, **como transformar o frontend atual
(`frontend/src/`) no design refeito**. Foi escrito para ser executado por um
agente de IA sem contexto prévio do produto.

## Arquivo de referência visual

`Helence Orçamento.dc.html` (raiz deste projeto) é a **fonte da verdade
visual**. Ele contém todas as telas em um único arquivo, navegáveis pelos
botões no topo. Sempre que este texto e o arquivo divergirem, **o arquivo
vence**. Abra-o e compare pixel a pixel ao implementar.

Cada tela do DC tem uma prop `telaInicial` para abrir direto naquela tela:
`painel · lista · itens · montar · condicoes · revisao · catalogo · admin ·
import · fila · ajustes · doc · login`.

## Ordem de implementação recomendada

| # | Documento | Depende de |
|---|---|---|
| 01 | [Fundação: tokens e primitivos](01-fundacao-tokens.md) | — |
| 02 | [App shell e navegação](02-app-shell-navegacao.md) | 01 |
| 03 | [Painel (nova rota `/`)](03-tela-painel.md) | 02 |
| 04 | [Acompanhamento de orçamentos](04-tela-acompanhamento.md) | 02 |
| 05 | [Editor · Itens](05-editor-itens.md) | 02, 04 |
| 06 | [Gaveta "Montar item"](06-gaveta-montar-item.md) | 05 |
| 07 | [Editor · Condições comerciais](07-editor-condicoes.md) | 05 |
| 08 | [Editor · Revisar e enviar](08-editor-revisar-enviar.md) | 05, 07 |
| 09 | [Catálogo · consulta](09-catalogo-consulta.md) | 02 |
| 09b | [Correção: filtro de dimensão do Catálogo](09b-correcao-filtro-dimensao.md) | 09 |
| 10 | [Catálogo · administração](10-catalogo-admin.md) | 09 |
| 11 | [Importações](11-importacoes.md) | 02 |
| 12 | [Fila de revisão](12-fila-revisao.md) | 11 |
| 13 | [Documento da proposta (PDF)](13-documento-proposta.md) | 07 |
| 14 | [Login](14-login.md) | 01 |
| 15 | [Ajustes](15-ajustes.md) | 02 |

Os documentos 01 e 02 são **pré-requisito obrigatório** — todos os outros
assumem que os tokens e o shell novos já existem.

## Regras que valem para todas as telas

1. **Nada de mudança de backend.** Todos os endpoints já existem em
   `frontend/src/api/*`. Se uma tela precisar de um dado que não existe,
   isso está marcado explicitamente como `⚠ NOVO ENDPOINT` no documento.
2. **Nenhum `section` genérico vira card automaticamente.** O CSS atual
   (`index.css`) transforma qualquer `<section>` em card. Isso é removido
   na Fundação; a partir dali cards são explícitos (`.card`).
3. **Alvos de toque ≥ 44 px de altura.** O produto roda em tablet.
4. **Números sempre em `IBM Plex Mono`** com `font-variant-numeric:
   tabular-nums`. Texto corrido em `IBM Plex Sans`. Títulos e valores de
   destaque em `IBM Plex Serif`.
5. **Vocabulário do usuário, não do banco.** Ver a tabela de renomeações em
   [01-fundacao-tokens.md](01-fundacao-tokens.md#vocabulário).
6. **Sem `window.confirm` / `window.alert`.** Toda confirmação usa o
   componente `<ConfirmDialog>` descrito na Fundação.
