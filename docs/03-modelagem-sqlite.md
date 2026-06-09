# Modelagem SQLite — catálogo, importação e orçamentos

> Baseado em `docs/01-auditoria-pdf-dominio.md` (mapa de domínio) e
> `docs/02-spike-extracao-pdf.md` + `docs/samples/extracao-amostra.json`
> (formato intermediário de extração já provado). DDL completo em
> [`docs/schema/schema.sql`](schema/schema.sql) — validado executando-o
> num banco SQLite em memória (24 tabelas + 32 índices, `PRAGMA
> foreign_key_check` sem inconsistências).
>
> Este documento descreve **o modelo de dados**, não a aplicação que o
> usa — não há código de importação/API/UI aqui, apenas schema + raciocínio.

---

## 1. Diagrama textual das entidades

O modelo é dividido em **três camadas** com dependência em uma única
direção — *importação → catálogo → orçamentos* — para que o catálogo
nunca precise "saber" como os dados foram extraídos, e os orçamentos
nunca precisem "saber" de onde os preços vieram (apenas referenciá-los).

```
┌─────────────────────────── CAMADA 1 — IMPORTAÇÃO / ORIGEM ───────────────────────────┐
│                                                                                       │
│  users ──1:N──> imported_files ──1:N──> price_tables                                 │
│                       │            (1 arquivo de origem gera N versões de tabela)    │
│                       │                                                               │
│                       └──1:N──> imported_pages ──1:N──> extracted_rows               │
│                                        │                                              │
│                                        └──1:N──> extracted_items                     │
│                                                       │                               │
│                                  N:N (extracted_item_source_rows)                     │
│                                        extracted_items ⇄ extracted_rows              │
│                                        (1 item pode vir de várias linhas e            │
│                                         1 linha pode alimentar vários itens)          │
│                                                       │                               │
│                                                       ├──1:N──> import_review_decisions│
│                                                       │              <──N:1── users    │
│                                                       │                               │
│   import_warnings ──N:1──> imported_files | imported_pages | extracted_items         │
│   (FKs nuláveis: um aviso pode apontar para qualquer granularidade)                  │
└───────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                          (prices.source_extracted_item_id)
                                          ▼
┌─────────────────────────── CAMADA 2 — CATÁLOGO NORMALIZADO ──────────────────────────┐
│                                                                                       │
│  product_families ──1:N──> products ──N:1──> dimensions                              │
│                                │      (dimensão "âncora" do produto-base)             │
│                                │                                                      │
│                                └──1:N──> component_variants                          │
│                                                  │──N:1──> product_components (tipo)  │
│                                                  │──N:1──> dimensions  (própria)      │
│                                                  │──N:1──> finishes                   │
│                                                  │                                    │
│                                                  └──1:N──> prices ──N:1──> skus       │
│                                                                  ──N:1──> price_tables│
│                                                                                       │
│  accessories ──1:1 (extensão)──> component_variants                                  │
│                  └──N:1──> products | product_components  (compatibilidade)          │
│                                                                                       │
│  business_rules ──N:1──> products | product_components | price_tables | imported_pages│
└───────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                       (quote_item_components.price_source_id)
                                          ▼
┌─────────────────────────────── CAMADA 3 — ORÇAMENTOS ────────────────────────────────┐
│                                                                                       │
│  customers ──1:N──> quotes <──N:1── price_tables   (versão-base usada na montagem)   │
│                        │     <──N:1── users          (criado_por)                    │
│                        │                                                              │
│                        ├──1:N──> quote_items ──N:1──> products                       │
│                        │              │                                              │
│                        │              └──1:N──> quote_item_components                │
│                        │                              │──N:1──> component_variants    │
│                        │                              │──N:1──> skus                  │
│                        │                              └──N:1──> prices (rastro,       │
│                        │                                         preço já CONGELADO)  │
│                        │                                                              │
│                        └──1:1──> quote_totals   (snapshot calculado e armazenado)     │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

**Cadeia completa de rastreabilidade** (de uma linha de orçamento até o
PDF original):

```
quote_item_components → prices → extracted_items → extracted_item_source_rows
   → extracted_rows → imported_pages → imported_files
