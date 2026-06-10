# Estratégia de testes e critérios de qualidade — MVP

> Documento de QA (não de implementação) que define **o que precisa
> estar testado, com que dado e com que critério de aceite**, antes de
> considerar o MVP pronto. Constrói sobre `docs/03-modelagem-sqlite.md`
> (schema), `docs/05-regras-orcamento.md` (RN-01 a RN-18),
> `docs/06-arquitetura-api.md` (códigos de erro e camadas) e
> `docs/07-plano-implementacao.md` (fases e critérios de aceite por
> fase). As fixtures usadas pelos exemplos abaixo estão em
> [`docs/samples/fixtures-orcamento.json`](samples/fixtures-orcamento.json),
> que reaproveita os dados reais já validados em
> `docs/samples/extracao-amostra.json` sempre que possível.

---

## 1. Princípios gerais

1. **Pirâmide de testes alinhada às camadas de `docs/06`** (seção 1):
   - **Unitários** — regras de negócio puras (`pricing.py`,
     compatibilidade, normalização de números/textos), sem banco nem
     HTTP. Maioria dos testes deve estar aqui — são os mais rápidos e
     os mais fáceis de tornar exaustivos.
   - **Integração** — fluxos completos contra um SQLite **temporário**
     (criado e destruído a cada teste/sessão), cobrindo
     repository→service→router. Usados para validar FKs, `UNIQUE`,
     `CHECK` e o contrato HTTP (status code + `error_code`).
   - **Ponta a ponta (E2E reduzido)** — os 4 exemplos de
     `docs/05-regras-orcamento.md` (seção 3), reproduzidos com as
     fixtures, mais o fluxo completo "extração → revisão → publicação →
     orçamento".

2. **Dados reais > dados ilustrativos > dados fictício-didáticos** —
   nessa ordem de preferência. `docs/samples/fixtures-orcamento.json`
   marca explicitamente a origem de cada registro
   (`_origem: real_da_amostra | ilustrativo | ficticio_didatico`) para
   que fique claro o que é garantia (já visto no PDF) e o que é
   construção deliberada para cobrir um caso-limite.

3. **Todo `error_code` nomeado em `docs/06` precisa de pelo menos um
   teste que o produza deliberadamente** — nunca apenas um teste de
   "caminho feliz" por endpoint. Um endpoint sem teste de erro nomeado
   é considerado **incompleto** para fins de MVP (ver seção 3).

4. **Nenhum teste depende de PDF real para rodar** — `data/source.pdf`
   é usado apenas no teste de gabarito da Fase 5 (comparação com
   `extracao-amostra.json`); todos os demais usam as fixtures JSON, que
   são determinísticas e versionadas.

5. **Banco de teste = SQLite em arquivo temporário ou `:memory:`**, com
   `PRAGMA foreign_keys = ON` ativado explicitamente em cada conexão
   (lembrete de `docs/03`, seção 3 — fácil de esquecer e mascara bugs
   de integridade).

---

## 2. As 14 categorias de teste

Cada categoria abaixo lista: **objetivo**, **camada(s)** (unitário/
integração/E2E), **fixtures usadas** (por `id` em
`fixtures-orcamento.json`), **regras de negócio relacionadas** e
**critérios de aceite mínimos**.

### 2.1 Testes de schema SQLite
**Objetivo**: garantir que `docs/schema/schema.sql` é aplicado de forma
íntegra, idempotente e com toda restrição declarada realmente ativa.

- **Camada**: integração.
- **Fixtures**: nenhuma (testa o schema vazio).
- **Casos**:
  1. Aplicar `0001_initial.sql` num banco temporário cria as 24 tabelas
     + 32 índices esperados (lista nominal, não só contagem).
  2. `PRAGMA foreign_key_check` retorna vazio após a criação.
  3. Rodar o executor de migrations duas vezes seguidas não falha nem
     duplica `schema_migrations`.
  4. Inserir um registro com FK inválida (ex. `products.family_id`
     inexistente) é **rejeitado** com `PRAGMA foreign_keys = ON` — e
     **aceito silenciosamente** se a pragma estiver desligada (teste
     negativo de regressão, para impedir reintrodução do esquecimento
     descrito em `docs/03`).
  5. Cada `CHECK` de domínio (seção 5 de `docs/03`) tem um teste que
     tenta inserir o valor inválido correspondente e confirma rejeição:
     `users.role` fora do enum, `prices.amount < 0`,
     `quote_items.quantity <= 0`, `extracted_items.confidence` fora de
     `[0,1]`, `dimensions` com as 4 grandezas nulas,
     `extracted_rows.is_vertical_text` fora de `{0,1}`.
  6. `UNIQUE` constraints (seção 5 de `docs/03`) — uma inserção
     duplicada de `dimensions(width_mm, depth_mm, diameter_mm,
     height_mm)`, `component_variants(product_id, component_id,
     dimension_id, finish_id, descriptor)` e
     `prices(component_variant_id, price_table_id)` é rejeitada pelo
     SQLite (não pela aplicação).
  7. `ON DELETE` — apagar um `imported_file` propaga `CASCADE` até
     `extracted_items`/`import_warnings`/`import_review_decisions`;
     apagar uma `price` referenciada por
     `quote_item_components.price_source_id` resulta em `SET NULL`
     (e **não** apaga a linha de orçamento nem o `frozen_unit_price`).

