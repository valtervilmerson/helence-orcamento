# Status operacional e continuação do redesign

> **Leitura obrigatória antes de alterar frontend, settings ou PDF.**
> Atualizado em 2026-07-28. Este documento descreve o estado real da branch
> `main`; consulte `git status --short` antes de iniciar uma nova alteração.

## Fonte de verdade visual

- Especificação: `entrega-redesign-helence/docs/01` a `15`.
- Referência visual prioritária: `entrega-redesign-helence/referencia-visual/Helence Orçamento.dc.html`.
- Base de uso: tablet em paisagem, 1194×834. Quando especificação e HTML
  divergirem, o HTML vence.

## Estado atual

### Concluído nesta branch

- Fundação visual: tokens Helence, IBM Plex, `labels.ts` e primitivos em
  `frontend/src/components/ui.tsx` (`Botao`, `Card`, `Selo`, `Vazio`,
  `Esqueleto`, `ConfirmDialog`).
- Shell: rail de 84 px, cinco destinos, permissões por papel, badge de itens
  de importação bloqueantes e aviso offline.
- Rotas: `/`, `/orcamentos`, `/orcamentos/:id/{itens,condicoes,revisao}`,
  `/orcamentos/:id/documento`, `/catalogo`, `/catalogo/admin`,
  `/importacoes` e `/ajustes`.
- Painel, acompanhamento, editor e prévia web foram criados como base
  navegável. O editor agora usa `useOrcamento.ts` como fonte compartilhada,
  mostra cards de itens, altera quantidade e salva condições comerciais na
  API. Eles **não** completam ainda a especificação visual/todas as
  interações de `entrega-redesign-helence`.
- Backend: migration `0020_commercial_policy_settings.sql` cria
  `discount_limit_percent=8` e `default_validity_days=30`; `GET/PATCH
  /api/v1/settings` expõe esses campos; `GET /api/v1/quotes/summary` devolve
  contagens/totais por status, `expirando_7d` e `pendencias`.
- Verificações executadas: `npm run build`, `python -m compileall app` e
  `git diff --check` passaram. `pytest` não foi executado porque o comando
  não estava disponível no PATH da sessão.

### Preservado e obrigatório

- Importação ativa é JSON estruturado; o pipeline PDF legado não pode ser
  removido.
- RN-04, RN-12, RN-14 e RN-16 continuam inalteradas.
- O PDF do backend ainda é o anterior; ele precisa ser redesenhado antes de
  declarar a proposta pronta para uso externo.

## Lacunas conhecidas — não tratar como concluídas

1. `EditorItemsPage` já mostra cards e permite quantidade, mas ainda não tem
   menus de item, desconto por item, edição de composição ou gaveta guiada.
2. `EditorConditionsPage` já persiste margem, desconto, entrada e parcelas,
   mas o salvamento ainda é manual; migrar para autosave com debounce de 600
   ms e indicador de “salvo há N”. Não remover `QuoteSettingsForm` até essa
   migração estar completa.
3. A revisão não tem evidências completas por checklist, resposta do cliente
   ou confirmações para transições.
4. Catálogo, administração, importações, fila de revisão, ajustes e login
   ainda usam majoritariamente telas antigas.
5. `ConfirmDialog` existe, mas componentes legados ainda usam
   `window.confirm`; migrar por fluxo.
6. `PageHeaderProvider` saiu do shell, mas telas legadas chamam
   `usePageHeader`; o contexto é no-op seguro até cada tela ser migrada.
7. O Painel ainda usa `listQuotes`; trocar para `quotes/summary` e manter
   fallback limitado a 30 orçamentos apenas se necessário.
8. A prévia web não é a fonte do PDF. `backend/app/quotes/export.py` ainda
   expõe detalhes internos proibidos no documento do cliente.

## Próximas etapas, na ordem obrigatória

### 1. Estabilizar a base

- Executar `python -m pytest tests/integration/ -v` em ambiente com as
  dependências instaladas; adicionar testes para migration 0020, settings e
  `GET /quotes/summary`.
- Confirmar login, `/`, `/orcamentos`, `/catalogo`, `/importacoes` e
  `/ajustes` com cada papel aplicável. Corrigir regressões de rota/permissão
  antes de expandir telas.
- Não commitar `frontend/dist`; versionar fontes e migration.

### 2. Completar orçamento (docs 04–08)

- Criar `pages/orcamentos/editor/useOrcamento.ts`, centralizando `getQuote`,
  `listItems`, `getTotals`, `getReviewChecklist` e dados de catálogo.
- Migrar `QuotesPage.tsx` por comportamento: lista cheia, modal único de
  cliente/orçamento, `ItemCard`, `PainelResumo`, gaveta em três passos e
  condições com autosave de 600 ms.
- Manter a ordem financeira: preço congelado × markup × quantidade → desconto
  de item → desconto do orçamento → total → juros → parcelas. Nunca gravar
  markup em `frozen_unit_price`.
- Usar `ConfirmDialog` para remoção, duplicação, recongelamento e status. O
  envio por e-mail/aceite público permanece fora de escopo e oculto.

### 3. Catálogo, importações e gestão (docs 09–12, 15)

- Consulta: filtros visuais, `FINISH_HEX` com fallback cinza, paginação e
  adição segura a orçamento em rascunho.
- Administração: tela única, gaveta de edição e motivo obrigatório. Antes de
  alterar contrato, verificar auditoria persistente e planejar migration/API/testes.
- Importações: somente `.json` na UI; aplicar novo layout sem quebrar correção
  em lote ou publicação.
- Ajustes: editar as três configurações globais via API.

### 4. Documento comercial e hardening (docs 13–14)

- Reescrever `backend/app/quotes/export.py` a partir do snapshot congelado.
  Mostrar apenas descrição comercial, quantidade, preço de venda, total,
  descontos consolidados e condições.
- Nunca expor SKU, custo, margem, tabela de preço, confiança, preço por
  componente ou metadados de auditoria ao cliente.
- Migrar LoginPage, validar tablet retrato e comparar cada tela concluída com
  a referência HTML.

## Checklist de handoff

- [ ] Rodar `git status --short` antes de começar; qualquer alteração local
      pertence à tarefa atual e deve ser preservada ou entendida antes de editar.
- [ ] Ler `Agents.md`, este documento e o documento do pacote específico da
      tela antes de editar.
- [ ] Rodar build frontend e testes backend antes de declarar uma etapa pronta.
- [ ] Não alterar migrations existentes; a próxima migration é `0021`.
- [ ] Não remover legado enquanto a tela nova equivalente não cobrir
      comportamento, permissões e erros.