```

---

## 2. Explicação das principais decisões

### 2.1 Três camadas com dependência em um único sentido
A separação *importação → catálogo → orçamentos* existe para isolar o
que muda por razões diferentes: a camada de importação muda quando o
**método de extração** evolui (nova versão de lib, nova heurística); o
catálogo muda quando o **negócio** muda (novo modelo, nova cor); os
orçamentos mudam quando **clientes** compram. Nenhuma camada depende de
detalhes internos da camada "abaixo" dela — o catálogo não tem nenhuma
coluna do tipo `raw_*` ou `confidence`, e os orçamentos não sabem se um
preço veio de PDF, planilha ou digitação manual.

### 2.2 `component_variants` como nó central de venda — e por que `price_table_id` NÃO é uma FK direta nele
O requisito diz: *"um componente pode ter múltiplas variações"* e
*"cada variação pode depender de acabamento, dimensão, tipo de
componente **e versão da tabela de preço**"*. As três primeiras
dependências viram FKs diretas (`component_id`, `dimension_id`,
`finish_id`). A quarta é resolvida **indiretamente**, através de
`prices`, e essa escolha é deliberada: a *definição* de uma variação
("Tampo Inteiro Simples, 1200×900, Carvalho") é atemporal — descreve uma
coisa que existe no catálogo do fabricante — enquanto sua
*representação comercial* (código, preço) muda a cada nova tabela. Se
`price_table_id` fosse uma coluna de `component_variants`, cada nova
versão da tabela obrigaria a duplicar a linha inteira da variação
(mesmo sem nenhuma mudança física no produto) só para registrar um novo
preço — poluindo o catálogo com cópias quase idênticas. Modelando a
dependência via `prices` (seção 2.3), a variação permanece **uma única
linha estável**, e cada versão de tabela apenas adiciona uma linha de
preço associada a ela.

### 2.3 `prices` como tabela-fato — onde SKU e preço se associam corretamente
`prices(component_variant_id, sku_id, price_table_id, amount, …)` com
`UNIQUE(component_variant_id, price_table_id)` é o ponto de encontro
exato exigido por *"SKU e preço devem ser associados à variação
correta"*: cada linha responde precisamente "nesta versão de tabela,
esta variação custa X e tem este código". Essa também é a razão de
`skus` **não** ter uma FK direta para `component_variants`: a auditoria
encontrou **9.287 códigos duplicados com preço idêntico**, reaparecendo
em variações de larguras/profundidades diferentes — ou seja, o mesmo
componente físico (ex.: um pé de estrutura) é revendido sob mais de um
contexto. Isso faz de SKU↔Variação uma relação **N:N por natureza**, e
`prices` — que de qualquer forma precisaria existir para registrar o
valor — é o lugar natural (e já normalizado) para resolvê-la, sem
precisar de uma tabela de associação extra.

### 2.4 Rastreabilidade ponta a ponta (arquivo → página → linha → item → preço → orçamento)
A cadeia documentada no fim da seção 1 satisfaz *"o banco deve
preservar rastreabilidade até arquivo, página e linha extraída"* de
forma literal — é possível partir de **qualquer preço usado em qualquer
orçamento** e chegar até a linha de texto exata (com coordenada Y) de
onde ele veio (consulta 5, seção 5). O elo `extracted_items ⇄
extracted_rows` é modelado como **N:N** via
`extracted_item_source_rows` porque a amostra real (página 2 do PDF, em
`docs/samples/extracao-amostra.json`) mostra descrições remontadas a
partir de 2–3 linhas físicas distintas — uma FK simples
(`extracted_items.row_id`) seria incapaz de capturar essa relação sem
perda de informação.

### 2.5 Múltiplas versões de tabela de preço
`price_tables` é uma entidade de catálogo de primeira classe — com
`code` (ex. `'01-2025'`), `valid_from`/`valid_to` e `status`
(`rascunho`/`vigente`/`substituida`/`arquivada`). Toda referência
comercial (`prices`, `quotes`, `business_rules`) aponta para uma versão
específica, então **nenhuma informação histórica é sobrescrita**: ao
chegar a tabela `02-2025`, o sistema simplesmente insere uma nova linha
em `price_tables` e novas linhas em `prices` — as antigas continuam
intactas e consultáveis.

### 2.6 Status de revisão em dois níveis (estado atual + histórico completo)
O requisito *"deve ser possível marcar dados como revisados, aprovados,
rejeitados ou corrigidos"* é atendido em **duas camadas
complementares**: `extracted_items.review_status` guarda o **estado
atual** (uma única coluna, ótima para filtrar "o que falta revisar" —
consulta 6); `import_review_decisions` é um **log append-only** de cada
decisão tomada, por quem, quando e — no caso de correções —
exatamente o que mudou (`field_corrected`/`previous_value`/
`corrected_value`). Sem o log, uma correção aplicada por engano não
poderia ser auditada nem revertida com segurança; sem a coluna de
estado, toda consulta de "pendências" precisaria de uma subquery sobre
o histórico inteiro.

### 2.7 Orçamento por composição — sem travar a decisão pendente da auditoria
A auditoria (`docs/01-…`, seção 5, perguntas 1 e 3) deixou em aberto se
o orçamento é **por composição de componentes** (tampo + estrutura +
apoio) ou por **item fechado** (kit). O modelo atende ao requisito
*"deve ser possível montar orçamento combinando componentes"* sem
forçar essa resposta agora: `quote_items` é a linha que o cliente vê
("Mesa de Reunião 1200×900 — Carvalho"), e `quote_item_components` é a
lista de 1+ componentes físicos que a compõem. Um **item fechado**
(ex.: mesa redonda vendida como unidade) é simplesmente um
`quote_item` com **um** componente; um **item composto** é um
`quote_item` com **vários**. Quando a área comercial responder à
pergunta 1, nenhuma alteração de schema será necessária — só muda
quantas linhas a aplicação insere.

### 2.8 Congelamento de preço (o requisito mais sensível do ponto de vista de negócio)
`quote_item_components` guarda uma **cópia** do valor no momento da
inclusão — `frozen_unit_price` + `frozen_currency` — que é,
dali em diante, o valor contratual do orçamento, **independente** do
que aconteça depois em `prices`/`price_tables`. `price_source_id`
(FK nulável para `prices`, com `ON DELETE SET NULL`) existe **apenas
para auditoria** ("de qual preço de catálogo este valor foi copiado") —
e o `SET NULL` garante que, mesmo que o preço de catálogo de origem
seja arquivado/removido numa limpeza futura, **o valor congelado
permanece intacto e legível**. `quote_totals` aplica exatamente o mesmo
princípio em nível agregado: é um *snapshot* calculado e gravado uma
vez (não uma view), para que um orçamento já enviado ao cliente nunca
mude de valor "sozinho" — mesmo que a fórmula de desconto/imposto/frete
evolua depois (consulta 4 mostra como recalcular para conferência sem
alterar o snapshot oficial).

### 2.9 `dimensions` normalizada e compartilhada — não três conjuntos de colunas
A auditoria encontrou **três formatos físicos de dimensão**:
retangular (`1200x900`), circular (`900MM`/`Diam 1350mm`) e
tridimensional (`1500 x 600 x 740 mm`, conectores STAFF). Em vez de
replicar pares `width_mm`/`depth_mm` (e inventar valores para os outros
formatos), `dimensions` guarda as quatro grandezas possíveis
(`width_mm`, `depth_mm`, `diameter_mm`, `height_mm`, todas nuláveis,
com `CHECK` garantindo que ao menos uma esteja presente) **em uma única
tabela reutilizável** — referenciada tanto por `products` quanto por
`component_variants`. Isso evita duplicar "1200×900" uma vez por
produto e outra por variação, e dá um único lugar para normalizar
`raw_label` → grandezas estruturadas.

### 2.10 `accessories` como extensão 1:1 de `component_variants` (não um fluxo paralelo)
Em vez de duplicar todo o fluxo comercial (SKU, preço, tabela de preço)
para os conectores STAFF, `accessories` é uma **tabela de extensão**
(`component_variant_id UNIQUE`): o acessório *é* uma
`component_variant` comum (com `component_id` apontando para o tipo
`'Acessório/Conector'`), e `accessories` apenas acrescenta os atributos
que **só fazem sentido para acessórios** — compatibilidade com produtos
e/ou tipos de componente específicos (ex.: "este conector serve para
tampos Bi-Partido"). Assim evitamos tanto a duplicação de SKU/preço
quanto a poluição de `component_variants` com colunas de compatibilidade
que ficariam `NULL` em 96% das linhas.

### 2.11 `business_rules` com FKs explícitas e nuláveis — não associação polimórfica
Observações de negócio (*"A Caixa de Tomada nos 1200x900 Tampos são
centralizadas"*, blocos de *"DESCRIÇÃO TÉCNICA"*) podem se aplicar a
níveis diferentes — produto, tipo de componente, versão de tabela ou só
a uma página. O padrão "polimórfico" clássico (`entity_type` +
`entity_id` genéricos) **não pode ser validado por FK** em SQLite (nem
na maioria dos bancos relacionais) — abre espaço para registros órfãos
silenciosos. Por isso o modelo usa **quatro FKs nuláveis explícitas**
(uma por alvo plausível): mais verboso, porém com integridade
referencial garantida pelo próprio motor — cada `business_rule`
aponta para algo que comprovadamente existe, ou para nada (regra
global).

### 2.12 Valores monetários como `NUMERIC` (decisão consciente de MVP)
O PDF de origem já entrega valores com 2 casas decimais
(`382,75` → `382.75`); usar `NUMERIC` evita uma camada de conversão na
importação e mantém o schema legível para esta fase de prova de modelo.
Registro consciente: bancos que fazem somas/agregações pesadas sobre
valores monetários costumam preferir **inteiro em centavos**
(`38275`) para eliminar de vez qualquer risco de erro de
arredondamento de ponto flutuante. Recomendo revisitar esse ponto
**antes de escalar para produção** — a migração é mecânica
(`amount_cents = ROUND(amount * 100)`), mas é mais barata decidir agora
do que depois de o catálogo estar populado.

### 2.13 `users`/`customers` minimalistas, por design
Incluídos porque o requisito pede *"se necessário"* — e são, de fato,
necessários: `imported_files`, `import_review_decisions` e `quotes`
precisam de um "quem" para a *"auditoria simples"* exigida, e `quotes`
obviamente precisa de um cliente. Ambas as tabelas foram mantidas
deliberadamente enxutas (sem papéis/permissões granulares, sem campos
de autenticação) — modelar controle de acesso é uma decisão de
**aplicação**, não de modelo de dados de domínio, e expandir essas
tabelas depois (adicionar colunas) é trivial e não-destrutivo.

---

## 3. DDL SQLite inicial

Arquivo completo: [`docs/schema/schema.sql`](schema/schema.sql).

Resumo das 24 tabelas (+ `sqlite_sequence`, gerada automaticamente pelo
SQLite por causa de `AUTOINCREMENT`), na ordem em que aparecem no
arquivo (ordem topológica — nenhuma FK aponta "para frente"):

| # | Camada | Tabela | Papel em uma frase |
|---|---|---|---|
| 1 | Importação | `users` | quem faz o quê (importa, revisa, cria orçamento) |
| 2 | Importação | `customers` | para quem se monta um orçamento |
| 3 | Importação | `imported_files` | um arquivo-fonte processado (PDF, hash, data) |
| 4 | Importação | `price_tables` | uma versão da tabela de preço (`'01-2025'`, vigência, status) |
| 5 | Importação | `imported_pages` | uma página processada (perfil de layout, seção) |
| 6 | Importação | `extracted_rows` | uma linha bruta de texto (raw_rows, com Y e flag de texto vertical) |
| 7 | Importação | `extracted_items` | um item candidato normalizado (com `confidence`/`review_status`) |
| 8 | Importação | `extracted_item_source_rows` | elo N:N item ⇄ linhas de origem |
| 9 | Importação | `import_warnings` | aviso ligado a arquivo/página/item |
| 10 | Importação | `import_review_decisions` | log de decisões humanas (aprovar/rejeitar/corrigir) |
| 11 | Catálogo | `dimensions` | grandezas normalizadas (LxP, diâmetro ou LxPxA) |
| 12 | Catálogo | `finishes` | acabamentos/cores, com agrupamento (madeirado/metálico/pé) |
| 13 | Catálogo | `product_families` | linha/família comercial (ex. "Mesas de Reunião") |
| 14 | Catálogo | `products` | produto-base (ex. "Reunião 1200x900") |
| 15 | Catálogo | `product_components` | catálogo de tipos de componente (Tampo, Estrutura, …) |
| 16 | Catálogo | `component_variants` | variação vendável (tipo + dimensão + acabamento + descritor) |
| 17 | Catálogo | `skus` | catálogo de códigos físicos |
| 18 | Catálogo | `prices` | fato comercial: variação + SKU + tabela → valor |
| 19 | Catálogo | `business_rules` | observações/regras associadas a produto/componente/tabela/página |
| 20 | Catálogo | `accessories` | extensão de variação para itens-acessório (compatibilidade) |
| 21 | Orçamentos | `quotes` | cabeçalho do orçamento (cliente, tabela-base, status) |
| 22 | Orçamentos | `quote_items` | linha lógica do orçamento (o que o cliente vê) |
| 23 | Orçamentos | `quote_item_components` | componentes que compõem a linha, com **preço congelado** |
| 24 | Orçamentos | `quote_totals` | snapshot calculado de subtotal/descontos/impostos/frete/total |

> **Nota de ambiente**: `PRAGMA foreign_keys = ON;` precisa ser executado
> em **cada conexão** — o SQLite não persiste essa configuração no
> arquivo do banco. Sem isso, todas as `REFERENCES` do schema são aceitas
> pelo parser mas **não são validadas** em tempo de execução.

---

## 4. Índices recomendados

Critério: cobrir (a) toda coluna de FK usada em `JOIN`s previsíveis a
partir das consultas de negócio (seção 6) e (b) colunas usadas em
filtros recorrentes que não são FK.

| Grupo | Índices | Por quê |
|---|---|---|
| Navegação na importação | `imported_pages(imported_file_id)`, `extracted_rows(imported_page_id)`, `extracted_items(imported_page_id)`, `extracted_item_source_rows(extracted_row_id)` | suportam a cadeia de rastreabilidade "de cima para baixo" (arquivo → página → linha/item) e "de baixo para cima" (linha → item) sem varredura completa |
| Filtros de revisão | `extracted_items(confidence_level)`, `extracted_items(review_status)` | atendem diretamente "listar itens com baixa confiança" e "o que falta revisar" — são as consultas mais frequentes em qualquer fluxo de curadoria |
| Avisos e decisões | `import_warnings(imported_file_id / imported_page_id / extracted_item_id)`, `import_review_decisions(extracted_item_id)` | permitem "quais avisos existem para este item/página/arquivo" e "qual o histórico de revisão deste item" sem table scan |
| Busca por dimensão | `dimensions(width_mm, depth_mm)`, `dimensions(diameter_mm)` | atendem diretamente a consulta 1 (buscar componente por dimensão), cobrindo tanto o caso retangular quanto o circular |
| Navegação no catálogo | `products(family_id)`, `component_variants(product_id / component_id / dimension_id / finish_id)` | suportam tanto "todas as variações deste produto" quanto "todas as variações deste tipo/dimensão/acabamento" (consultas 1–3) |
| Consulta comercial | `prices(component_variant_id / sku_id / price_table_id / source_extracted_item_id)` | suportam as quatro direções de navegação a partir do fato comercial: "preço desta variação", "onde este SKU aparece", "preços desta versão de tabela" e "auditar origem" (consultas 2, 3, 5) |
| Regras de negócio | `business_rules(applies_to_product_id / applies_to_component_id)` | suportam "quais regras valem para este produto/tipo" ao montar a descrição de um item |
| Orçamentos | `quotes(customer_id / price_table_id / status)`, `quote_items(quote_id / product_id)`, `quote_item_components(quote_item_id / component_variant_id / sku_id / price_source_id)` | suportam listagens operacionais ("orçamentos deste cliente", "orçamentos pendentes"), a montagem/exibição de um orçamento completo e o cálculo de total (consulta 4) |

Todas as `UNIQUE` constraints (seção 5) já criam índices implicitamente
— por isso `price_tables.code`, `skus.code`, `finishes.name` etc. **não**
aparecem duplicados na lista acima.

---

## 5. Constraints

### Unicidade (evitam duplicação silenciosa do mesmo dado)
- `price_tables.code`, `skus.code`, `finishes.name`,
  `product_families.name`, `product_components.name` — cada um é um
  identificador de negócio que deve ser único por definição.
- `dimensions(width_mm, depth_mm, diameter_mm, height_mm)` — impede
  criar duas linhas para "1200×900"; toda referência a essa dimensão
  reaproveita a mesma linha.
- `component_variants(product_id, component_id, dimension_id, finish_id, descriptor)`
  — impede duplicar a "mesma variação" (ex. duas linhas para "Tampo
  Inteiro Simples 1200×900 Carvalho").
- `prices(component_variant_id, price_table_id)` — impede duas linhas
  de preço para a mesma variação na mesma versão de tabela; é a
  constraint que **formaliza** o padrão observado na fonte ("um preço
  por variação por tabela").
- `imported_pages(imported_file_id, page_number)`,
  `extracted_rows(imported_page_id, sequence_no)` — impedem duplicar o
  registro da mesma página/linha ao reprocessar um arquivo.
- `accessories.component_variant_id`, `quote_totals.quote_id` —
  formalizam a relação 1:1 dessas tabelas de extensão.

### Validação de domínio (`CHECK`)
- Enums fechados via `CHECK (... IN (...))`: `users.role`,
  `price_tables.status`, `extracted_items.confidence_level`,
  `extracted_items.review_status`, `import_warnings.severity`,
  `import_review_decisions.decision`, `finishes.finish_group`,
  `quotes.status` — todos representam vocabulários fechados do domínio
  (definidos a partir da auditoria e do briefing); travar via `CHECK`
  evita que a aplicação grave um valor fora do conjunto conhecido (ex.
  `'aprovadoo'` por erro de digitação).
- `extracted_items.confidence BETWEEN 0.0 AND 1.0` — a pontuação de
  confiança é, por definição, uma proporção.
- `prices.amount >= 0`, `quote_item_components.frozen_unit_price >= 0`
  — preços não-negativos (um valor negativo indicaria erro de extração
  ou de digitação, nunca um preço de catálogo válido).
- `quote_items.quantity > 0`, `quote_item_components.quantity > 0` —
  uma linha de orçamento sem quantidade não faz sentido; zero deveria
  ser "remover a linha", não "manter com quantidade zero".
- `extracted_rows.is_vertical_text IN (0, 1)` — emula booleano (SQLite
  não tem tipo nativo).
- `dimensions`: `CHECK` garantindo que ao menos uma das quatro
  grandezas esteja preenchida — uma linha de dimensão "vazia" não tem
  sentido de domínio.

### `ON DELETE` — cascata vs. preservação
- **`CASCADE`** em toda a cadeia de importação
  (`imported_files → imported_pages → extracted_rows/extracted_items →
  extracted_item_source_rows/import_warnings/import_review_decisions`)
  e em `quotes → quote_items → quote_item_components` /
  `quotes → quote_totals`: remover um arquivo importado (ex. uma
  reimportação corrigida) ou um orçamento deve limpar tudo o que só
  existe em função dele — não deixar registros órfãos para trás.
- **`SET NULL`** apenas em `quote_item_components.price_source_id`:
  este é o único ponto do modelo em que "perder a referência" é
  **desejável** — o valor congelado (`frozen_unit_price`) é o que
  importa contratualmente, e ele sobrevive intacto mesmo que o preço de
  catálogo de origem seja removido numa limpeza futura. É a aplicação
  prática direta do requisito de congelamento.
- **Sem `ON DELETE`** (= `RESTRICT` implícito do SQLite) nas FKs do
  catálogo (`prices → component_variants/skus/price_tables`,
  `component_variants → products/…`): por design, **não deve ser
  possível apagar** uma variação, SKU ou versão de tabela que já tenha
  preços/orçamentos associados — isso destruiria histórico comercial.
  Se um item de catálogo for descontinuado, o caminho correto é marcar
  (`status`/flag), não excluir.

---

## 6. Exemplos de consulta

### 6.1 Buscar componentes por dimensão
```sql
-- Todas as variações vendáveis para a dimensão "1200 x 900"
SELECT cv.id, pc.name AS tipo_componente, p.name AS produto,
       d.raw_label AS dimensao, f.name AS acabamento, cv.descriptor