**Critério de aceite**: os 7 casos acima passam contra o
`schema.sql` real do repositório (não uma cópia simplificada).

---

### 2.2 Testes de importação
**Objetivo**: cobrir o ciclo "receber arquivo → registrar metadados →
detectar duplicata", conforme `docs/06` (14.1/14.2) e Fase 4 de
`docs/07`.

- **Camada**: integração.
- **Fixtures**: `price_tables` (id 1, 2 — `source_imported_file_id`
  1 e 2).
- **Casos**:
  1. Upload de um PDF válido cria `imported_files` com `file_hash`
     calculado, `status = 'recebido'`.
  2. Reenviar o **mesmo** arquivo (mesmo hash) retorna `409
     ARQUIVO_DUPLICADO` com `details.existing_import_id` apontando para
     o registro já existente — **não** cria um segundo registro.
  3. Upload de um arquivo que não é PDF (ou corrompido) retorna `400
     ARQUIVO_INVALIDO`.
  4. Listagem de importações (`GET /imports`) suporta paginação e
     filtro por `status`.
  5. `imported_pages(imported_file_id, page_number)` é `UNIQUE` —
     reprocessar não duplica páginas.

**Critério de aceite**: os 5 casos passam; nenhum teste depende do
conteúdo real do PDF (usar um PDF mínimo gerado em memória/fixture
binária para os casos 1–3).

---

### 2.3 Testes de normalização
**Objetivo**: validar as transformações texto-bruto → valor normalizado
que a extração aplica **antes** de gravar `extracted_items`.

- **Camada**: unitário (funções puras de normalização).
- **Fixtures**: `extracted_items_samples` ids `101` (cabeçalho
  `"NOGUEIRA\nCADIZ"` → `"Nogueira Cádiz"`) e `103` (`"744 ,22"` →
  `744.22`).
- **Casos**:
  1. `normalizar_preco("744 ,22")` → `Decimal("744.22")` — espaço
     interno antes da vírgula decimal é removido **antes** da
     conversão (não tratado como erro de formato).
  2. `normalizar_preco("382,75")` → `Decimal("382.75")` (caso simples,
     regressão).
  3. `normalizar_acabamento(["NOGUEIRA", "CADIZ"])` → `"Nogueira Cádiz"`
     — remontagem de cabeçalho multilinha via contagem cruzada
     cabeçalhos×colunas (não apenas concatenação ingênua com espaço, o
     que daria `"NOGUEIRA CADIZ"` sem acento/capitalização correta).
  4. Para o caso 3, `confidence` resultante é `0.85` (reduzida de uma
     base `0.95` por depender de heurística de remontagem) —
     confirmando que a normalização **não-trivial** rebaixa a
     confiança, conforme `extraction_notes` da fixture `101`.
  5. Texto vertical (`is_vertical_text = 1`, item `102`) **nunca** vira
     `extracted_item` — a função de normalização recebe esses spans
     filtrados por `dir=(0,-1)` e os descarta da lista de candidatos a
     item, mantendo-os apenas em `extracted_rows` para auditoria.

**Critério de aceite**: os 5 casos passam isoladamente, sem banco —
qualquer um deles falhando é bloqueante (são a base de toda a
extração).

---

### 2.4 Testes de revisão humana
**Objetivo**: cobrir `POST /extracted-items/{id}/review` (`docs/06`,
14.6) e o log `import_review_decisions`, conforme Fase 6 de `docs/07`.

- **Camada**: integração.
- **Fixtures**: `extracted_items_samples` ids `104` (`pendente`,
  `confidence_level = 'baixa'`), `107` (`pendente`, `confidence_level =
  'media'`).
