# Plano de implementação incremental — Helence Orçamento

> Plano de entregas pequenas e testáveis, construído sobre as decisões
> já tomadas em `docs/01` a `docs/06`. Cada fase produz algo que pode
> ser demonstrado e validado — nenhuma fase depende de "terminar de
> entender o PDF" para gerar valor.

## Princípio organizador: o pipeline de importação é o item de **maior
## incerteza** do projeto — por isso ele vem depois, não antes

Há uma armadilha natural neste projeto: como tudo "começa" com o PDF,
é tentador começar a construir por ali. Esse é exatamente o caminho que
este plano evita, por três razões concretas:

1. **A extração é a parte menos previsível do sistema.** A própria
   auditoria (`docs/01`) e o spike (`docs/02`) mostraram páginas de
   alta, média e baixa confiança, casos de "código sem preço",
   convenções inferidas (não declaradas) de compatibilidade — ou seja,
   *sempre* vai sobrar trabalho de revisão humana. Construir em cima de
   uma extração "quase pronta" é construir em cima de areia movediça.
2. **O catálogo e o orçamento são o que entrega valor — e podem ser
   validados sem PDF nenhum.** O modelo de dados (`docs/03`) e as
   regras de negócio (`docs/05`) já estão desenhados; cadastrar um
   punhado de produtos manualmente e montar um orçamento de ponta a
   ponta prova — cedo, barato e em escala controlada — que esse núcleo
   funciona. Erros de modelagem aparecem agora, não com dados reais em
   produção.
3. **"Extração progressiva, sempre revisada"** não é só uma
   característica do produto final (RN-14 de `docs/05`) — é também a
   estratégia certa de **construção**: cada fase do pipeline de
   importação (upload → extração → revisão → publicação) é entregue e
   testada isoladamente, e o "portão de qualidade" entre extração e
   catálogo (a revisão humana) é construído **antes** da publicação
   automática — nunca depois, como um remendo.

Por isso a ordem do plano é, em linhas gerais: **construir o destino
dos dados primeiro (fases 1-3, com dados manuais) → depois construir a
origem, peça por peça e sempre atrás de revisão humana (fases 4-7) →
depois enriquecer ambos os lados com dados reais em volume (fases
8-10) → por fim, preparar o sistema para operar de verdade (fases
11-12)**.

---

## Fase 0 — Setup e decisões iniciais

**Objetivo**: preparar o terreno técnico — repositório, ambiente de
desenvolvimento, ferramentas e convenções — para que toda fase seguinte
comece a partir de uma base estável e compartilhada pelo time.

**Por que essa fase vem nessa ordem**: nenhuma linha de funcionalidade
deveria ser escrita antes de o time conseguir, de forma reproduzível,
clonar o repositório, instalar dependências e rodar a aplicação. Adiar
essas decisões "para depois" é a forma mais comum de gerar
inconsistência silenciosa entre máquinas e, depois, retrabalho caro.

**Entregáveis**:
- Estrutura de pastas inicial conforme `docs/06-arquitetura-api.md`
  (seção 2) — `backend/`, `frontend/`, `docs/`, `scripts/spikes/`.
- Ambiente de desenvolvimento funcionando: backend (FastAPI) e
  frontend (React+TS) sobem localmente e respondem a um *healthcheck*
  básico ("hello world" de cada lado).
- Convenções registradas e aplicadas: formato de erro (`docs/06`,
  seção 9), convenção de *commits*/branches, *linter*/formatador
  configurados.
- Pipeline de integração contínua mínimo (roda *lint* + testes a cada
  *push*, mesmo que os testes ainda sejam triviais).
- `README.md` com passo a passo de instalação e execução local.

**Arquivos/módulos prováveis**: `backend/app/main.py`,
`backend/pyproject.toml`, `frontend/package.json`,
`.github/workflows/ci.yml` (ou equivalente), `README.md`.

**Critérios de aceite**:
- Uma pessoa que nunca tocou no projeto consegue, seguindo só o
  `README`, clonar, instalar e rodar backend + frontend localmente.
- O pipeline de CI roda e passa (mesmo com testes triviais).
- `GET /api/v1/health` (ou equivalente) responde `200`.

**Testes mínimos**: teste de *smoke* do backend (sobe a app, healthcheck
responde); verificação de que o frontend builda sem erros.

**Riscos**:
- *"Funciona na minha máquina"* — diferenças sutis de versão de
  ferramentas entre desenvolvedores. Mitigação: travar versões
  (`lockfiles`), documentar versões mínimas no `README`.
- Tempo gasto "polindo" ferramentas além do necessário. Mitigação: o
  objetivo aqui é destravar o time, não ter a configuração perfeita —
  ajustes finos podem esperar.

**O que não deve ser feito ainda**:
- Nenhuma regra de negócio, nenhuma tela final, nenhuma conexão com
  banco de dados real (isso é a Fase 1).
- Nenhuma decisão sobre extração de PDF — ainda é cedo demais para
  isso ter qualquer prioridade.

---

## Fase 1 — Banco SQLite e migrations

**Objetivo**: ter o schema completo de 24 tabelas (`docs/schema/schema.sql`,
já desenhado e validado em `docs/03-modelagem-sqlite.md`) aplicado via
migrations versionadas, com a infraestrutura básica de acesso a dados
funcionando.