FROM component_variants cv
JOIN dimensions d            ON d.id = cv.dimension_id
JOIN product_components pc   ON pc.id = cv.component_id
LEFT JOIN products p         ON p.id = cv.product_id
LEFT JOIN finishes f         ON f.id = cv.finish_id
WHERE d.width_mm = 1200 AND d.depth_mm = 900;

-- Variante: mesas redondas por diâmetro
-- WHERE d.diameter_mm = 900
```

### 6.2 Buscar preço por acabamento
```sql
-- Preço de todas as variações com acabamento "Carvalho" na tabela 01-2025
SELECT pc.name AS componente, p.name AS produto, cv.descriptor,
       f.name AS acabamento, pr.amount, pr.currency, pt.code AS tabela
FROM prices pr
JOIN component_variants cv  ON cv.id = pr.component_variant_id
JOIN finishes f             ON f.id = cv.finish_id
JOIN product_components pc  ON pc.id = cv.component_id
JOIN price_tables pt        ON pt.id = pr.price_table_id
LEFT JOIN products p        ON p.id = cv.product_id
WHERE f.name = 'Carvalho' AND pt.code = '01-2025';
```

### 6.3 Buscar SKU por componente e acabamento
```sql
-- Código (SKU) e preço de "Tampo" com acabamento "Argila" na tabela 01-2025
SELECT s.code AS sku, pr.amount, pr.currency,
       p.name AS produto, cv.descriptor, f.name AS acabamento