- **Casos**:
  1. **Aprovar** o item `104` muda `review_status` para `aprovado` e
     grava uma linha em `import_review_decisions` com `decision =
     'aprovado'`, `user_id`, timestamp.
  2. **Rejeitar** o item `107` exige `motivo` (campo obrigatório) e
     grava `decision = 'rejeitado'` com o motivo.
  3. **Corrigir** um campo (ex. `finish_raw: "Cinza Platina"` →
     `"Carvalho"` no item `107`) grava `decision = 'corrigido'` com
     `field_corrected = 'finish_raw'`, `previous_value = 'Cinza
     Platina'`, `corrected_value = 'Carvalho'`.
  4. Tentar revisar **de novo** um item já com decisão final
     (`aprovado`/`rejeitado`) retorna `409 STATUS_INVALIDO` — reabrir
     exige uma ação explícita e diferente (não testada aqui, mas o
     bloqueio do caminho normal sim).
  5. **Correção em lote**: aplicar uma correção a todos os itens com
     `finish_raw = "Cinza Platina"` (apenas o item `107` na fixture)
     gera uma prévia, aplica a mudança, e **exclui** do escopo
     qualquer item que já tenha decisão humana registrada (simular
     adicionando um segundo item fictício já `aprovado` com o mesmo
     `finish_raw` e confirmar que ele **não** é alterado).

**Critério de aceite**: os 5 casos passam; o histórico em
`import_review_decisions` é append-only (nenhum `UPDATE`/`DELETE` em
linhas existentes durante os testes).

---

### 2.5 Testes de catálogo
**Objetivo**: CRUD do catálogo normalizado (`docs/06`, 14.9) e as
restrições de unicidade que impedem duplicação silenciosa.

- **Camada**: integração.
- **Fixtures**: `product_families` (id 1), `products` (ids 1–3),
  `product_components` (ids 1–3), `dimensions` (ids 1–3), `finishes`
  (ids 1–4), `component_variants` (ids 1–10), `skus`, `prices`.