**Por que essa fase vem nessa ordem**: tudo que será construído a
partir da Fase 2 precisa persistir em algum lugar real. Como o schema
**já foi desenhado e validado** (incluindo verificação de
`PRAGMA foreign_key_check`), esta fase é "aplicar uma decisão já
tomada", não "tomar uma decisão nova" — baixo risco, alto valor de
desbloqueio para tudo que vem depois.

**Entregáveis**:
- Executor de migrations (lê scripts numerados, aplica em ordem,
  registra em `schema_migrations`) — conforme `docs/06`, seção 10.
- `0001_initial.sql` aplicando o schema completo de
  `docs/schema/schema.sql`.
- Conexão configurada para ativar `PRAGMA foreign_keys = ON` por
  conexão (não é persistido pelo SQLite — precisa ser feito sempre).
- *Seed* mínimo de dados de referência para destravar o
  desenvolvimento (ex.: usuários de teste com cada papel — Importador/
  Revisor/Aprovador/Vendedor/Auditor — e uma `price_table` vazia em
  status `vigente`, necessária para a Fase 3 não ficar bloqueada por
  `NENHUMA_TABELA_VIGENTE`).

**Arquivos/módulos prováveis**: `backend/app/db/connection.py`,
`backend/app/db/migrations/0001_initial.sql`, `backend/app/shared/config.py`.

**Critérios de aceite**:
- Subir a aplicação do zero cria um banco com as 24 tabelas + 32
  índices descritos em `docs/03`.
- `PRAGMA foreign_key_check` retorna vazio.
- Rodar o executor de migrations duas vezes seguidas não falha nem
  duplica nada (idempotente).

**Testes mínimos**:
- Teste de integração que aplica as migrations num banco SQLite
  temporário e confirma a existência das tabelas-chave de cada camada
  (`imported_files`, `component_variants`, `quotes`).
- Teste que insere um registro respeitando uma cadeia de FK (ex. um
  `product` ligado a uma `product_family`) e confirma que uma FK
  inválida é rejeitada.

**Riscos**:
- Ordem de criação de tabelas causando erro de FK. Mitigação: a ordem
  topológica já foi resolvida e validada em `docs/03` — basta seguir o
  arquivo de schema na ordem em que está.
- Comportamento do SQLite variar entre versões/drivers. Mitigação:
  fixar a versão do driver e documentar a versão mínima do SQLite.

**O que não deve ser feito ainda**:
- Não popular o banco com dados reais extraídos do PDF.
- Não criar nenhum endpoint de API ainda — esta fase é só schema +
  acesso a dados.

---

## Fase 2 — Catálogo manual

**Objetivo**: permitir cadastrar manualmente, via API e uma tela
simples, os elementos do catálogo normalizado (famílias, produtos,
tipos de componente, dimensões, acabamentos, variações vendáveis,
SKUs e preços) — **sem qualquer dependência de importação de PDF**.

**Por que essa fase vem nessa ordem**: esta é a peça central da
estratégia "construir o destino antes da origem". Cadastrando à mão um
conjunto pequeno de produtos **reais** — usando os dados já verificados
no spike (`docs/samples/extracao-amostra.json`: ex. as 9 variações de
"Tampo Inteiro Simples 1200×900", com preços de R$ 374,45 a R$ 493,80
conforme o acabamento) — o time prova que o modelo de dados funciona
**e** ganha, de graça, dados reais para testar a montagem de orçamento
na Fase 3, muito antes de a extração de PDF estar pronta. Também
valida cedo o contrato de "CRUD manual de componentes" (`docs/06`,
14.9), que continuará existindo depois como ferramenta de
preenchimento de lacunas pontuais.

**Entregáveis**:
- Endpoints de CRUD para as entidades centrais do catálogo
  (`product_families`, `products`, `product_components`, `dimensions`,
  `finishes`, e o conjunto `component_variants`+`skus`+`prices` —
  conforme contrato de `docs/06`, 14.9).
- Tela(s) simples de cadastro — propositalmente utilitárias, sem
  refinamento visual (função antes de forma nesta fase).
- Catálogo populado manualmente com um conjunto pequeno e **real** de
  produtos, replicando os dados já verificados no spike de extração.

**Arquivos/módulos prováveis**: `backend/app/catalog/` (`router.py`,
`service.py`, `repository.py`, `schemas.py`), `frontend/src/pages/catalog/cadastro`.

**Critérios de aceite**:
- É possível cadastrar, via tela ou API, um produto completo (família
  → produto → componente → dimensão → acabamento → variação → SKU →
  preço) e recuperá-lo de volta com exatamente os mesmos dados.
- Tentar cadastrar uma combinação duplicada é bloqueada pelas
  restrições `UNIQUE` do schema, retornando os erros nomeados
  `VARIACAO_DUPLICADA`/`PRECO_DUPLICADO` conforme o contrato de
  `docs/06`.

**Testes mínimos**:
- Teste de integração "cadastra → consulta → confirma igualdade".
- Teste de que duplicatas retornam o código de erro nomeado correto
  (não um erro genérico de banco vazado para o cliente).

**Riscos**:
- Investir tempo demais desenhando a UI de cadastro como se fosse a
  definitiva. Mitigação: tratar esta tela explicitamente como
  ferramenta interna/utilitária — refinamento visual não é objetivo
  desta fase.
- Confundir "cadastro manual" com "fluxo de importação real" na cabeça
  do time ou dos usuários. Mitigação: nomear e comunicar claramente que
  esta é uma ferramenta de *bootstrapping* e preenchimento de lacunas —
  não um substituto da importação (que vem nas Fases 4-7).

