-- ===========================================================================
-- Migration 0009 — preço único por item, sem tabelas de preço/vigência
-- ===========================================================================
--
-- Elimina o conceito de "tabela de preços" (price_tables) e de "vigência".
-- Cada component_variant passa a ter no máximo um preço (prices,
-- UNIQUE(component_variant_id)). component_variants ganha family_id, que
-- passa a ser a fonte de verdade da "linha de produto" do item,
-- independente de product_id (agora opcional — itens avulsos sem
-- produto-base). SKU passa a ser opcional em prices e
-- quote_item_components.
--
-- SQLite não permite remover colunas/constraints UNIQUE via ALTER TABLE,
-- então as tabelas afetadas são recriadas: CREATE nova tabela ->
-- INSERT ... SELECT -> DROP -> RENAME -> recriar índices.

PRAGMA foreign_keys = OFF;

-- ---------------------------------------------------------------------
-- 1. component_variants: + family_id, novo UNIQUE incluindo family_id
-- ---------------------------------------------------------------------
CREATE TABLE component_variants_new (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id    INTEGER REFERENCES products(id),
    family_id     INTEGER REFERENCES product_families(id),
    component_id  INTEGER NOT NULL REFERENCES product_components(id),
    dimension_id  INTEGER REFERENCES dimensions(id),
    finish_id     INTEGER REFERENCES finishes(id),
    descriptor    TEXT,
    description   TEXT,
    UNIQUE (family_id, product_id, component_id, dimension_id, finish_id, descriptor)
);

INSERT INTO component_variants_new
    (id, product_id, family_id, component_id, dimension_id, finish_id, descriptor, description)
SELECT
    cv.id,
    cv.product_id,
    (SELECT p.family_id FROM products p WHERE p.id = cv.product_id),
    cv.component_id,
    cv.dimension_id,
    cv.finish_id,
    cv.descriptor,
    cv.description
FROM component_variants cv;

DROP TABLE component_variants;
ALTER TABLE component_variants_new RENAME TO component_variants;

CREATE INDEX idx_variants_product   ON component_variants(product_id);
CREATE INDEX idx_variants_family    ON component_variants(family_id);
CREATE INDEX idx_variants_component ON component_variants(component_id);
CREATE INDEX idx_variants_dimension ON component_variants(dimension_id);
CREATE INDEX idx_variants_finish    ON component_variants(finish_id);

-- ---------------------------------------------------------------------
-- 2. prices: sem price_table_id, sku_id opcional, 1 preço por variação
-- ---------------------------------------------------------------------
CREATE TABLE prices_new (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    component_variant_id     INTEGER NOT NULL REFERENCES component_variants(id),
    sku_id                    INTEGER REFERENCES skus(id),
    amount                    NUMERIC NOT NULL CHECK (amount >= 0),
    currency                  TEXT NOT NULL DEFAULT 'BRL',
    source_extracted_item_id  INTEGER REFERENCES extracted_items(id),
    created_at                TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (component_variant_id)
);

-- Para variações com múltiplas linhas históricas em prices (uma por
-- price_table_id), mantém apenas uma: preferindo a que pertencia a uma
-- tabela 'vigente', senão a de maior id (mais recente).
INSERT INTO prices_new
    (id, component_variant_id, sku_id, amount, currency, source_extracted_item_id, created_at)
SELECT p.id, p.component_variant_id, p.sku_id, p.amount, p.currency, p.source_extracted_item_id, p.created_at
FROM prices p
WHERE p.id = (
    SELECT p2.id
    FROM prices p2
    LEFT JOIN price_tables pt2 ON pt2.id = p2.price_table_id
    WHERE p2.component_variant_id = p.component_variant_id
    ORDER BY (CASE WHEN pt2.status = 'vigente' THEN 1 ELSE 0 END) DESC, p2.id DESC
    LIMIT 1
);

DROP TABLE prices;
ALTER TABLE prices_new RENAME TO prices;

CREATE INDEX idx_prices_variant     ON prices(component_variant_id);
CREATE INDEX idx_prices_sku         ON prices(sku_id);
CREATE INDEX idx_prices_source_item ON prices(source_extracted_item_id);

