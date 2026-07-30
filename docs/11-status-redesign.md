# Status operacional e continuidade do redesign

> **Fonte de verdade operacional do redesign.** Atualizado em 2026-07-29.
> Leia este arquivo e `Agents.md` antes de alterar frontend, settings ou PDF.
> Sempre execute `git status --short` antes de começar: o worktree pode conter
> mudanças de uma etapa anterior que devem ser preservadas.

## Referências visuais e regras imutáveis

- Especificação: `entrega-redesign-helence/docs/01` a `15`.
- Referência visual prioritária: `entrega-redesign-helence/referencia-visual/Helence Orçamento.dc.html`.
  Em caso de divergência, o HTML vence. Base: tablet paisagem, 1194×834.
- Importação ativa é exclusivamente JSON estruturado; não remover o pipeline
  PDF legado.
- Preservar RN-04, RN-12, RN-14 e RN-16. Em particular, nunca gravar markup
  em `frozen_unit_price` e nunca alterar a ordem de cálculo financeiro.
- Não alterar migrations existentes. A próxima migration disponível é `0022`.

## Aplicado nesta branch

### Fundação e navegação

- Tokens Helence, IBM Plex e primitivos `Botao`, `Card`, `Selo`, `Vazio`,
  `Esqueleto` e `ConfirmDialog` estão disponíveis.
- Shell com rail de 84 px, cinco destinos, permissões por papel, badge de
  importações bloqueantes e aviso offline.
- Rotas novas: `/`, `/orcamentos`, `/orcamentos/:id/{itens,condicoes,revisao}`,
  `/orcamentos/:id/documento`, `/catalogo`, `/catalogo/admin`,
  `/importacoes` e `/ajustes`.

### Painel e orçamento

- O Painel usa `GET /api/v1/quotes/summary` para métricas, funil, pendências e
  vencimentos. `listQuotes` é usado somente para enriquecer a atividade recente.
- O editor usa `useOrcamento.ts` como fonte compartilhada de orçamento, itens,
  totais e checklist.
- Itens usam cards, permitem ajustar quantidade, aplicar/limpar desconto por
  item com motivo e remover com `ConfirmDialog`.
- Condições comerciais usam autosave com debounce de 600 ms e indicador de
  estado no cabeçalho.
- Revisão tem veredito, checklist acionável, prévia do documento e explicação
  de bloqueio antes de congelar/enviar.
- `CompositionDrawer.tsx` está conectada à etapa de itens por
  `EditorItemsWithComposition.tsx`: busca, adiciona, remove e troca componentes
  pelas APIs existentes. Variantes sem preço são bloqueadas e erros de
  compatibilidade do backend são exibidos. Antes da troca, a confirmação mostra
  o preço congelado atual e o novo preço. Ao remover a última peça, o usuário
  confirma a remoção da linha inteira em vez de receber erro técnico.

### Catálogo e auditoria

- Consulta `/catalogo` possui filtros visuais, amostras de acabamento via
  `FINISH_HEX`, resultados com SKU/preço e inclusão em orçamento em rascunho.
- Administração `/catalogo/admin` lista variações e abre `VariantEditDrawer`.
  A gaveta edita descritor, descrição, SKU e preço, exige motivo e recarrega a
  lista após salvar. CRUDs legados nas rotas filhas permanecem como ponte.
- Migration `0021_component_variant_audit.sql` cria
  `component_variant_change_log`. `PATCH /components/{id}` aceita
  `change_reason` e, quando fornecido, persiste usuário, motivo, snapshot
  anterior e snapshot novo.
- O motivo ainda não é obrigatório no backend porque os CRUDs legados não foram
  migrados; só torná-lo obrigatório após esses fluxos enviarem `change_reason`.

### Execução local

- Desenvolvimento local deve preferir `http://localhost`, sem misturar com
  `127.0.0.1`.
- `backend/.env.local` e `frontend/.env.local` são sobreposições não
  versionadas para desenvolvimento. Em HTTP local, usar
  `SESSION_COOKIE_SECURE=false` e permitir a origem exata do Vite.
- Nesta sessão as portas padrão estão ocupadas por processos externos; a cópia
  verificada roda em frontend `http://localhost:5174` e backend
  `http://localhost:8001`.

## Lacunas abertas — não declarar como concluídas

1. **Composição de item:** transformar o acionador provisório em ação integrada
   no card; carregar produto pronto e filtrar complementos pela dimensão da
   base. Preço anterior/novo e remoção da última peça já estão tratados.
   Para o filtro, o contrato de `QuoteItemComponent` precisa expor a dimensão
   da peça-base, ou o backend precisa oferecer uma busca compatível por item;
   não inferir dimensão pelo texto no frontend.
2. **Acompanhamento:** remover o comportamento legado de orçamentos finalizados
   em `<details>` e unificar criação de cliente e orçamento em um diálogo.
3. **Condições:** completar a cascata financeira visual, as opções grandes de
   margem/pagamento e a mensagem de alçada conforme docs 07.
4. **Revisão posterior:** para orçamento enviado, criar “Registrar resposta do
   cliente” (aprovar, recusar ou expirar) com `ConfirmDialog`.
5. **Catálogo:** paginação explícita, tabela vigente visível, retorno direto ao
   orçamento de origem e auditoria/origem do preço na consulta. Administração
   precisa voltar a listar/editar as seis entidades na mesma rota sem navegar.
6. **Importações, fila de revisão, Ajustes e Login:** ainda são essencialmente
   telas legadas e precisam migrar conforme docs 11, 12, 15 e 14.
7. **Documento comercial:** `backend/app/quotes/export.py` ainda não foi
   redesenhado. É o maior bloqueio para uso externo: PDF e prévia devem ser
   equivalentes e nunca expor SKU, custo, margem, tabela, confiança ou auditoria.
8. **Hardening:** remover gradualmente `window.confirm`, `usePageHeader` e
   tokens/estilos legados; validar tablet retrato e todos os papéis.

## Próxima sequência recomendada

1. Concluir a gaveta de composição integrada ao card e cobrir
   `addComponent`/`removeComponent`/`swapComponent` com testes. Primeiro
   expor a dimensão pelo contrato/API e aplicar o filtro server-side.
2. Implementar resposta do cliente e concluir acompanhamento.
3. Finalizar catálogo: entidades administrativas, paginação e auditoria.
4. Migrar Importações, fila de revisão, Ajustes e Login.
5. Reescrever o PDF comercial a partir do snapshot congelado e comparar com a
   prévia web.

## Verificação obrigatória antes de handoff

- `npm run build` no frontend.
- `python -m compileall app` no backend.
- `git diff --check`.
- Executar `python -m pytest tests/integration/ -v` em ambiente com pytest
  instalado. Nesta sessão o módulo não está disponível.
- Adicionar testes para migration 0021 e auditoria de PATCH: autor, motivo,
  snapshot anterior e snapshot novo.
- O último `npm run build` e `git diff --check` passaram após a confirmação de
  remoção da última peça. `pytest` continua indisponível nesta sessão.