**O que não deve ser feito ainda**:
- Não implementar busca avançada com filtros sofisticados — isso é a
  Fase 8, e só faz sentido com volume real de dados.
- Nenhuma conexão com upload, extração ou PDF.

---

## Fase 3 — Montagem manual de orçamento (ciclo de vida básico)

**Objetivo**: implementar o ciclo de vida básico de um orçamento —
criar, adicionar item, calcular total, alterar status — tratando, **de
propósito, cada linha como um item "fechado"** (um `quote_item` com
exatamente um `quote_item_component`, o caso mais simples já previsto
no modelo de `docs/03`). Ainda **sem** as regras de composição/
compatibilidade mais ricas (várias peças por linha, tampo↔estrutura
etc.).

**Por que essa fase vem nessa ordem**: aplica, dentro do próprio domínio
de orçamentos, o mesmo princípio de incrementalidade do plano inteiro —
provar primeiro o **esqueleto** (criar orçamento → adicionar item →
calcular total → mudar status → ver o congelamento de preço acontecer)
com o caso mais simples possível, e só depois (Fase 9) empilhar a
complexidade da composição múltipla. Testar o ciclo de vida completo
agora, com dados pequenos e controlados (cadastrados na Fase 2), expõe
cedo qualquer problema de modelagem nas regras **mais sensíveis** do
sistema — RN-15 (tabela vigente) e RN-16 (congelamento de preço, a
"regra mais sensível do ponto de vista de negócio" segundo `docs/05`).

**Entregáveis**:
- Endpoints: criação de orçamento, adição de item (com um único
  componente), atualização de quantidade/desconto, cálculo de total
  (`docs/06`, 14.10/14.11/14.12/14.13 — usados aqui em sua forma mais
  simples).
- Regras de negócio centrais implementadas e testadas: ancoragem
  automática à tabela vigente (RN-15), congelamento de preço no momento
  da adição (RN-16), bloqueio de item sem preço/SKU (RN-12/13 —
  testável mesmo com poucos dados, pois o cadastro manual da Fase 2
  pode incluir deliberadamente uma variação sem preço para validar o
  bloqueio).
- Tela básica de montagem (funcional, sem composição — o equivalente a
  "escolher um produto pronto e adicionar ao orçamento").
- Um orçamento de ponta a ponta criado manualmente, reproduzindo em
  espírito o Exemplo 1 de `docs/05` (ainda que de forma simplificada,
  sem múltiplos componentes por linha).

**Arquivos/módulos prováveis**: `backend/app/quotes/` (`router.py`,
`service.py`, `pricing.py`, `repository.py`, `schemas.py`),
`frontend/src/pages/quotes/montagem` (versão simples).

**Critérios de aceite**:
- É possível criar um orçamento, adicionar um item com preço, ver o
  valor congelado corretamente, alterar quantidade/desconto e ver o
  total recalculado.
- Tentar adicionar um item sem preço cadastrado é bloqueado com o erro
  nomeado `ITEM_SEM_PRECO` (não um erro genérico) — provando a regra
  mais crítica de bloqueio (RN-12) cedo.
- Alterar a versão vigente da tabela **não** muda o valor já congelado
  de um item existente (RN-16 comprovada na prática, não só no papel).

**Testes mínimos**:
- Testes unitários das regras de congelamento e de ancoragem à tabela
  vigente, isolados (camada de serviço, sem precisar de HTTP/banco —
  conforme a separação de camadas de `docs/06`, seção 1).
- Teste de integração do fluxo completo: criar → adicionar item →
  atualizar desconto → calcular total → mudar status.

**Riscos**:
- A tentação de "esperar dados reais" para validar isso direito.
  Mitigação: esse é exatamente o ponto desta fase — **não esperar**.
  Poucos dados manuais, bem escolhidos, já expõem a maioria dos
  problemas de regra.
- Descobrir só agora que o entendimento de congelamento/versão vigente
  estava equivocado. Mitigação: isso é desejável **aqui** — é
  imensamente mais barato corrigir agora do que com clientes reais
  recebendo orçamentos.

**O que não deve ser feito ainda**:
- Não implementar composição com múltiplos componentes por linha, nem
  regras de compatibilidade — isso é a Fase 9, deliberadamente adiada.
- Não implementar exportação refinada (Fase 10) nem duplicação de
  orçamento (Fase 9).
- Nenhuma conexão com dados de importação real.

---

## Fase 4 — Upload de PDF

**Objetivo**: implementar o endpoint e o fluxo de upload de arquivo —
recepção, validação básica, cálculo de hash, deduplicação,
armazenamento e registro em `imported_files` — **sem processar ou
extrair absolutamente nada ainda**.

**Por que essa fase vem nessa ordem**: neste ponto o time já provou que
o "destino" dos dados (catálogo + orçamento) funciona de ponta a ponta
com dados reais cadastrados manualmente — agora é seguro começar a
construir o "início" do pipeline de importação, escolhendo
deliberadamente a parte **mais simples e menos arriscada** (receber e
guardar um arquivo) antes de se comprometer com a parte difícil
(extração, Fase 5). Separar as duas evita que problemas de extração
atrasem (ou contaminem) algo tão básico quanto "conseguir enviar um
arquivo".

**Entregáveis**:
- Endpoint `POST /api/v1/imports` (`docs/06`, 14.1): recebe o PDF,
  valida tipo/tamanho, calcula `sha256`, detecta duplicatas, armazena o
  arquivo e cria o registro em `imported_files`.
