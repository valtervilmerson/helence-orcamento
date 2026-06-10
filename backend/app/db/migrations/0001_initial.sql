-- ===========================================================================
-- Migration 0001 — schema inicial
-- Helence Orçamento — Modelo de dados SQLite
-- (camada de importação, catálogo normalizado e orçamentos)
--
-- Espelha docs/schema/schema.sql (já validado, incluindo
-- PRAGMA foreign_key_check). Ver docs/03-modelagem-sqlite.md para o
-- diagrama de entidades, a justificativa das decisões de modelagem,
-- índices e exemplos de consulta.
--
-- Convenções adotadas:
--   - Chaves primárias: INTEGER PRIMARY KEY AUTOINCREMENT — preserva o id
--     mesmo após exclusões, o que importa para trilhas de auditoria
--     (ex.: um aviso pode referenciar um item já removido sem reciclar id).
--   - Datas/horas: TEXT em formato ISO-8601 ('YYYY-MM-DD HH:MM:SS').
--   - Valores monetários: NUMERIC com 2 casas decimais (mesma unidade que
--     "currency"). Ver nota sobre uso de inteiro em centavos na seção
--     "Decisões de modelagem" do documento — escolha deliberada de MVP.
--   - Booleanos: INTEGER 0/1 com CHECK, por não existir tipo BOOLEAN nativo.
--   - PRAGMA foreign_keys deve ser ativado por conexão (não é persistido
--     no arquivo do banco): execute "PRAGMA foreign_keys = ON;" sempre que
--     abrir uma nova conexão para que as constraints de FK sejam validadas.
-- ===========================================================================

PRAGMA foreign_keys = ON;

-- ===========================================================================
-- 1. CAMADA DE ORIGEM / IMPORTAÇÃO
--    Preserva rastreabilidade até arquivo, página e linha extraída, e
--    registra avisos e decisões humanas de revisão (aprovar/rejeitar/corrigir).
-- ===========================================================================

CREATE TABLE users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    email       TEXT UNIQUE,
    role        TEXT NOT NULL DEFAULT 'colaborador'
                    CHECK (role IN ('admin', 'importador', 'revisor', 'vendedor', 'colaborador')),
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE customers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    document    TEXT,                       -- CNPJ/CPF
    email       TEXT,
    phone       TEXT,
    address     TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE imported_files (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path            TEXT NOT NULL,
    file_hash            TEXT,                -- sha256 do conteúdo (dedup/integridade)
    original_filename    TEXT,
    page_count           INTEGER,
    imported_at          TEXT NOT NULL DEFAULT (datetime('now')),
    imported_by_user_id  INTEGER REFERENCES users(id),
    notes                TEXT
);

