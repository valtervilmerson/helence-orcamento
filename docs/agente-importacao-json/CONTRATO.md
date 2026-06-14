# Contrato de importação via JSON (planilhas Excel)

> Complementa `docs/01` a `docs/07`. Descreve um **segundo caminho de
> importação**, paralelo ao pipeline de PDF (Fases 4-7), motivado pela
> mudança da fonte de preços para planilhas Excel
> (`data/TABELA DE PRECO 01-2026_*.xlsx`).

## 1. Motivação e responsabilidades

Até aqui, o sistema era responsável por **entender** o arquivo de
origem (PDF): localizar texto por coordenadas, agrupar linhas,
reconhecer códigos/preços/acabamentos (`backend/app/imports/extraction.py`).
Esse trabalho é específico de cada formato de origem e cresce em
complexidade a cada arquivo novo.

A proposta validada nesta tarefa inverte essa responsabilidade para
fontes em planilha:

- Um **agente de IA externo ao sistema** lê a(s) planilha(s) de origem
  (formato e leiaute variam por arquivo/aba — ver seção 4) e produz um
  **arquivo JSON** seguindo o contrato descrito abaixo.
- O sistema **não tenta mais entender Excel**. Ele recebe o JSON, valida
  contra o contrato, e a partir daí assume a responsabilidade normal:
  popular o banco (camada de importação + catálogo normalizado) e
  oferecer edição/orçamento dos itens.
- O **pipeline de PDF permanece como caminho legado**, sem alterações
  (`extraction.py`, upload/processamento de PDF, Fases 4-6 já
  implementadas). Os dois caminhos convergem na mesma tabela
  `extracted_items` e na mesma fila de revisão (`ReviewPage.tsx`,
  Fase 6).

## 2. Visão geral do fluxo

```
planilha(s) Excel  --[agente de IA externo]-->  JSON (contrato v1.0)
                                                       |
                                                       v
                                  POST /api/v1/imports/json (novo)
                                                       |
                          valida contrato + resolve entidades por nome
                                                       |
                              cria 1 linha em extracted_items por item
                                                       |
                       +-------------------------------------------------+
                       |                                                   |
            "limpo" -> aprovado automaticamente          "precisa de atenção" -> pendente
            (fast path)                                  (fila de revisão, Fase 6)
                       |                                                   |
            publica direto em                              segue fluxo normal:
            component_variants/skus/prices                 revisão -> aprovação -> publicação
                                                             (Fase 7, a publicar)
```

Os dois braços já existem (ou estão desenhados) no sistema atual:
- a fila de revisão e a correção em lote (`backend/app/imports/service.py`,
  `ReviewPage.tsx`) — Fase 6, já implementada;
- a publicação `extracted_items` aprovados → catálogo — Fase 7, ainda
  não implementada, e é pré-requisito tanto para o fast path quanto
  para o braço de revisão.

## 3. Contrato JSON

### 3.1 Envelope

```jsonc
{
  "contract_version": "1.0",
  "source": {
    "description": "TABELA DE PRECO 01-2026_REUNIOES.xlsx + ...",
    "generated_by": "agente-ia-externo",
    "generated_at": "2026-06-12T00:00:00Z"
  },
  "items": [ /* ver 3.2 */ ]
}
```

- `contract_version`: permite evoluir o contrato sem quebrar imports
  antigos guardados para auditoria.
- `source`: metadados livres para auditoria (gravados em
  `imported_files.notes` ou equivalente); não afeta a normalização.

> Não existe mais o conceito de "tabela de preços"/vigência. Cada item
> carrega o preço atual do `component_variant` correspondente; reimportar
> um item já existente apenas atualiza `prices.amount` (upsert).

### 3.2 Item

Cada item descreve **uma variação vendável** (de um item avulso a um
componente de um produto maior): família × (produto-base opcional) ×
componente × dimensão × acabamento × (SKU opcional) × preço — o mesmo
nível de granularidade de uma linha de `extracted_items`.

```jsonc
{
  "ref": "REUNIOES.xlsx!P900!L6,9",
  "family": "Mesas de Reunião",
  "product_context": "Reunião 1200x900",
  "component_type": "Tampo",
  "description": "Tampo Inteiro Simples Para Estrutura Reunião 1200x900 Caixa de Tomada Fosco",
  "dimension": "1200x900",
  "finish": "Argila",
  "finish_group": null,
  "sku": "3981113028",
  "price": 421.03,
  "currency": "BRL",
  "confidence": 0.97,
  "notes": null
}
```