- Endpoint de listagem de importações (`docs/06`, 14.2) — nesta fase,
  todo registro aparece com `status = "recebido"`.
- Tela de upload básica + listagem.

**Arquivos/módulos prováveis**: `backend/app/imports/router.py`,
`backend/app/imports/repository.py`, `backend/app/files/storage.py`,
`frontend/src/pages/imports/upload`.

**Critérios de aceite**:
- Enviar um PDF válido cria o registro, armazena o arquivo (nomeado
  pelo hash) e retorna os dados conforme o contrato `14.1`.
- Reenviar o mesmo arquivo é detectado como duplicado
  (`ARQUIVO_DUPLICADO`, apontando para a importação existente).
- A listagem mostra os arquivos enviados com paginação e filtro por
  status.

**Testes mínimos**:
- Teste de upload bem-sucedido (caminho feliz).
- Teste de rejeição de arquivo inválido/corrompido (`ARQUIVO_INVALIDO`).
- Teste de deduplicação por hash.

**Riscos**:
- Antecipar decisões de processamento "só para adiantar". Mitigação:
  resistir conscientemente — esta fase é estritamente "receber e
  guardar"; qualquer lógica de extração aqui é escopo da Fase 5.
- Limite de tamanho de arquivo mal calibrado. Mitigação: usar como
  referência o porte dos arquivos já analisados na auditoria (`docs/01`).

**O que não deve ser feito ainda**:
- **Não** implementar processamento/extração — isso é, deliberadamente,
  a próxima fase, separada.
- Não construir a tela de acompanhamento de progresso ainda (ela só faz
  sentido quando existir processamento de fato — Fase 5).

---

## Fase 5 — Spike de extração integrado

**Objetivo**: pegar a estratégia de extração já validada no spike
exploratório (`docs/02-spike-extracao-pdf.md` — pymupdf recomendado) e
**integrá-la** ao pipeline real: transformar um PDF armazenado em
`extracted_rows`/`extracted_items` gravados no banco, com nível de
confiança e avisos honestos — e **parar exatamente aí**, sem qualquer
promoção automática ao catálogo.

**Por que essa fase vem nessa ordem — e por que ela tem este escopo
deliberadamente limitado**: só agora — depois que upload, catálogo e
orçamento já existem e funcionam de ponta a ponta — faz sentido
investir na parte de **maior incerteza** do projeto. E o ponto mais
importante desta fase é o que ela **não** tenta fazer: não tenta
"extrair perfeitamente". Meta explícita = **reproduzir, de forma
automatizada, exatamente o que o spike já provou manualmente** — nem
mais, nem menos. A amostra `docs/samples/extracao-amostra.json` (já
validada) funciona como "gabarito": se o pipeline automatizado produz,
para as mesmas páginas, os mesmos itens com os mesmos níveis de
confiança, a fase está completa — refinamentos de extração entram como
itens de backlog contínuo, nunca como bloqueio desta entrega.

**Entregáveis**:
- Endpoint `POST /api/v1/imports/{id}/process` (`docs/06`, 14.3),
  rodando em segundo plano (estratégia de processamento assíncrono em
  processo, conforme `docs/06`, seção 7).
- *Pipeline* que aplica a extração e grava `extracted_rows` +
  `extracted_items` (com `confidence`/`confidence_level`/
  `extraction_notes`), gerando `import_warnings` honestos para o que
  não foi bem compreendido.
- Endpoint de status com progresso incremental (`docs/06`, 14.4).

**Arquivos/módulos prováveis**: `backend/app/imports/extraction.py`
(porta a lógica validada em `scripts/spikes/`, não o código exploratório
bruto), `backend/app/imports/service.py`.

**Critérios de aceite**:
- Processar o PDF de referência reproduz, para as páginas já auditadas
  (1, 2, 432), os **mesmos** itens, valores e níveis de confiança
  documentados em `docs/samples/extracao-amostra.json` — a prova de
  que a automação replica o que já foi validado manualmente.
- Itens de baixa confiança (ex. o caso real "código sem preço",
  SKU `398101456`) são marcados corretamente como `confidence_level =
  'baixa'` e geram avisos em `import_warnings`.

**Testes mínimos**:
- Teste de integração processando o PDF de referência e comparando a
  saída automatizada com o JSON canônico já validado (gabarito).
- Teste de que páginas problemáticas geram avisos — não falham
  silenciosamente nem travam o processamento inteiro.

**Riscos**:
- A maior tentação desta fase: tentar "melhorar a extração"
  indefinidamente. Mitigação: meta de aceite **fixa e objetiva**
  (igualar o gabarito já validado) — qualquer melhoria além disso é
  backlog, não critério de conclusão.
- Performance em arquivos grandes (centenas de páginas). Mitigação: já
  endereçada arquiteturalmente — processamento assíncrono com
  acompanhamento incremental (`docs/06`, seção 7).

**O que não deve ser feito ainda**:
- **Não promover nada automaticamente para o catálogo** — isso só
  acontece na Fase 7, e somente depois de revisão humana (Fase 6). Esta
  é a aplicação direta de RN-14 (`docs/05`): um item extraído é
  **invisível** para o catálogo até passar pelo ciclo completo.
- Não tentar tratar 100% das páginas/casos — registrar honestamente
  como aviso/baixa confiança o que não foi entendido é o comportamento
  **correto**, não uma falha a esconder.

---

## Fase 6 — Revisão de importação