- **Casos**:
  1. Cadastrar a cadeia completa família → produto → componente →
     dimensão → acabamento → variação → SKU → preço (replicando
     `component_variant_id = 1`, "Tampo Inteiro Simples 1200x900 —
     Argila", SKU `3981113028`, preço `382.75` na tabela `01-2025`) e
     recuperá-la com exatamente os mesmos dados.
  2. Repetir a criação da **mesma** `component_variant` (mesmo
     `product_id`+`component_id`+`dimension_id`+`finish_id`+
     `descriptor`) retorna `409 VARIACAO_DUPLICADA`.
  3. Repetir a criação de `prices` para a mesma
     `(component_variant_id, price_table_id)` retorna `409
     PRECO_DUPLICADO`.
  4. Criar uma `component_variant`/`price` referenciando um
     `dimension_id`/`finish_id`/`product_id` inexistente retorna `422
     REFERENCIA_INVALIDA`.
  5. Consulta "componentes por dimensão" (`docs/03`, 6.1) com
     `width=1200, depth=900` retorna as variações `1, 2, 3, 4, 5, 6, 7,
     9` (todas associadas a `dimension_id = 1`) e **não** retorna a
     `8` (associada a `dimension_id = 2`).
  6. Consulta "preço por acabamento" (`docs/03`, 6.2) com
     `finish = 'Argila'`, `tabela = '01-2025'` retorna a variação `1`
     com `amount = 382.75`.

**Critério de aceite**: os 6 casos passam; nenhum erro de banco "cru"
(mensagem SQLite) vaza para a resposta HTTP — sempre o `error_code`
nomeado.

---

### 2.6 Testes de orçamento
**Objetivo**: ciclo de vida básico de orçamento (Fase 3 de `docs/07`) —
criar, adicionar item(ns), calcular total, mudar status.

- **Camada**: integração + E2E (reproduz Exemplos 1 e 2 de `docs/05`).
- **Fixtures**: `customers` (id 1), `quote_scenarios` →
  `exemplo_1_simples_tampo_estrutura` e `exemplo_2_com_apoio_opcional`.
- **Casos**:
  1. Criar orçamento `901` para `customer_id = 1` ancora
     automaticamente em `price_table_id = 2` (a `vigente` no momento —
     RN-15), mesmo que o `setup` da fixture declare `price_table_id: 2`
     explicitamente (o teste deve **derivar** isso do estado
     `vigente`, não copiar o valor fixo).
  2. `POST /quotes/901/items` com os componentes `1` (Tampo Argila) e
     `4` (Estrutura Prata) → `201`, com `frozen_unit_price` = `412.90`
     e `612.40` respectivamente (preços da tabela `02-2025`,
     `prices id=7` e `id=10`), `line_subtotal = 2051.60` (= `(412.90 +
     612.40) × 2`).
  3. `POST /quotes/901/items/{itemId}/components` adicionando o
     componente opcional `7` (Apoio Credenza) → `201`, com
     `frozen_unit_price = 318.90` (`prices id=13`) e **propagação da
     quantidade da linha** (RN-08): `novo_line_subtotal = (412.90 +
     612.40 + 318.90) × 2 = 2688.40` — **não** `2701.40` (valor
     "armadilha" presente na fixture justamente para verificar que o
     teste aplica a regra em vez de copiar um número pronto).
  4. Atualizar `quantity` da linha de `2` para `3` recalcula
     `line_subtotal` proporcionalmente para os 3 componentes.
  5. Mudar `status` do orçamento de `rascunho` para outro estado exige
     passar pelo checklist RN-18 (ver categoria 2.7/2.8 para os casos
     de bloqueio específicos).

**Critério de aceite**: os 5 casos passam; o caso 3 falha
deliberadamente se o teste "decorar" `2701.40` — usado como
verificação de que a suíte testa a **regra**, não um valor fixo.

---

### 2.7 Testes de congelamento de preço
**Objetivo**: provar RN-16 — a regra "mais sensível do ponto de vista
de negócio" — de ponta a ponta.

- **Camada**: unitário (função de congelamento isolada) + integração.
- **Fixtures**: `quote_scenarios` → `exemplo_4_item_com_preco_de_versao_antiga`.
- **Casos**:
  1. Adicionar o componente `1` (Tampo Argila) ao orçamento `903`
     **enquanto a tabela `01-2025` (id=1) é a vigente** congela
     `frozen_unit_price = 382.75` (`prices id=1`).
  2. Publicar a tabela `02-2025` (id=2) como `vigente` (arquivando a
     `01-2025`) e atualizar o preço de catálogo da variação `1` para
     `412.90` (`prices id=7`).
  3. **Reler** o componente `1` já congelado no orçamento `903`: o
     `frozen_unit_price` continua `382.75` — **não** muda para
     `412.90`. Esta é a asserção central da categoria.
  4. Adicionar um **novo** componente (`7`, Apoio Credenza) ao mesmo
     orçamento `903`, agora com `02-2025` vigente, congela
     `frozen_unit_price = 318.90` (`prices id=13`) — preço **atual**
     no momento desta segunda adição (RN-15: cada adição usa a tabela
     vigente *no momento em que ocorre*).
  5. Apagar (ou arquivar) a linha `prices id=1` (origem do componente
     `1`) — `quote_item_components.price_source_id` vira `NULL`
     (`ON DELETE SET NULL`), mas `frozen_unit_price = 382.75`
     **permanece intacto e legível**.
  6. Trocar a variação do componente `1` (recongelamento — RN-16,
     "regra de recongelamento controlado") busca o preço **atual** da
     nova variação na tabela vigente, e o teste verifica que o
     resultado mostra **lado a lado** o valor anterior (`382.75`) e o
     novo, antes de confirmar.

**Critério de aceite**: caso 3 e caso 5 são os **bloqueantes** — se
qualquer um falhar, RN-16 está quebrada e o MVP não pode ser
considerado pronto (ver seção 3).

---

### 2.8 Testes de múltiplas versões de tabela de preço
**Objetivo**: RN-15 — ancoragem à tabela vigente, uso de tabela
não-vigente, e detecção de "orçamento de versão mista".

- **Camada**: integração.
- **Fixtures**: `price_tables` (id 1 = `substituida`, id 2 =
  `vigente`), `quote_scenarios` →
  `exemplo_4_item_com_preco_de_versao_antiga`.
- **Casos**:
  1. Criar um orçamento sem nenhuma tabela `vigente` cadastrada
     (estado hipotético, simulado num banco de teste isolado) retorna
     `409 NENHUMA_TABELA_VIGENTE`.
  2. Criar um orçamento com `02-2025` vigente preenche
     `quotes.price_table_id = 2` automaticamente — o vendedor **não**
     escolhe esse valor.
  3. Forçar o uso da tabela `01-2025` (`substituida`) exige
     confirmação explícita (`details.confirmado = true` ou similar) e
     o orçamento resultante carrega uma nota permanente/visível
     ("montado com base na tabela 01-2025, que não é mais a
     vigente").
  4. Reproduzir o orçamento `903` do Exemplo 4 (componente `1`
     congelado sob `01-2025`, componente `7` congelado sob `02-2025`)
     e confirmar que o orçamento expõe o aviso `code =
     "VERSOES_DE_TABELA_MISTAS"` com a mensagem listando **ambas** as
     versões (`01-2025` e `02-2025`).
  5. `quote_totals` é um *snapshot* gravado, não uma `view` — recalcular
     "ao vivo" (consulta 6.4a de `docs/03`) e comparar com o snapshot
     (6.4b): em caso de divergência proposital (alterar um preço de
     catálogo após o snapshot ser gravado), o **snapshot prevalece**.

**Critério de aceite**: caso 4 é o núcleo desta categoria — um
orçamento com itens de duas tabelas **sem** o aviso `
VERSOES_DE_TABELA_MISTAS` é considerado defeito bloqueante.

---

### 2.9 Testes de dados inconsistentes
**Objetivo**: garantir que ambiguidades e conflitos reais do catálogo
**não** são resolvidos automaticamente — exigem revisão humana ou
bloqueiam a publicação.

- **Camada**: integração.
- **Fixtures**: `finishes` ids `2` (`"Branco"`, `finish_group = NULL`)
  e `3` (`"Preto"`, `finish_group = NULL`); `extracted_items_samples`
  → `sku_duplicado_com_precos_divergentes` (ids `105`/`106`);
  `import_warnings_samples` id `203`.
- **Casos**:
  1. **Ambiguidade de acabamento (Branco/Preto)**: `finish_id = 2`
     ("Branco") é referenciado tanto por `component_variants id=2`
     (Tampo, contexto madeirado) quanto por `id=5` (Estrutura, contexto
     metálico). A consulta de "acabamentos disponíveis para Tampo"
     retorna `Branco` associado **apenas** ao `component_id = 1`
     (Tampo) — a desambiguação acontece via `component_id`, **não**
     via `finish_group` (que é `NULL` para este registro). Repetir o
     teste para "acabamentos disponíveis para Estrutura"
     (`component_id = 2`) também retorna `Branco`, associado a
     `id=5` — confirmando que a mesma linha de `finishes` serve aos
     dois contextos sem colisão.
  2. **SKU duplicado com preços divergentes** (itens `105`/`106`,
     mesmo `sku_raw = "398301122"`, preços `455.00` e `489.90`,
     acabamentos `Prata`/`Branco`): a importação que contém **ambos**
     gera o aviso `import_warnings id=203`,
     `severity = 'critico'`, e a tabela de preço correspondente
     **não pode** ser publicada (`POST /price-tables/{id}/publish`
     retorna `409` com referência a este conflito) até decisão humana.
  3. O conflito do caso 2 **não** é resolvido automaticamente
     escolhendo "o mais recente" ou "o mais barato" — o teste falha se
     a publicação prosseguir silenciosamente com qualquer um dos dois
     valores.

**Critério de aceite**: caso 2 é bloqueante — publicação silenciosa de
um catálogo com SKU duplicado e preços divergentes é considerada falha
crítica de integridade de dados.

---

### 2.10 Testes de PDFs com linhas quebradas
**Objetivo**: cobrir os três padrões reais de "quebra" identificados na
auditoria (`docs/01`/`docs/02`) — cabeçalho multilinha, texto vertical
espelhado, número com espaço interno.

- **Camada**: unitário (parsing/normalização) + integração (pipeline
  completo contra a amostra).
- **Fixtures**: `extracted_items_samples` ids `101`, `102`, `103`.
- **Casos**:
  1. **Cabeçalho em duas linhas** (`101`): `"NOGUEIRA"` + `"CADIZ"` em
     posições Y consecutivas, mesma coluna X, são remontados como uma
     única célula `"Nogueira Cádiz"` — via contagem cruzada de 9
     cabeçalhos × 9 colunas de código/preço (não por concatenação
     posicional ingênua, que falharia se a ordem de leitura não fosse
     estritamente top-to-bottom).
  2. **Texto vertical espelhado** (`102`): comparar a saída de uma lib
     genérica (`pdfplumber`/`camelot`, que produziria
     `["OCSOF", "ETNAHLIRB", ...]` — strings invertidas) com a saída do
     pipeline real (`pymupdf` filtrando por `dir=(0,-1)`, que produz
     `["FOSCO", "BRILHANTE", ...]`). O teste de regressão verifica que
     o pipeline **nunca** produz as strings invertidas e que esses 5
     spans **não** geram `extracted_items`.
  3. **Número com espaço interno** (`103`): `"744 ,22"` →
     `Decimal("744.22")` (já coberto em 2.3, repetido aqui no contexto
     de pipeline completo, com `confidence` rebaixada de `0.8` para
     `0.7`).
  4. **Teste de gabarito** (Fase 5 de `docs/07`): processar
     `data/source.pdf`, páginas 1, 2 e 432, e comparar a saída
     automatizada com `docs/samples/extracao-amostra.json` —
     diferenças de `description`/`confidence`/`review_status` para
     essas páginas são tratadas como regressão.

**Critério de aceite**: casos 1–3 são unitários e devem rodar em
milissegundos, sem PDF; caso 4 é o único teste do projeto que depende
de `data/source.pdf` e roda separadamente (ex. marcado como `slow`).

---

### 2.11 Testes de SKU duplicado
**Objetivo**: distinguir **reaproveitamento legítimo** de SKU (mesmo
componente físico vendido em contextos de largura diferentes, mesmo
preço) de **duplicação anômala** (mesmo código, preços/acabamentos
diferentes — categoria 2.9).

- **Camada**: integração.
- **Fixtures**: `component_variants` ids `4` (Estrutura
  1200x900 — Prata, SKU `398250071`) e `10` (Estrutura 1600x900 —
  Prata, **mesmo** SKU `398250071`); `skus` id `4` (nota explicando o
  reaproveitamento); `prices` ids `4`/`6`/`10`/`15` (mesmo
  `amount = 612.40` em ambas as variações, ambas as tabelas).
- **Casos**:
  1. Cadastrar `component_variants id=4` e `id=10`, ambas referenciando
     `sku_id = 4`, é **aceito** pelo schema — `skus` não tem FK direta
     para `component_variants` (decisão de modelagem de `docs/03`,
     2.3) exatamente para permitir N:N.
  2. Consultar "onde este SKU aparece" (`docs/03`, 6.3, adaptada) para
     `code = "398250071"` retorna **duas** linhas de `prices` (uma por
     `component_variant_id`, `4` e `10`), ambas com `amount = 612.40`
     na mesma `price_table_id` — confirmando que o mesmo código,
     mesmo preço, em dois contextos de largura, é **válido** e
     **esperado**.
  3. Diferença para a categoria 2.9: o teste explicitamente verifica
     que **nenhum aviso** é gerado para este caso (`import_warnings`
     vazio para este SKU) — em oposição ao SKU `398301122` (caso 2.9,
     aviso `critico`). A regra distintiva testada: **mesmo preço →
     reaproveitamento legítimo (sem aviso); preços/acabamentos
     divergentes → anomalia (aviso crítico)**.

**Critério de aceite**: os 3 casos passam; o teste 3 é o que prova que
a heurística de distinção (preço idêntico vs. divergente) está
implementada — não apenas "qualquer SKU repetido gera aviso", o que
geraria ruído excessivo (lembrando que a auditoria encontrou **9.287**
ocorrências legítimas desse padrão).

---

### 2.12 Testes de preço ausente
**Objetivo**: RN-12 nas **duas camadas** onde se manifesta — extração
(`price = NULL`, não publicado) e catálogo já publicado (variação sem
preço na tabela vigente, bloqueio na montagem).

- **Camada**: integração + E2E.
- **Fixtures**: `extracted_items_samples` id `104` (camada de
  extração, `sku_raw = "398101456"`, `price_raw = null`,
  `confidence_level = 'baixa'`); `component_variants` id `9` ("Tampo
  Encabeçado") + `prices` id `5` (preço **só** na tabela `01-2025`) +
  `quote_scenarios` → `exemplo_3_item_bloqueado_por_ausencia_de_preco`.
- **Casos — camada de extração**:
  1. O item `104` é extraído com `price_raw = null` e
     `confidence_level = 'baixa'`, gerando `import_warnings id=201`
     (`severity = 'atencao'`).
  2. Um item com `price = NULL` **não pode** atingir
     `review_status = 'aprovado'` por um caminho automático — se a
     área de catálogo decidir aprová-lo mesmo assim como "lacuna
     conhecida", isso deve ficar registrado explicitamente (campo/flag
     dedicado), não como um `aprovado` indistinguível dos demais.
- **Casos — camada de catálogo publicado**:
  3. `POST /quotes/902/items` com `component_variant_id = 9` (que tem
     preço **apenas** em `01-2025`, não em `02-2025`/vigente) retorna
     `422 ITEM_SEM_PRECO`, com `details.component_variant_id = 9`,
     `details.price_table_id = 2` e uma `explicacao` legível
     mencionando o preço histórico (`451.20`, tabela `01-2025`) e a
     ausência na vigente.
  4. A checagem do caso 3 ocorre **antes** da tentativa de inserção
     (a resposta `422` não deixa nenhum registro parcial em
     `quote_item_components`).
  5. RN-18 (checklist de fechamento): mesmo que, por falha em RN-12,
     um componente sem preço tenha entrado num orçamento por algum
     caminho não previsto, o checklist de fechamento (item 2 da seção
     2 de `docs/05`) o detecta e bloqueia o avanço — teste de "rede de
     segurança" inserindo o registro diretamente via repositório
     (bypass da regra de serviço) e confirmando que `POST
     /quotes/{id}/finalize` ainda assim bloqueia.

**Critério de aceite**: caso 3 é o mapeamento direto do Exemplo 3 de
`docs/05` e é bloqueante; caso 5 é o teste que prova que RN-18 é uma
**defesa em profundidade**, não uma reafirmação redundante de RN-12.

---

### 2.13 Testes de acabamento ausente
**Objetivo**: RN-05 (compatibilidade acabamento↔componente) no caso em
que o **nome** do acabamento extraído não existe em `finishes`.

- **Camada**: integração.
- **Fixtures**: `extracted_items_samples` id `107` (`finish_raw =
  "Cinza Platina"`, sem correspondência em `finishes`);
  `import_warnings_samples` id `204`.
- **Casos**:
  1. Extrair o item `107` com `finish_raw = "Cinza Platina"` gera
     `import_warnings id=204` (`severity = 'atencao'`), listando os
     acabamentos conhecidos para contraste, e mantém
     `review_status = 'pendente'` — **nenhuma** decisão automática
     (nem criar um `finish` novo, nem mapear para um existente).
  2. Na tela de revisão (categoria 2.4), o revisor tem duas opções
     válidas testáveis: (a) **corrigir** `finish_raw` para um nome
     existente (ex. `"Carvalho"`) — vira `decision = 'corrigido'`; ou
     (b) **aprovar como novo acabamento** — o teste confirma que essa
     ação cria uma nova linha em `finishes` **somente** como
     consequência de uma decisão humana explícita, nunca como efeito
     colateral da extração.
  3. **Filtro por grupo (RN-05, camada 1)**: mesmo após "Cinza Platina"
     virar um `finish` válido, tentar associá-lo a uma
     `component_variant` de `component_id` incompatível com seu
     `finish_group` (ex. um acabamento madeirado associado a
     `Estrutura`) é bloqueado na composição — reaproveita o teste de
     `finish_group` da categoria 2.5/2.9.
  4. **Verificação de existência real (RN-05, camada 2)**: mesmo que
     `"Carvalho"` exista em `finishes` com `finish_group` correto,
     tentar montar "Tampo Carvalho 2400x1000" (dimensão para a qual
     **não existe** `component_variant` cadastrada) cai no mesmo
     tratamento de RN-12 (`ITEM_SEM_PRECO`/sem variação encontrada) —
     **não** numa adição silenciosa com dado incompleto.

**Critério de aceite**: caso 1 é bloqueante (nenhuma criação automática
de `finish`); casos 3–4 conectam esta categoria às categorias 2.5 e
2.14, evidenciando que "acabamento ausente" não é um caso isolado, mas
uma instância das duas camadas de RN-05.

---

### 2.14 Testes de componente incompatível com dimensão
**Objetivo**: RN-03 — a lista de componentes/descritores oferecida para
uma dimensão é sempre derivada da existência real de `component_variant`
+ `prices`, nunca uma lista fixa.

- **Camada**: integração.
- **Fixtures**: `products` ids `1` (Reunião 1200x900) e `2` (Reunião
  2400x1000); `component_variants` id `8` (Tampo **Bi-Partido**
  2400x1000 — Argila, **só** existe para `dimension_id = 2`); `prices`
  id `14`.
- **Casos**:
  1. Consultar "descritores de Tampo disponíveis para Reunião
     1200x900" (`product_id = 1`, `dimension_id = 1`) retorna
     `["Inteiro Simples", "Encabeçado"]` (variações `1`, `2`, `3`, `9`)
     — **não** inclui `"Bi-Partido"`.
  2. Consultar a mesma lista para "Reunião 2400x1000" (`product_id =
     2`, `dimension_id = 2`) retorna `["Bi-Partido"]` (variação `8`),
     com preço `689.50` (`prices id=14`) na tabela `02-2025`.
  3. `POST /quotes/{id}/items` tentando montar "Reunião 1200x900 —
     Tampo Bi-Partido" (combinação `product_id=1` + descritor
     `"Bi-Partido"`, que **não existe** como `component_variant`)
     retorna `422 DIMENSAO_INCOMPATIVEL` — não `ITEM_SEM_PRECO` (a
     distinção semântica importa: aqui a combinação **não existe no
     catálogo**, não "existe mas sem preço").
  4. A mesma combinação montada para `product_id=2` (onde a variação
     `8` existe e tem preço) é aceita normalmente (caso de controle —
     prova que o bloqueio do caso 3 é específico da combinação, não um
     bloqueio geral de "Bi-Partido").

**Critério de aceite**: casos 1–2 validam RN-03 como **consulta ao
catálogo** (não regra hardcoded); caso 3 é bloqueante — se o sistema
permitir montar uma combinação inexistente, RN-03 está quebrada.

---

## 3. Critérios mínimos de qualidade para considerar o MVP pronto

O MVP é considerado pronto quando **todos** os itens abaixo são
verdadeiros — não é uma lista de "nice to have":

### 3.1 Cobertura funcional
- [ ] As 14 categorias de teste desta seção têm pelo menos os casos
      "bloqueantes" (marcados explicitamente em cada seção) passando.
- [ ] Os 4 exemplos de `docs/05-regras-orcamento.md` (seção 3) são
      reproduzíveis de ponta a ponta usando
      `docs/samples/fixtures-orcamento.json` (`quote_scenarios`).
- [ ] Todo `error_code` nomeado em `docs/06-arquitetura-api.md`
      relevante para as fases 1–7 do plano (`docs/07`) tem pelo menos
      um teste que o produz: `ARQUIVO_INVALIDO`, `ARQUIVO_DUPLICADO`,
      `STATUS_INVALIDO`, `ITENS_PENDENTES_DE_REVISAO`,
      `VARIACAO_DUPLICADA`, `PRECO_DUPLICADO`, `REFERENCIA_INVALIDA`,
      `NENHUMA_TABELA_VIGENTE`, `ITEM_SEM_PRECO`, `ITEM_SEM_SKU`,
      `DESCRITOR_INCOMPATIVEL`, `DIMENSAO_INCOMPATIVEL`,
      `QUANTIDADE_INVALIDA`, `DESCONTO_INVALIDO`,
      `VERSOES_DE_TABELA_MISTAS`, `TOTAIS_NAO_CALCULADOS`,
      `PARAMETRO_INVALIDO`, `FORMATO_INVALIDO`.

### 3.2 Integridade de dados (RN mais sensíveis)
- [ ] **RN-16 (congelamento)**: alterar/remover um preço de catálogo
      **nunca** altera um `frozen_unit_price` já gravado (categoria
      2.7, casos 3 e 5).
- [ ] **RN-12/13 (item sem preço/SKU)**: bloqueio ocorre **antes** da
      inserção, com `error_code` nomeado, em **ambas** as camadas
      (extração e montagem) — categoria 2.12.
- [ ] **RN-15 (versão mista)**: um orçamento com itens de duas tabelas
      diferentes **sempre** exibe `VERSOES_DE_TABELA_MISTAS` —
      categoria 2.8, caso 4.
- [ ] **`PRAGMA foreign_key_check`** retorna vazio após qualquer
      sequência de testes de integração que insira/remova dados (não
      apenas no banco vazio).

### 3.3 Tratamento honesto de incerteza
- [ ] Itens de `confidence_level = 'baixa'` **nunca** chegam a
      `component_variants`/`prices` sem passar por
      `review_status = 'aprovado'` (RN-14) — testável construindo um
      cenário onde isso é tentado diretamente via repositório (bypass)
      e confirmando que a camada de publicação rejeita.
- [ ] SKU duplicado com dados **divergentes** (categoria 2.9) bloqueia
      publicação; SKU duplicado com dados **idênticos** (categoria
      2.11) não gera aviso nem bloqueio — a distinção está testada nos
      dois sentidos.
- [ ] Acabamento não reconhecido (categoria 2.13) nunca cria um
      `finish` novo automaticamente.

### 3.4 Qualidade de execução da suíte
- [ ] Toda a suíte (exceto o teste de gabarito da categoria 2.10, caso
      4, marcado como `slow`) roda em menos de ~30s em CI, sem rede e
      sem dependência de PDF.
- [ ] Testes de integração usam um banco SQLite **isolado por teste**
      (arquivo temporário ou `:memory:` recriado) — nenhum teste
      depende de ordem de execução ou de estado deixado por outro.
- [ ] `docs/samples/fixtures-orcamento.json` é a **única** fonte de
      dados de teste para as categorias 2.5–2.14 — qualquer dado novo
      necessário é adicionado a esse arquivo (com `_origem` preenchida)
      em vez de inventado inline no código do teste, para manter
      rastreabilidade entre teste e documento de regras.

### 3.5 Auditabilidade
- [ ] A consulta "auditar origem de um preço" (`docs/03`, 6.5) é
      exercitada por pelo menos um teste de integração que percorre a
      cadeia completa `quote_item_components → prices →
      extracted_items → extracted_item_source_rows → extracted_rows →
      imported_pages → imported_files` e obtém um resultado não-nulo em
      cada elo.
- [ ] `import_review_decisions` é comprovadamente append-only ao longo
      de toda a suíte (nenhum teste faz `UPDATE`/`DELETE` direto nessa
      tabela).

---

## 4. O que este documento deliberadamente não cobre

- **Testes de carga/performance** — adiados para a Fase 8
  (`docs/07`), quando houver volume real de catálogo publicado; os
  critérios desta seção 3 cobrem **correção**, não desempenho.
- **Testes de UI/E2E via browser** — as telas de `docs/04-ux-operacional.md`
  são validadas manualmente nas fases correspondentes do plano; este
  documento cobre a camada de API/serviço/banco.
- **Testes de autenticação/autorização por papel** — escopo da Fase 11
  (`docs/07`, "Logs, backup e hardening"), quando os papéis
  Importador/Revisor/Aprovador/Vendedor/Auditor estiverem
  implementados.
- **Testes de desconto/margem (RN-09/RN-10)** — dependem de decisões
  comerciais ainda pendentes (perguntas de validação 5 e 6 de
  `docs/05`); quando essas regras forem confirmadas, esta seção 2 deve
  ganhar uma categoria 15 dedicada.