| Campo | Tipo | Obrigatório | Mapeia para | Observações |
|---|---|:---:|---|---|
| `ref` | string | sim | `extracted_items.source_text` | Identificação legível da origem (arquivo, aba, linhas) — só auditoria, não é parseado. |
| `family` | string | sim | `product_families.name` (lookup; cria se ausente) | `extracted_items.family_raw` guarda o valor recebido. Também grava direto em `component_variants.family_id` — é a "linha de produto" do item, independente de `product_context`. |
| `product_context` | string ou `null` | não | `products.name` (lookup sob a família; cria se ausente) | `extracted_items.product_context_raw`. Ausente/`null` ⇒ item **avulso**, vendável por si só (`component_variants.product_id = NULL`). Presente ⇒ item é um componente de um produto-base (ex.: "Reunião 1200x900"). |
| `component_type` | string | sim | `product_components.name` (lookup; cria se ausente) | `extracted_items.component_type_raw`. |
| `description` | string | não | `component_variants.description` | `extracted_items.description_raw`. |
| `dimension` | string | sim | `dimensions` — parse de `"1200x900"` (W×D), `"900MM"` (diâmetro) ou `"1200x500x1000"` (W×D×H) | `extracted_items.dimension_raw`. Reaproveitar/extrair o parser de dimensão já usado em `extraction.py`, se existir. |
| `finish` | string | sim | `finishes.name` (lookup) | `extracted_items.finish_raw`. Criar uma `finish` nova **exige** `finish_group` (ver abaixo) — mesma regra já implementada na Fase 6 para "cadastrar novo acabamento". |
| `finish_group` | enum `madeirado\|metalico\|pe_estrutura\|outro` | só se `finish` for novo | `finishes.finish_group` | Ausente/`null` quando `finish` já existe. |
| `sku` | string ou `null` | não | `skus.code` (lookup/cria) | `extracted_items.sku_raw`. Ausente/`null` ⇒ `prices.sku_id = NULL` (item sem código de SKU próprio, ex.: produto completo vendido como um todo). |
| `price` | number | sim | `prices.amount` (2 casas decimais) — **um preço único por `component_variant`**, sem versionamento | `extracted_items.price_raw` guarda o valor recebido como string. Agente deve arredondar artefatos de ponto flutuante (ex.: `543.1800000000001` → `543.18`) antes de gerar o JSON. Reimportar o mesmo item com `price` diferente **atualiza** `prices.amount` (upsert). |
| `currency` | string | não (default `"BRL"`) | `prices.currency` / `extracted_items.currency` | |
| `confidence` | number 0-1 ou `null` | não | `extracted_items.confidence` + `confidence_level` derivado (`alta`≥0.9, `media`≥0.7, `baixa`<0.7; `null`→tratado como `baixa`) | Autoavaliação do agente — usada só para decidir fast path vs. revisão. |
| `notes` | string ou `null` | não | gera `import_warnings` (severity=`atencao`, ligado ao `extracted_item_id`) | Qualquer `notes` não nulo força `review_status='pendente'`, independente da confiança. |

### 3.3 Regra de fast path (revisão por exceção)

Um item é **aprovado automaticamente** (`review_status='aprovado'`,
publicado direto em `component_variants`/`skus`/`prices`) quando
**todas** as condições abaixo são verdadeiras:

1. `confidence` é `alta` (≥ 0.9);
2. `notes` é nulo/ausente;
3. `family`, `component_type` e `finish` **já existem** no catálogo, e
   `product_context` (quando informado) também já existe sob a família
   (nenhuma criação implícita de entidade que exija julgamento humano).

`sku` ausente/novo, `product_context` ausente (item avulso) e `price`
novo/atualizado **não** impedem o fast path — são exatamente o que se
espera de uma atualização normal de preços (criar/atualizar `skus` e
inserir/atualizar `prices` é mecânico).

Qualquer outro caso vai para `review_status='pendente'` na fila de
revisão (Fase 6), com um `import_warning` explicando o motivo (entidade
nova, confiança baixa/média, ou `notes` do agente).

> Nota: esta regra refina o critério originalmente esboçado (que também
> exigia `sku` pré-existente); exigir `sku` existente tornaria o fast
> path inútil para o caso comum de "atualização de preços com SKUs novos
> para variações já cadastradas".

### 3.4 Itens sem página real (`imported_pages` sintética)

`extracted_items.imported_page_id` é `NOT NULL` hoje. Para imports via
JSON (sem páginas físicas), o ingestor cria **uma única**
`imported_pages` por import, com `page_profile='json_import'` e
`page_number=1`, e associa todos os itens daquele JSON a ela. Isso
evita migração de schema agora; se no futuro isso for incômodo,
tornar `imported_page_id` nulável é uma migração simples e isolada.