**Objetivo**: construir o fluxo e a tela de revisão humana de itens
extraídos — visualizar o trecho original, comparar com o item
normalizado, aprovar, rejeitar, corrigir e aplicar correção em lote —
exatamente como especificado na Tela 3/4 de `docs/04-ux-operacional.md`.

**Por que essa fase vem nessa ordem**: é o complemento direto e
indispensável da Fase 5 — sem revisão, os dados extraídos ficam
estruturalmente presos, sem caminho para o catálogo (por desenho,
RN-14). Construí-la logo em seguida mantém o ciclo "extrai → revisa"
coeso, e permite testá-la imediatamente com dados reais (já produzidos
pela Fase 5, não mais simulados).

**Entregáveis**:
- Endpoint `POST /api/v1/extracted-items/{id}/review` (`docs/06`,
  14.6), cobrindo os três tipos de decisão num único contrato
  (aprovar/rejeitar/corrigir).
- Tela de revisão com: visualização do trecho/página original,
  comparação lado a lado linha↔item normalizado, edição de
  campos (SKU/preço/acabamento/dimensão), aprovação/rejeição
  individual, alerta de baixa confiança, e o modal de correção em lote
  (agrupamento por valor bruto, prévia, exclusão de itens já decididos)
  — todas as 10 capacidades específicas mapeadas em `docs/04`.

**Arquivos/módulos prováveis**: extensão de `backend/app/imports/`
(`router.py`, `service.py`), `frontend/src/pages/imports/revisao`.

**Critérios de aceite**:
- Um revisor consegue, para um PDF já processado (Fase 5), percorrer os
  itens, ver o nível de confiança e o trecho de origem, aprovar os
  corretos, corrigir os com erro pontual e rejeitar os inválidos — com
  cada decisão registrada em `import_review_decisions`, completa e
  auditável (quem, quando, o quê mudou, de/para).
- Um item já decidido não pode ser sobrescrito silenciosamente —
  reabrir uma decisão exige uma ação explícita e diferenciada
  (`STATUS_INVALIDO` no caminho normal).
- A correção em lote aplica a mudança apenas ao escopo selecionado, com
  prévia antes de confirmar, e nunca sobrescreve itens que já têm
  decisão humana registrada.

**Testes mínimos**:
- Teste de fluxo "aprovar"/"corrigir campo"/"rejeitar com motivo"
  gerando o registro de decisão correto e a transição de
  `review_status` esperada.
- Teste de que a correção em lote exclui corretamente itens já
  decididos do escopo de aplicação.

**Riscos**:
- Subestimar o esforço de UX desta tela — é a mais complexa do sistema.
  Mitigação: ela já foi especificada em detalhe em `docs/04`; seguir a
  especificação reduz decisões de design a tomar "na hora".
- Volume de itens pendentes tornar a revisão tediosa a ponto de gerar
  aprovações apressadas. Mitigação: a correção em lote, desenhada desde
  o início para isso, existe exatamente para reduzir esse atrito sem
  comprometer a qualidade da decisão.

**O que não deve ser feito ainda**:
- Não implementar publicação no catálogo — isso é a Fase 7.
- Não tentar automatizar nenhuma decisão de revisão — por definição, e
  por ser o "portão de qualidade" central do sistema, a revisão é
  **sempre** humana.

---

## Fase 7 — Publicação dos dados aprovados no catálogo

**Objetivo**: implementar o "portão" que transforma `extracted_items`
aprovados em `component_variants`/`skus`/`prices` reais no catálogo
normalizado, e que marca a versão de tabela correspondente como
`vigente` (arquivando a anterior).

**Por que essa fase vem nessa ordem**: ela só faz sentido **depois**
que (a) existe um conjunto real de itens aprovados para publicar
(Fases 5+6) e (b) o catálogo e o consumo dele por orçamentos já estão
validados com dados manuais (Fases 2+3) — ou seja, "publicar" é,
tecnicamente, popular as **mesmas** tabelas que o cadastro manual já
populava, só que em escala e a partir de uma origem diferente. É também
o momento em que o sistema deixa de depender de dados "de mentirinha" e
passa a operar com dados reais derivados do PDF — o ponto de virada do
projeto.

**Entregáveis**:
- Endpoint `POST /api/v1/price-tables/{id}/publish` (`docs/06`, 14.7):
  mapeia itens aprovados para variações/SKUs/preços (respeitando as
  restrições `UNIQUE` do schema), grava a rastreabilidade
  (`prices.source_extracted_item_id`), e troca o status
  `vigente`↔`substituída`.
- Tela de aprovação/publicação (Tela 5 de `docs/04`).

**Arquivos/módulos prováveis**: `backend/app/catalog/service.py`
(lógica de publicação), extensão de `router.py`.

**Critérios de aceite**:
- Publicar uma tabela revisada cria as entradas correspondentes no
  catálogo, com rastreabilidade completa até o `extracted_item` de
  origem — comprovável pela consulta "auditar origem de preço" já
  desenhada em `docs/03`.
- Itens pendentes de revisão **bloqueiam** a publicação
  (`ITENS_PENDENTES_DE_REVISAO`, com a contagem e link para revisão —
  nunca uma publicação parcial silenciosa).
- A versão anterior é corretamente arquivada (`substituida`) e a nova
  passa a `vigente`.

**Testes mínimos**:
- Teste de fluxo completo "extração → revisão → publicação → consulta
  no catálogo", confirmando que o dado chega íntegro e rastreável.