FROM skus s
JOIN prices pr              ON pr.sku_id = s.id
JOIN component_variants cv  ON cv.id = pr.component_variant_id
JOIN product_components pc  ON pc.id = cv.component_id
JOIN finishes f             ON f.id = cv.finish_id
JOIN price_tables pt        ON pt.id = pr.price_table_id
LEFT JOIN products p        ON p.id = cv.product_id
WHERE pc.name = 'Tampo' AND f.name = 'Argila' AND pt.code = '01-2025';
```

### 6.4 Calcular total de um orçamento
```sql
-- (a) Recalcular "ao vivo" a partir dos itens com preço congelado
--     (útil para CONFERIR o snapshot oficial, não para substituí-lo)
SELECT qi.quote_id,
       SUM(qic.frozen_unit_price * qic.quantity * qi.quantity) AS subtotal_recalculado
FROM quote_item_components qic
JOIN quote_items qi ON qi.id = qic.quote_item_id
WHERE qi.quote_id = :quote_id
GROUP BY qi.quote_id;

-- (b) Ler o snapshot OFICIAL armazenado (o valor que vale para o cliente)
SELECT subtotal, discount_percent, discount_amount,
       tax_amount, freight_amount, total, currency, calculated_at
FROM quote_totals
WHERE quote_id = :quote_id;
```
> Em caso de divergência entre (a) e (b), (b) prevalece — é o valor
> congelado no momento do fechamento; (a) serve só para auditoria/QA.

### 6.5 Auditar origem de um preço
```sql
-- De um preço de catálogo até o arquivo/página/linha exatos de origem
SELECT pr.id AS price_id, pr.amount, pr.currency, pt.code AS tabela,
       s.code AS sku, cv.descriptor,
       ei.confidence_level, ei.review_status, ei.source_text,
       er.sequence_no, er.y_coordinate, er.raw_text, er.is_vertical_text,
       ip.page_number, ip.page_profile, ip.section,
       imf.file_path, imf.imported_at