-- ---------------------------------------------------------------------
-- 3. quote_item_components: sku_id opcional, limpa price_source_id órfão
-- ---------------------------------------------------------------------
CREATE TABLE quote_item_components_new (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    quote_item_id         INTEGER NOT NULL REFERENCES quote_items(id) ON DELETE CASCADE,
    component_variant_id  INTEGER NOT NULL REFERENCES component_variants(id),
    sku_id                INTEGER REFERENCES skus(id),
    quantity              INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    frozen_unit_price     NUMERIC NOT NULL CHECK (frozen_unit_price >= 0),
    frozen_currency       TEXT NOT NULL DEFAULT 'BRL',
    price_source_id       INTEGER REFERENCES prices(id) ON DELETE SET NULL,
    frozen_at             TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT INTO quote_item_components_new
    (id, quote_item_id, component_variant_id, sku_id, quantity, frozen_unit_price, frozen_currency, price_source_id, frozen_at)
SELECT
    qic.id,
    qic.quote_item_id,
    qic.component_variant_id,
    qic.sku_id,
    qic.quantity,
    qic.frozen_unit_price,
    qic.frozen_currency,
    CASE WHEN qic.price_source_id IN (SELECT id FROM prices) THEN qic.price_source_id ELSE NULL END,
    qic.frozen_at
FROM quote_item_components qic;

DROP TABLE quote_item_components;
ALTER TABLE quote_item_components_new RENAME TO quote_item_components;

CREATE INDEX idx_quote_item_components_item ON quote_item_components(quote_item_id);
CREATE INDEX idx_quote_item_components_var  ON quote_item_components(component_variant_id);
CREATE INDEX idx_quote_item_components_sku  ON quote_item_components(sku_id);
CREATE INDEX idx_quote_item_components_src  ON quote_item_components(price_source_id);

-- ---------------------------------------------------------------------
-- 4. quotes: remove price_table_id
-- ---------------------------------------------------------------------
CREATE TABLE quotes_new (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    quote_number        TEXT UNIQUE,
    customer_id         INTEGER REFERENCES customers(id),
    created_by_user_id  INTEGER REFERENCES users(id),
    status              TEXT NOT NULL DEFAULT 'rascunho'
                            CHECK (status IN ('rascunho', 'enviado', 'aprovado', 'rejeitado', 'expirado')),
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    valid_until         TEXT,
    notes               TEXT,
    source_quote_id     INTEGER REFERENCES quotes(id)
);

INSERT INTO quotes_new
    (id, quote_number, customer_id, created_by_user_id, status, created_at, valid_until, notes, source_quote_id)
SELECT id, quote_number, customer_id, created_by_user_id, status, created_at, valid_until, notes, source_quote_id
FROM quotes;

DROP TABLE quotes;
ALTER TABLE quotes_new RENAME TO quotes;

CREATE INDEX idx_quotes_customer ON quotes(customer_id);
CREATE INDEX idx_quotes_status   ON quotes(status);

-- ---------------------------------------------------------------------
-- 5. business_rules: remove applies_to_price_table_id
-- ---------------------------------------------------------------------
CREATE TABLE business_rules_new (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_text                TEXT NOT NULL,
    applies_to_product_id    INTEGER REFERENCES products(id),
    applies_to_component_id  INTEGER REFERENCES product_components(id),
    source_imported_page_id  INTEGER REFERENCES imported_pages(id),
    created_at               TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT INTO business_rules_new
    (id, rule_text, applies_to_product_id, applies_to_component_id, source_imported_page_id, created_at)
SELECT id, rule_text, applies_to_product_id, applies_to_component_id, source_imported_page_id, created_at
FROM business_rules;

DROP TABLE business_rules;
ALTER TABLE business_rules_new RENAME TO business_rules;

CREATE INDEX idx_business_rules_product   ON business_rules(applies_to_product_id);
CREATE INDEX idx_business_rules_component ON business_rules(applies_to_component_id);

-- ---------------------------------------------------------------------
-- 6. price_tables: não há mais referências — remover
-- ---------------------------------------------------------------------
DROP TABLE price_tables;

PRAGMA foreign_keys = ON;