- Teste de bloqueio por itens pendentes.
- Teste de que publicar a mesma tabela duas vezes não duplica dados
  (idempotência/segurança da operação).

**Riscos**:
- Conflitos de restrição `UNIQUE` durante a publicação em massa (ex.
  duas linhas extraídas mapeando para a mesma variação). Mitigação:
  tratamento explícito, testado, com mensagem que aponta exatamente
  qual item conflitou — nunca um erro de banco cru.
- Desempenho da publicação de tabelas grandes. Mitigação: operação em
  transação única, com possibilidade de processamento em lotes — a
  decidir conforme o volume real observado nas Fases 5/6.

**O que não deve ser feito ainda**:
- Não remover a possibilidade de cadastro manual (Fase 2) — ela
  permanece como ferramenta legítima de preenchimento de lacunas
  pontuais (ex. os casos de "código sem preço").
- Não tentar republicar/corrigir publicações automaticamente — qualquer
  correção pós-publicação é, por desenho, um novo ciclo revisão→publicação.

---

## Fase 8 — Busca avançada e filtros

**Objetivo**: evoluir a busca de catálogo (que já existe de forma
simples desde a Fase 2) para suportar os filtros completos
especificados em `docs/06` (14.8) e na Tela 6 de `docs/04` — família,
produto, componente, dimensão, acabamento e busca textual livre,
combináveis.

**Por que essa fase vem nessa ordem**: investir em busca sofisticada
só faz sentido **depois** de existir volume real de dados publicados
(Fase 7) — testar filtros complexos contra um catálogo de meia dúzia de
produtos cadastrados à mão não revela os problemas reais de usabilidade
e desempenho que aparecem com centenas de variações (a escala
observada na auditoria).

**Entregáveis**:
- Endpoint de busca com todos os filtros combináveis (`GET
  /api/v1/catalog/search`).
- Tela de consulta do catálogo refinada (Tela 6 de `docs/04`).
- Ajuste dos índices de banco conforme os padrões de uso reais
  observados (os índices propostos em `docs/03` são o ponto de
  partida, não a palavra final).

**Arquivos/módulos prováveis**: extensão de
`backend/app/catalog/repository.py`/`service.py`,
`frontend/src/pages/catalog/consulta`.

**Critérios de aceite**:
- É possível localizar rapidamente, por exemplo, "todas as variações de
  Tampo para Reunião 1200×900 em Carvalho" com resultado correto.
- Filtros combinados retornam a **interseção** correta (não a união).
- Tempo de resposta aceitável com o volume real publicado.

**Testes mínimos**:
- Testes de busca com cada filtro isolado e em combinações.
- Teste básico de desempenho com o volume real de catálogo publicado.

**Riscos**:
- Explosão de combinações de filtro deixando a consulta lenta.
  Mitigação: os índices já previstos em `docs/03` cobrem os casos
  identificados; ajustar conforme medições reais, não suposições.
- UX de filtro confusa para o usuário final. Mitigação: já especificada
  em `docs/04` — seguir a especificação e validar com usuários reais
  (vendedores), não apenas com o time técnico.

**O que não deve ser feito ainda**:
- Não criar filtros especulativos não previstos em `docs/04`/`docs/06`
  — adicionar somente sob demanda real, observada no uso.

---

## Fase 9 — Orçamento composto por componentes

**Objetivo**: evoluir o fluxo de montagem (existente, em sua forma mais
simples, desde a Fase 3) para suportar **composição completa** —
múltiplos componentes físicos por linha lógica, com todas as regras de
compatibilidade (`docs/05`: RN-03 dimensão↔componente, RN-04
tampo↔estrutura, RN-05 acabamento↔SKU, RN-07 obrigatório/opcional), além
dos fluxos de edição mais ricos: troca de variação com recongelamento
explícito e duplicação de orçamento (RN-17).

**Por que essa fase vem nessa ordem**: agora o catálogo tem **dados
reais e ricos** (pós Fases 7-8) — exatamente o que falta para testar
regras de compatibilidade de verdade (não é possível validar
"tampo↔estrutura compatível" com dois produtos cadastrados à mão). E o
**esqueleto** do ciclo de vida do orçamento já foi provado e
estabilizado na Fase 3 — agora se constrói a parte mais complexa e mais
valiosa do sistema **sobre uma base já sólida**, em vez de tentar tudo
de uma vez (o que teria misturado bugs de ciclo de vida com bugs de
regra de composição, dificultando o diagnóstico de ambos).

**Entregáveis**:
- Endpoints completos de composição (`docs/06`, 14.11/14.12): múltiplos
  componentes por linha, adição de componente opcional a uma linha
  existente, troca de variação/acabamento com recongelamento
  (mostrando valor anterior × novo), duplicação de orçamento.
- Regras de compatibilidade implementadas e testadas, modeladas como
  **dado de configuração revisável** (não regra fixa em código —
  conforme a ressalva de RN-04 sobre a correspondência tampo↔estrutura
  ser inferida, não declarada explicitamente no PDF).
- Tela de montagem completa (Tela 7) e edição de item (Tela 8),
  conforme `docs/04`.

**Arquivos/módulos prováveis**: extensão substancial de
`backend/app/quotes/service.py` (regras de compatibilidade),
`frontend/src/pages/quotes/montagem` e `edicao` (versões completas).

**Critérios de aceite**:
- É possível montar um orçamento real com Tampo + Estrutura
  compatíveis (RN-04 validada contra dados reais publicados).
