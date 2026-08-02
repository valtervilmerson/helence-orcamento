# Status operacional e continuidade do redesign

> **Fonte de verdade operacional do redesign.** Atualizado em 2026-08-01.
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
  item com motivo e remover com `ConfirmDialog`. As ações do card ficam no
  menu `⋯`, que também permite duplicar a composição como uma nova linha.
- O painel lateral de itens usa o checklist RN-18 para mostrar progresso,
  pendências explicadas e links para a etapa que as resolve; também oferece
  acesso direto às condições comerciais.
- Condições comerciais usam autosave com debounce de 600 ms e indicador de
  estado no cabeçalho. A etapa agora traz cartões de escolha para margem,
  desconto e pagamento, botões rápidos de parcelamento, alerta de alçada com
  motivo obrigatório e a cascata financeira fixa conforme documento 07.
- Revisão tem veredito, checklist acionável, prévia do documento e explicação
  de bloqueio antes de congelar/enviar.
- Acompanhamento agrupa orçamentos em atenção, andamento e encerrados, com
  filtros por situação e criação unificada de cliente + orçamento. Propostas
  enviadas permitem registrar aprovação, recusa ou expiração com confirmação.
- `CompositionDrawer.tsx` está conectada à etapa de itens por
  `EditorItemsWithComposition.tsx`: busca, adiciona, remove e troca componentes
  pelas APIs existentes. Variantes sem preço são bloqueadas e erros de
  compatibilidade do backend são exibidos. Antes da troca, a confirmação mostra
  o preço congelado atual e o novo preço. Ao remover a última peça, o usuário
  confirma a remoção da linha inteira em vez de receber erro técnico.

### Catálogo e auditoria

- Consulta `/catalogo` possui filtros visuais, amostras de acabamento via
  `FINISH_HEX`, resultados com SKU/preço e inclusão em orçamento em rascunho.
- O filtro de dimensão da consulta foi corrigido pelo complemento 09b: largura
  reduz a lista de medidas completas, grupos são colapsáveis e a barra lateral
  fica contida na viewport de tablet sem alterar o contrato de busca.
- Administração `/catalogo/admin` lista variações e abre `VariantEditDrawer`.
  A gaveta edita descritor, descrição, SKU e preço, exige motivo e recarrega a
  lista após salvar. CRUDs legados nas rotas filhas permanecem como ponte.
- Migration `0021_component_variant_audit.sql` cria
  `component_variant_change_log`. `PATCH /components/{id}` aceita
  `change_reason` e, quando fornecido, persiste usuário, motivo, snapshot
  anterior e snapshot novo.
- O motivo ainda não é obrigatório no backend porque os CRUDs legados não foram
  migrados; só torná-lo obrigatório após esses fluxos enviarem `change_reason`.
- Administração em `/catalogo/admin` passou a reunir as seis entidades na mesma
  rota: os cards trocam a tabela ativa sem navegação. Variações vendáveis têm
  paginação de 25, criação local e edição em gaveta com motivo obrigatório.
- A consulta em `/catalogo` agora pagina explicitamente de 25 em 25. Quando
  aberta com `?voltarPara=/orcamentos/:id/itens`, a adição da variação é direta
  e retorna ao editor do orçamento de origem.

### Importações

- `/importacoes` foi migrada para o fluxo ativo de JSON: zona de envio restrita
  a `.json`, feedback de contrato, cartão prioritário da fila bloqueante e
  histórico com ações por permissão. A revisão agora tem rota própria em
  `/importacoes/:id/revisao`; o pipeline legado de processamento permanece
  acessível somente para registros antigos recebidos.
- A fila de revisão passou ao layout operacional de duas colunas: busca e
  filtros com seleção em lote à esquerda; motivo da pendência e comparação
  entre origem e catálogo à direita. Mantém correção de campo, criação de
  acabamento, aplicação em lote, rejeição justificada e avança para o próximo
  item pendente depois da decisão.

### Ajustes