FROM prices pr
JOIN price_tables pt          ON pt.id = pr.price_table_id
JOIN skus s                   ON s.id = pr.sku_id
JOIN component_variants cv    ON cv.id = pr.component_variant_id
LEFT JOIN extracted_items ei  ON ei.id = pr.source_extracted_item_id
LEFT JOIN extracted_item_source_rows eisr ON eisr.extracted_item_id = ei.id
LEFT JOIN extracted_rows er   ON er.id = eisr.extracted_row_id
LEFT JOIN imported_pages ip   ON ip.id = ei.imported_page_id
LEFT JOIN imported_files imf  ON imf.id = ip.imported_file_id
WHERE pr.id = :price_id
ORDER BY er.sequence_no;
```
> A mesma consulta, partindo de `quote_item_components.price_source_id`
> em vez de `prices.id`, audita a origem de **um valor usado num
> orçamento** — fechando a cadeia de ponta a ponta descrita na seção 1.

### 6.6 Listar itens com baixa confiança de importação
```sql
-- Itens que exigem revisão obrigatória (ver critérios no doc 02, seção 4)
SELECT ei.id, ei.confidence, ei.confidence_level, ei.review_status,
       ei.description_raw, ei.sku_raw, ei.price_raw, ei.finish_raw,
       ip.page_number, ip.page_profile, imf.file_path
FROM extracted_items ei
JOIN imported_pages ip   ON ip.id = ei.imported_page_id
JOIN imported_files imf  ON imf.id = ip.imported_file_id
WHERE ei.confidence_level = 'baixa'
   OR ei.confidence < 0.5
   OR ei.review_status = 'pendente'
ORDER BY ei.confidence ASC;
```

---

## 7. O que este documento deliberadamente não resolve

Por construção, o modelo **comporta** as duas respostas possíveis às
perguntas em aberto da auditoria (composição vs. item fechado; seleção
de acabamento por componente vs. global) sem exigir alteração de
schema — mas **não as resolve**. Essas continuam sendo decisões de
negócio a validar antes de implementar a aplicação (ver
`docs/01-auditoria-pdf-dominio.md`, seção 5). Da mesma forma, margens,
descontos, impostos e frete têm colunas reservadas em `quote_totals`,
mas **as regras de cálculo** desses valores não são modeladas aqui —
dependem de informação de negócio que não está no PDF.