- Tentar uma combinação incompatível é bloqueada com mensagem
  específica e nomeada (`DESCRITOR_INCOMPATIVEL`/`DIMENSAO_INCOMPATIVEL`).
- Trocar o acabamento de um componente recongela corretamente o preço,
  mostrando o valor anterior e o novo lado a lado, antes de confirmar.
- Duplicar um orçamento gera a versão re-precificada com aviso
  explícito (RN-17), e sinaliza itens que não existem mais no catálogo
  vigente como pendências — nunca os omite silenciosamente.

**Testes mínimos**:
- Testes unitários de cada regra de compatibilidade, isolados.
- Teste de integração reproduzindo, com dados reais, os 4 exemplos de
  `docs/05`: orçamento simples (tampo+estrutura), orçamento com
  apoio+acessório, item bloqueado por ausência de preço, item com
  preço de versão antiga da tabela.

**Riscos**:
- O mapeamento tampo↔estrutura (RN-04) ser uma **inferência** (não um
  dado declarado no PDF — pergunta de validação 1 de `docs/05`) e
  precisar de ajuste manual contínuo conforme o catálogo real revela
  exceções. Mitigação: por isso ele é modelado como configuração
  revisável pela área comercial, não como regra fixa em código.
- Descobrir, só agora, que a matriz obrigatório/opcional (RN-07) estava
  incompleta ou equivocada. Mitigação: aceitável e esperado — corrigir
  agora, com volume controlado, é ordens de grandeza mais barato que
  corrigir com usuários dependendo do sistema.

**O que não deve ser feito ainda**:
- Não tentar prever toda combinação possível antes de ter dados reais
  publicados em volume — ajustar a matriz de compatibilidade de forma
  incremental, conforme o catálogo real for revelando os casos reais
  (e não os hipotéticos).

---

## Fase 10 — Exportação

**Objetivo**: implementar a geração e o download/visualização do
documento final do orçamento (PDF, com possível extensão futura para
planilha), a partir do *snapshot* congelado de totais.

**Por que essa fase vem nessa ordem**: investir em exportação só faz
sentido quando o **conteúdo** que ela exporta — orçamentos compostos,
com regras de composição corretas — já está estável (pós Fase 9).
Exportar algo cujo formato/estrutura ainda está mudando é retrabalho
garantido.

**Entregáveis**:
- Endpoint `GET /api/v1/quotes/{id}/export` (`docs/06`, 14.14), gerando
  o documento a partir do *snapshot* congelado (`quote_totals` +
  `quote_item_components` — nunca recalculando na hora de exportar).
- Tela de pré-visualização/exportação (Tela 9 de `docs/04`), com
  observações do fabricante e do vendedor claramente distinguidas
  (RN-11).

**Arquivos/módulos prováveis**: `backend/app/quotes/export.py`,
`frontend/src/pages/quotes/exportacao`.

**Critérios de aceite**:
- Exportar um orçamento gera um documento que reflete fielmente o
  *snapshot* congelado — valores, SKUs, observações — sem misturar
  observações de origens diferentes.
- Exportar duas vezes o mesmo orçamento (sem alterações) produz
  documentos com conteúdo idêntico (a exportação é **determinística**
  em relação ao *snapshot*, não ao estado "ao vivo").
- Tentar exportar um orçamento sem totais congelados é bloqueado
  (`TOTAIS_NAO_CALCULADOS`), com indicação clara do passo que falta.

**Testes mínimos**:
- Teste de geração a partir de um orçamento de referência, validando
  presença e correção dos campos centrais.
- Teste de bloqueio de exportação sem *snapshot* calculado.

**Riscos**:
- Escolha/integração da biblioteca de geração de documento consumir
  mais tempo que o esperado. Mitigação: começar pelo caminho mais
  simples (ex. geração de HTML e conversão para PDF) e refinar o
  layout depois, com o conteúdo já validado.
- Pressão para suportar múltiplos formatos inflar o escopo. Mitigação:
  entregar PDF primeiro (formato citado como principal em `docs/04`);
  avaliar planilha como incremento posterior, sob demanda real.

**O que não deve ser feito ainda**:
- Não investir em customização visual elaborada do documento antes de
  validar o **conteúdo** com usuários reais (vendedores e clientes).
- Não implementar envio automático por e-mail — não há especificação
  para isso em nenhum documento anterior; escopo não confirmado.

---

## Fase 11 — Logs, backup e hardening

**Objetivo**: implementar de fato as estratégias de logging, tratamento
de erros consistente, *backup* e revisão de segurança/robustez já
especificadas em `docs/06` (seções 8, 9 e 12) — agora que o sistema tem
funcionalidade completa para, de fato, "endurecer".

**Por que essa fase vem nessa ordem**: aplicar observabilidade e
*hardening* cedo demais geraria ruído sobre um sistema cuja forma ainda
estava mudando (cada nova fase alteraria pontos de log e tratamento de
erro recém-criados); aplicá-los tarde demais deixaria lacunas
acumuladas. Este é o ponto de equilíbrio: a funcionalidade está
completa, e o sistema ainda não está em operação real — janela ideal
para revisar tudo de forma centralizada e consistente.

**Entregáveis**:
- Logging estruturado consolidado em todos os módulos, seguindo a
  convenção de `docs/06` (seção 8): logs de requisição, de domínio e
  de erro, com `request_id` correlacionável.
- Envelope de erro padronizado e auditado em **todos** os endpoints —
  varredura para garantir que nenhum módulo escapou ao padrão definido
  na Fase 0/seção 9 de `docs/06`.