- `/ajustes` agora apresenta a política comercial em edição por linha, ligada
  às configurações persistidas de margem global, alçada de desconto e validade
  padrão. A equipe usa `GET /auth/users`, restrito a admin, em vez de dados
  estáticos; testes cobrem acesso permitido e negado.

### Login

- Login migrou para a composição de dois painéis: a proposta do produto ocupa
  o painel de marca e o formulário permanece enxuto no painel claro. Falhas de
  credencial usam uma mensagem genérica e o sucesso sempre direciona ao Painel.
  Como o modelo atual não expõe uma tabela vigente, a tela não inventa esse
  dado. Em tablet retrato, o painel de marca vira uma faixa superior de 160 px.

### Execução local

- Desenvolvimento local deve preferir `http://localhost`, sem misturar com
  `127.0.0.1`.
- `backend/.env.local` e `frontend/.env.local` são sobreposições não
  versionadas para desenvolvimento. Em HTTP local, usar
  `SESSION_COOKIE_SECURE=false` e permitir a origem exata do Vite.
- Nesta sessão a cópia local verificada roda em frontend
  `http://localhost:5173` e backend `http://localhost:8000`.

## Lacunas abertas — não declarar como concluídas

1. **Composição de item:** a ação agora vive no card e o fluxo “Carregar
   produto pronto” cria a linha pela composição cadastrada. O contrato de
   `QuoteItemComponent` expõe `dimension_id`/`dimension_label`, e
   `GET /components` filtra por `dimension_id` no servidor; a gaveta usa a
   dimensão da peça-base sem inferência textual. A criação manual passou a ter
   os passos Peça base → Complementos → Confirmar, cartões com SKU/preço,
   total e aviso de congelamento. Os cards de item indicam linha incompleta,
   levam diretamente à composição e mostram o instante do preço congelado.
   Preço anterior/novo e remoção da última peça já estão tratados. O atalho de
   produto pronto também preenche o passo de confirmação em vez de adicionar
   diretamente. Resta validar o fluxo com composições reais.
2. **Acompanhamento:** o fluxo legado de finalizados foi removido e a criação
   de cliente + orçamento está no mesmo diálogo. Rascunhos agora consultam as
   próprias linhas para mostrar quantidade de itens incompletos e os
   componentes ausentes, além de irem automaticamente para atenção. Resta
   validar o carregamento dessa informação em uma base com alto volume de
   orçamentos.
3. **Condições:** a estrutura do documento 07 está aplicada. Resta validar o
   comportamento com dados reais, especialmente quando a política global de
   margem é alterada enquanto um rascunho usa o padrão da empresa.
4. **Revisão posterior:** “Registrar resposta do cliente” já oferece aprovar,
   recusar ou expirar com `ConfirmDialog`. O motivo opcional de recusa depende
   de um campo persistido pelo backend, que ainda não existe no contrato.
5. **Catálogo:** paginação explícita, retorno direto ao orçamento de origem,
   administração unificada e a consulta de origem/auditoria de preço estão
   entregues. A migration `0009` removeu tabela/preço por vigência; portanto a
   leitura mostra "Preços ativos do catálogo", sem inventar código ou data de
   tabela. A auditoria é restrita a admin/revisor e nunca integra o PDF.
6. **Importações, fila de revisão, Ajustes e Login:** todas essas telas já
   seguem o desenho operacional. Ainda falta validar os fluxos com dados reais.
7. **Documento comercial:** a prévia web e `backend/app/quotes/export.py`
   usam a folha comercial: condições, descrição comercial, desconto unificado
   e aceite. O PDF passa a distribuir os valores a partir de `quote_totals`,
   sem reler markup global, e não expõe SKU, custo, margem, tabela, confiança
   ou auditoria. Ainda falta a comparação visual rigorosa página a página e o
   embed das fontes IBM Plex para declarar equivalência total.
8. **Hardening:** remover gradualmente `window.confirm`, `usePageHeader` e
   tokens/estilos legados; validar tablet retrato e todos os papéis.

## Próxima sequência recomendada

1. Validar os fluxos operacionais com dados reais.
2. Reescrever o PDF comercial a partir do snapshot congelado e comparar com a
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