-- Uma versão da tabela de preço (ex.: "01-2025") nasce de um arquivo
-- importado. O sentido da FK é deliberadamente este (e não o inverso) —
-- ver "Decisões de modelagem" no documento.
CREATE TABLE price_tables (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    code                     TEXT NOT NULL UNIQUE,        -- ex.: '01-2025'
    name                     TEXT,                        -- ex.: 'Tabela de Preços 01-2025'
    valid_from               TEXT,                        -- data 'YYYY-MM-DD'
    valid_to                 TEXT,
    status                   TEXT NOT NULL DEFAULT 'rascunho'
                                 CHECK (status IN ('rascunho', 'vigente', 'substituida', 'arquivada')),
    source_imported_file_id  INTEGER REFERENCES imported_files(id),
    created_at               TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE imported_pages (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    imported_file_id  INTEGER NOT NULL REFERENCES imported_files(id) ON DELETE CASCADE,
    page_number       INTEGER NOT NULL,
    page_profile      TEXT,        -- ex.: 'tampo_padrao' | 'redonda_lounge' | 'indice'
    section           TEXT,        -- cabeçalho de seção detectado na página
    UNIQUE (imported_file_id, page_number)
);

CREATE TABLE extracted_rows (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    imported_page_id  INTEGER NOT NULL REFERENCES imported_pages(id) ON DELETE CASCADE,
    sequence_no       INTEGER NOT NULL,   -- ordem de leitura dentro da página
    y_coordinate      REAL,               -- posição vertical, quando disponível
    raw_text          TEXT NOT NULL,
    is_vertical_text  INTEGER NOT NULL DEFAULT 0 CHECK (is_vertical_text IN (0, 1)),
    UNIQUE (imported_page_id, sequence_no)
);

CREATE TABLE extracted_items (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    imported_page_id     INTEGER NOT NULL REFERENCES imported_pages(id) ON DELETE CASCADE,
    family_raw           TEXT,
    product_context_raw  TEXT,
    component_type_raw   TEXT,
    description_raw      TEXT,
    dimension_raw        TEXT,            -- texto original, ex.: '1200x900', '900MM'
    finish_raw           TEXT,
    sku_raw              TEXT,
    price_raw            TEXT,            -- texto original antes da normalização (ex.: '744 ,22')
    currency             TEXT NOT NULL DEFAULT 'BRL',
    confidence           REAL CHECK (confidence BETWEEN 0.0 AND 1.0),
    confidence_level     TEXT CHECK (confidence_level IN ('alta', 'media', 'baixa')),
    source_text          TEXT,            -- concatenação do(s) trecho(s) brutos de origem
    extraction_notes     TEXT,            -- JSON: lista de heurísticas aplicadas a este item
    review_status        TEXT NOT NULL DEFAULT 'pendente'
                             CHECK (review_status IN ('pendente', 'revisado', 'aprovado', 'rejeitado', 'corrigido')),
    created_at           TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Liga cada item normalizado às linhas brutas que o originaram. É N:N
-- porque (a) uma descrição pode ser remontada a partir de várias linhas
-- físicas (ex.: "Para Estrutura Reunião" + "A Caixa de Tomada..." na
-- amostra real da página 2) e (b) uma mesma linha de cabeçalho pode
-- alimentar vários itens (ex.: 1 linha de códigos + 1 de preços geram
-- 9 itens, um por acabamento).
CREATE TABLE extracted_item_source_rows (
    extracted_item_id  INTEGER NOT NULL REFERENCES extracted_items(id) ON DELETE CASCADE,
    extracted_row_id   INTEGER NOT NULL REFERENCES extracted_rows(id)  ON DELETE CASCADE,
    PRIMARY KEY (extracted_item_id, extracted_row_id)
);

CREATE TABLE import_warnings (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    imported_file_id   INTEGER NOT NULL REFERENCES imported_files(id) ON DELETE CASCADE,
    imported_page_id   INTEGER REFERENCES imported_pages(id) ON DELETE CASCADE,
    extracted_item_id  INTEGER REFERENCES extracted_items(id) ON DELETE CASCADE,
    severity           TEXT NOT NULL DEFAULT 'atencao'
                           CHECK (severity IN ('info', 'atencao', 'critico')),
    message            TEXT NOT NULL,
    created_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Registro append-only de toda decisão humana sobre um item extraído —
-- a auditoria completa ("quem, quando, o quê mudou"). O estado "atual"
-- fica em extracted_items.review_status (consulta rápida); o histórico
-- completo fica aqui (consulta de auditoria/disputa).
CREATE TABLE import_review_decisions (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    extracted_item_id    INTEGER NOT NULL REFERENCES extracted_items(id) ON DELETE CASCADE,
    decision             TEXT NOT NULL
                             CHECK (decision IN ('revisado', 'aprovado', 'rejeitado', 'corrigido')),
    reviewed_by_user_id  INTEGER REFERENCES users(id),
    reviewed_at          TEXT NOT NULL DEFAULT (datetime('now')),
    field_corrected      TEXT,    -- nome do campo alterado (preenchido só quando decision = 'corrigido')
    previous_value       TEXT,
    corrected_value      TEXT,
    notes                TEXT
);

-- ===========================================================================
-- 2. CATÁLOGO NORMALIZADO
--    Domínio "limpo": famílias, produtos-base, tipos de componente,
--    dimensões, acabamentos, variações vendáveis, SKUs e preços — já
--    desacoplado do texto bruto e do processo de extração do PDF.
-- ===========================================================================

-- Representação única e reutilizável de dimensão. Um único formato de
-- registro cobre os 3 padrões encontrados na auditoria: retangular
-- (width/depth), circular (diameter) e tridimensional (width/depth/height
-- — conectores STAFF), evitando colunas fantasmas e duplicação de "1200x900"
-- entre produto e cada uma de suas variações.
CREATE TABLE dimensions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    width_mm     INTEGER,
    depth_mm     INTEGER,
    diameter_mm  INTEGER,
    height_mm    INTEGER,
    raw_label    TEXT,      -- texto original, ex.: '1200x900', '900MM', '1500 x 600 x 740 mm'
    UNIQUE (width_mm, depth_mm, diameter_mm, height_mm),
    CHECK (width_mm IS NOT NULL OR depth_mm IS NOT NULL
           OR diameter_mm IS NOT NULL OR height_mm IS NOT NULL)
);

CREATE TABLE finishes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL UNIQUE,        -- ex.: 'Argila', 'Nogueira Cádiz', 'Prata'
    finish_group  TEXT
                      CHECK (finish_group IN ('madeirado', 'metalico', 'pe_estrutura', 'outro')),
    description   TEXT
);

CREATE TABLE product_families (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL UNIQUE,         -- ex.: 'Mesas de Reunião'
    description  TEXT
);

-- "Produto-base": a combinação largura×profundidade que ancora um bloco
-- de linhas (ex.: 'Reunião 1200x900'). Não é, em si, um item vendável —
-- é o contexto que agrupa as variações de componente.
CREATE TABLE products (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    family_id     INTEGER NOT NULL REFERENCES product_families(id),
    name          TEXT NOT NULL,                       -- ex.: 'Reunião 1200x900'
    dimension_id  INTEGER REFERENCES dimensions(id),   -- dimensão "âncora" do produto-base
    UNIQUE (family_id, name)
);

-- Catálogo de TIPOS de componente (não instâncias): Tampo, Estrutura,
-- Apoio/Credenza, Conjunto Completo (mesas redondas/lounge vendidas como
-- unidade), Acessório/Conector.
CREATE TABLE product_components (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL UNIQUE,
    description  TEXT
);

-- Variação vendável concreta: cruza tipo de componente + produto-base +
-- dimensão + acabamento + um "descritor" textual (Simples, Encabeçado,
-- Bi-Partido, Pé Painel...). É o nível em que SKU e preço se associam
-- corretamente — ver "Decisões de modelagem" no documento para o porquê
-- de "versão da tabela de preço" NÃO ser uma FK direta aqui.
CREATE TABLE component_variants (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id    INTEGER REFERENCES products(id),          -- nulo para itens não ancorados a um produto-base (ex.: acessórios)
    component_id  INTEGER NOT NULL REFERENCES product_components(id),
    dimension_id  INTEGER REFERENCES dimensions(id),
    finish_id     INTEGER REFERENCES finishes(id),
    descriptor    TEXT,             -- ex.: 'Simples', 'Encabeçado', 'Bi-Partido', 'Pé Painel'
    description   TEXT,
    UNIQUE (product_id, component_id, dimension_id, finish_id, descriptor)
);

-- Catálogo de códigos físicos. Sem FK direta para component_variants:
-- a auditoria confirmou 9.287 códigos que se repetem, com preço idêntico,
-- em mais de uma variação (a mesma peça estrutural física é revendida em
-- diferentes contextos de largura/profundidade) — ou seja, SKU↔Variação
-- é N:N por natureza, e quem resolve essa relação é "prices" (ver abaixo).
CREATE TABLE skus (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    code   TEXT NOT NULL UNIQUE,
    notes  TEXT
);

-- Tabela-fato comercial: o único lugar em que "variação + SKU + versão de
-- tabela" se encontram com um valor monetário. UNIQUE(variação, tabela)
-- garante no máximo um preço vigente por variação em cada versão —
-- replicando o padrão observado no PDF de origem — e ainda preserva o
-- rastro até o item extraído que originou o valor.
CREATE TABLE prices (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    component_variant_id      INTEGER NOT NULL REFERENCES component_variants(id),
    sku_id                    INTEGER NOT NULL REFERENCES skus(id),
    price_table_id            INTEGER NOT NULL REFERENCES price_tables(id),
    amount                    NUMERIC NOT NULL CHECK (amount >= 0),
    currency                  TEXT NOT NULL DEFAULT 'BRL',
    source_extracted_item_id  INTEGER REFERENCES extracted_items(id),
    created_at                TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (component_variant_id, price_table_id)
);

-- Observações/regras de negócio em texto livre (ex.: "A Caixa de Tomada
-- nos 1200x900 Tampos são centralizadas", blocos de "DESCRIÇÃO TÉCNICA").
-- FKs nuláveis e explícitas para cada alvo plausível — em vez de uma
-- associação polimórfica genérica (entity_type/entity_id), que o SQLite
-- não consegue validar via FK e abriria espaço para referências inválidas.
CREATE TABLE business_rules (
    id                         INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_text                  TEXT NOT NULL,
    applies_to_product_id      INTEGER REFERENCES products(id),
    applies_to_component_id    INTEGER REFERENCES product_components(id),
    applies_to_price_table_id  INTEGER REFERENCES price_tables(id),
    source_imported_page_id    INTEGER REFERENCES imported_pages(id),
    created_at                 TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Extensão 1:1 de component_variants para itens vendidos como acessório
-- (ex.: conectores STAFF — pág. 435). Em vez de duplicar o fluxo
-- comercial (SKU/preço) para acessórios, a variação em si continua
-- fluindo por component_variants/skus/prices; esta tabela apenas agrega
-- metadados de compatibilidade que não fazem sentido para um componente
-- estrutural comum (ex.: "este conector é compatível com tampos Bi-Partido").
CREATE TABLE accessories (
    id                            INTEGER PRIMARY KEY AUTOINCREMENT,
    component_variant_id          INTEGER NOT NULL UNIQUE REFERENCES component_variants(id),
    compatible_with_product_id    INTEGER REFERENCES products(id),
    compatible_with_component_id  INTEGER REFERENCES product_components(id),
    notes                         TEXT
);

-- ===========================================================================
-- 3. ORÇAMENTOS
--    Monta orçamentos por composição de componentes, com preço CONGELADO
--    no momento da inclusão — preservando o valor mesmo que a tabela de
--    preço de catálogo seja atualizada depois.
-- ===========================================================================

CREATE TABLE quotes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    quote_number        TEXT UNIQUE,
    customer_id         INTEGER REFERENCES customers(id),
    price_table_id      INTEGER NOT NULL REFERENCES price_tables(id),  -- versão-base usada na montagem
    created_by_user_id  INTEGER REFERENCES users(id),
    status              TEXT NOT NULL DEFAULT 'rascunho'
                            CHECK (status IN ('rascunho', 'enviado', 'aprovado', 'rejeitado', 'expirado')),
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    valid_until         TEXT,
    notes               TEXT
);

-- Linha "lógica" do orçamento — o que o cliente vê (ex.: "Mesa de Reunião
-- 1200x900 — Carvalho"). Pode agregar 1+ componentes físicos via
-- quote_item_components: um "item fechado" (ex.: mesa redonda vendida
-- como unidade) é um quote_item com 1 componente; um item "por composição"
-- (tampo + estrutura + apoio) é um quote_item com N componentes. O modelo
-- não obriga a decidir agora entre os dois modos (pergunta em aberto na
-- auditoria) — ambos cabem sem alteração de schema.
CREATE TABLE quote_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    quote_id    INTEGER NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
    product_id  INTEGER REFERENCES products(id),
    label       TEXT NOT NULL,
    quantity    INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    notes       TEXT
);

-- Cada componente físico que compõe uma linha do orçamento. O preço é
-- COPIADO de "prices" no momento da inclusão (frozen_unit_price/
-- frozen_currency) — é esse valor, e não o de catálogo, que vale para o
-- orçamento dali em diante. price_source_id mantém o rastro até o preço
-- de catálogo de origem só para fins de auditoria; ON DELETE SET NULL
-- garante que o valor congelado sobrevive mesmo que o registro de
-- catálogo seja removido/substituído por uma nova versão de tabela.
CREATE TABLE quote_item_components (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    quote_item_id         INTEGER NOT NULL REFERENCES quote_items(id) ON DELETE CASCADE,
    component_variant_id  INTEGER NOT NULL REFERENCES component_variants(id),
    sku_id                INTEGER NOT NULL REFERENCES skus(id),
    quantity              INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    frozen_unit_price     NUMERIC NOT NULL CHECK (frozen_unit_price >= 0),
    frozen_currency       TEXT NOT NULL DEFAULT 'BRL',
    price_source_id       INTEGER REFERENCES prices(id) ON DELETE SET NULL,
    frozen_at             TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Totais também "congelados" — um snapshot calculado e armazenado no
-- momento do fechamento/emissão, para que o valor exibido/impresso não
-- mude silenciosamente caso a fórmula de cálculo (ex.: regra de imposto)
-- evolua depois. Pode ser recalculado a qualquer momento a partir de
-- quote_item_components para fins de conferência (ver consulta 4).
CREATE TABLE quote_totals (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    quote_id          INTEGER NOT NULL UNIQUE REFERENCES quotes(id) ON DELETE CASCADE,
    subtotal          NUMERIC NOT NULL,
    discount_percent  NUMERIC NOT NULL DEFAULT 0,
    discount_amount   NUMERIC NOT NULL DEFAULT 0,
    tax_amount        NUMERIC NOT NULL DEFAULT 0,
    freight_amount    NUMERIC NOT NULL DEFAULT 0,
    total             NUMERIC NOT NULL,
    currency          TEXT NOT NULL DEFAULT 'BRL',
    calculated_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ===========================================================================
-- 4. ÍNDICES RECOMENDADOS
--    Cobrem (a) FKs usadas em joins frequentes e (b) colunas usadas em
--    filtros de consulta recorrentes (status, nível de confiança, dimensão).
--    Ver "Índices recomendados" no documento para o raciocínio completo.
-- ===========================================================================

-- Camada de importação
CREATE INDEX idx_imported_pages_file        ON imported_pages(imported_file_id);
CREATE INDEX idx_extracted_rows_page        ON extracted_rows(imported_page_id);
CREATE INDEX idx_extracted_items_page       ON extracted_items(imported_page_id);
CREATE INDEX idx_extracted_items_confidence ON extracted_items(confidence_level);
CREATE INDEX idx_extracted_items_review     ON extracted_items(review_status);
CREATE INDEX idx_item_source_rows_row       ON extracted_item_source_rows(extracted_row_id);
CREATE INDEX idx_import_warnings_file       ON import_warnings(imported_file_id);
CREATE INDEX idx_import_warnings_page       ON import_warnings(imported_page_id);
CREATE INDEX idx_import_warnings_item       ON import_warnings(extracted_item_id);
CREATE INDEX idx_review_decisions_item      ON import_review_decisions(extracted_item_id);

-- Catálogo normalizado
CREATE INDEX idx_products_family            ON products(family_id);
CREATE INDEX idx_dimensions_wd              ON dimensions(width_mm, depth_mm);
CREATE INDEX idx_dimensions_diameter        ON dimensions(diameter_mm);
CREATE INDEX idx_variants_product           ON component_variants(product_id);
CREATE INDEX idx_variants_component         ON component_variants(component_id);
CREATE INDEX idx_variants_dimension         ON component_variants(dimension_id);
CREATE INDEX idx_variants_finish            ON component_variants(finish_id);
CREATE INDEX idx_prices_variant             ON prices(component_variant_id);
CREATE INDEX idx_prices_sku                 ON prices(sku_id);
CREATE INDEX idx_prices_table               ON prices(price_table_id);
CREATE INDEX idx_prices_source_item         ON prices(source_extracted_item_id);
CREATE INDEX idx_business_rules_product     ON business_rules(applies_to_product_id);
CREATE INDEX idx_business_rules_component   ON business_rules(applies_to_component_id);

-- Orçamentos
CREATE INDEX idx_quotes_customer            ON quotes(customer_id);
CREATE INDEX idx_quotes_price_table         ON quotes(price_table_id);
CREATE INDEX idx_quotes_status              ON quotes(status);
CREATE INDEX idx_quote_items_quote          ON quote_items(quote_id);
CREATE INDEX idx_quote_items_product        ON quote_items(product_id);
CREATE INDEX idx_quote_item_components_item ON quote_item_components(quote_item_id);
CREATE INDEX idx_quote_item_components_var  ON quote_item_components(component_variant_id);
CREATE INDEX idx_quote_item_components_sku  ON quote_item_components(sku_id);
CREATE INDEX idx_quote_item_components_src  ON quote_item_components(price_source_id);