- Mecanismo de *backup* automatizado **e testado de fato** (banco +
  diretório de uploads — RN da seção 12 de `docs/06`).
- Revisão de segurança: autenticação, autorização por papel em cada
  endpoint sensível, validação de entrada.

**Arquivos/módulos prováveis**: consolidação final de
`backend/app/shared/logging.py` e `errors.py`, scripts de *backup*,
checklist de revisão de segurança (documento de apoio, não código).

**Critérios de aceite**:
- Toda exceção de domínio é logada (com `request_id`) e retorna o
  envelope padrão — nenhuma rota escapa.
- Um *backup* pode ser gerado **e restaurado** com sucesso, de forma
  testada (não apenas escrita em script e nunca executada).
- Cada endpoint sensível recusa corretamente um usuário sem o papel
  necessário (`403`, não `200` nem `500`).

**Testes mínimos**:
- Teste de que erros não tratados retornam `500` sem vazar detalhes
  internos (*stack trace*, SQL) na resposta ao cliente.
- Teste de restauração de *backup* de ponta a ponta.
- Testes de autorização por papel para os endpoints mais sensíveis
  (publicação de catálogo, aprovação de revisão, exportação).

**Riscos**:
- Esta fase **vai** descobrir lacunas de tratamento de erro espalhadas
  pelo código construído nas fases anteriores. Mitigação: isso é
  esperado e é exatamente o objetivo — encontrar e corrigir de forma
  centralizada, em vez de deixar cada lacuna ser descoberta em produção.
- Falso senso de segurança por *checklist* incompleto ou
  autoaplicado. Mitigação: revisão cruzada entre membros do time —
  quem implementou uma regra não deveria ser o único a validá-la.

**O que não deve ser feito ainda**:
- Não introduzir ferramentas externas de observabilidade (APM,
  agregadores de log) sem necessidade comprovada — os logs estruturados
  locais já atendem ao porte da aplicação descrito em `docs/06`, seção
  8; reavaliar somente se o uso real revelar o contrário.

---

## Fase 12 — Documentação de implantação

**Objetivo**: documentar como instalar, configurar, operar e dar
suporte à aplicação no seu ambiente real de uso — o "manual do
operador" que falta para o sistema sair do ambiente de desenvolvimento.

**Por que essa fase vem nessa ordem**: só faz sentido escrever isso por
último — depois que todas as decisões operacionais (logs, *backup*,
autenticação, migrations) estão implementadas **e estáveis**.
Documentar processos que ainda vão mudar é desperdício garantido — e
pior, gera confiança falsa em quem seguir a documentação desatualizada.

**Entregáveis**:
- Guia de instalação/configuração do zero.
- *Runbook* de operação: como aplicar migrations, como fazer e
  restaurar *backup*, como ler e interpretar logs, como reagir a erros
  comuns.
- Guia de primeiros passos para novos usuários, ligado diretamente às
  telas/fluxos já especificados em `docs/04-ux-operacional.md`.

**Arquivos/módulos prováveis**: `docs/08-implantacao.md` (ou
equivalente), `README.md` atualizado e promovido a ponto de entrada
operacional (não apenas "como rodar em desenvolvimento").

**Critérios de aceite**:
- Uma pessoa que não participou do desenvolvimento consegue, seguindo
  **apenas** a documentação, instalar, configurar e operar a aplicação
  — incluindo realizar um *backup* e uma restauração — sem precisar
  perguntar ao time.

**Testes mínimos**:
- "Teste de mesa": alguém de fora do time de desenvolvimento segue o
  guia do zero e relata exatamente onde travou (e a documentação é
  corrigida a partir disso — o teste real é esse ciclo, não a leitura).
- Checklist de operação executado ponta a ponta: subir o sistema,
  gerar *backup*, restaurar, interpretar um erro simulado a partir do
  log.

**Riscos**:
- Documentação ficar desatualizada rapidamente após o lançamento.
  Mitigação: tratar a atualização da documentação de implantação como
  parte obrigatória de qualquer mudança futura de infraestrutura — não
  como um documento estático e esquecível.
- Assumir conhecimento que o operador real não tem. Mitigação:
  exatamente o que o teste de mesa com pessoa de fora do time revela.

**O que não deve ser feito ainda**:
- Nada — esta é a última fase planejada. Necessidades identificadas
  aqui (ex. integração com SSO corporativo, necessidade de
  escalabilidade, suporte a múltiplos formatos de exportação) tornam-se
  itens de **backlog futuro** — não tarefas a encaixar retroativamente
  neste plano.

---

## Visão consolidada — o que cada "marco" prova

| Após a fase | O que já está provado, de ponta a ponta |
|---|---|
| 1 | O modelo de dados existe e é íntegro (FKs validadas) |
| 3 | O núcleo de negócio funciona — catálogo + orçamento + congelamento — **com dados controlados, sem PDF** |
| 6 | O pipeline de importação funciona até o "portão de revisão" — nenhum dado de baixa qualidade passa adiante sem aval humano |
| 7 | O sistema opera com **dados reais** de ponta a ponta — do PDF ao orçamento |
| 9 | As regras de composição mais complexas (e mais valiosas comercialmente) estão provadas contra dados reais em volume |
| 11 | O sistema está pronto, tecnicamente, para operar de forma confiável e recuperável |
| 12 | O sistema está pronto para ser **operado por alguém além do time que o construiu** |