`imported_files` ganha (trabalho futuro, não implementado nesta
entrega) uma forma de indicar a origem do arquivo — por exemplo uma
coluna `source_type CHECK (source_type IN ('pdf','json'))` — para que
telas de listagem possam diferenciar os dois caminhos. Até essa
migração existir, `original_filename` com extensão `.json` já permite
diferenciar visualmente.

## 4. Estrutura real das planilhas de origem (validação da viabilidade)

Levantamento feito sobre `data/TABELA DE PRECO 01-2026_REUNIOES.xlsx`
(15 abas) e `data/TABELA DE PRECO 01-2026_REUNIOES BISTRO.xlsx` (11
abas):

- Cada aba representa uma dimensão/linha de produto (ex.: abas
  `P900`...`P1800` na planilha REUNIOES, uma por largura).
- Linha de cabeçalho com a lista de acabamentos em colunas — **a ordem
  e o conjunto variam por arquivo/aba** (REUNIOES tem 9 acabamentos;
  BISTRO tem 8, em ordem diferente). O agente de IA deve ler esse
  cabeçalho dinamicamente, nunca assumir posição fixa.
- Padrão repetido em blocos: uma linha com um SKU por coluna de
  acabamento, seguida (na mesma linha ou poucas linhas depois) de uma
  linha de preços alinhada às mesmas colunas. A coluna A traz o
  modelo/dimensão, a coluna de descrição é frequentemente espalhada por
  2-4 linhas que precisam ser concatenadas.
- Preços trazem artefatos de ponto flutuante (ex.:
  `543.1800000000001`) — o agente arredonda antes de gerar o JSON
  (campo `price` do contrato já é o valor limpo).
- Há abas/colunas de apoio que devem ser ignoradas pelo agente (ex.:
  `CUSTOS_SISTEMA`, `ÍNDICE REVENDA`, `COEF`, `PERC_VENDA`, colunas
  extras à direita do cabeçalho de acabamentos).

Esse formato é mecânico e repetitivo — exatamente o tipo de
normalização que um agente de IA externo consegue produzir de forma
confiável a partir de um JSON de exemplo, confirmando a viabilidade da
abordagem.

## 5. Exemplo completo

Ver `data/exemplo_importacao_reunioes.json` — 12 itens reais extraídos
das duas planilhas citadas, cobrindo:

- **Fast path** (itens 1-6): família/produto/componente/acabamento já
  existentes no catálogo seed (`Mesas de Reunião` / `Reunião 1200x900` /
  `Tampo`), variando acabamento e SKU/preço — inclui um item cujo `sku`
  já existe no catálogo (atualização de preço pura) e itens com `sku`
  novo.
- **Revisão por novo tipo de componente** (itens 7-8): `component_type`
  `"Estrutura"` ainda não existe no catálogo; o item 7 também introduz
  o acabamento novo `"Prata"` (com `finish_group: "metalico"`).
- **Revisão por novo tipo + acabamento** (item 9): `component_type`
  `"Estrutura Apoio Credenza"` (novo) + `"Prata"` (novo).
- **Revisão por nova linha de produto** (itens 10-12, planilha BISTRO):
  `product_context` `"Reunião Bistrô 1200x500"` / `"...1300x500"` são
  novos; item 12 não informa `confidence` (`null`), forçando revisão
  por padrão.

## 6. O que falta para implementar (próxima rodada — fora do escopo desta entrega)

1. Endpoint `POST /api/v1/imports/json` — recebe o arquivo, valida
   contra o contrato (`pydantic`), grava `imported_files` +
   `imported_pages` sintética.
2. Serviço de resolução/criação de entidades por nome (família,
   produto, tipo de componente, dimensão, acabamento) com detecção de
   "entidade nova" para fins de `import_warnings`.
3. Cálculo de `confidence_level` e aplicação da regra de fast path
   (seção 3.3), incluindo a publicação direta em
   `component_variants`/`skus`/`prices` — depende da Fase 7
   (publicação), que ainda não existe e passa a ser pré-requisito
   também deste caminho.
4. Geração de `import_warnings` a partir de `notes` e de entidades
   novas detectadas.
5. Parser de `dimension` (`"1200x900"`, `"900MM"`, `"1200x500x1000"`) —
   verificar se já existe lógica equivalente em `extraction.py` para
   reaproveitar.
6. Testes de integração cobrindo: fast path, revisão por entidade nova,
   revisão por `notes`/confiança ausente, usando
   `data/exemplo_importacao_reunioes.json` como fixture.
