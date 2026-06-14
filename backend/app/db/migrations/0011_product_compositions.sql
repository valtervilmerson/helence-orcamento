-- ===========================================================================
-- Migration 0011 — renomeia "kits" para "composição de produto"
-- ===========================================================================
--
-- O termo "kit" colidia com produtos reais do catálogo ("Kit de Montagem X").
-- A tabela product_kit_items passa a se chamar product_compositions, mantendo
-- as mesmas colunas e constraints.

ALTER TABLE product_kit_items RENAME TO product_compositions;

DROP INDEX IF EXISTS idx_product_kit_items_product;
DROP INDEX IF EXISTS idx_product_kit_items_variant;

CREATE INDEX idx_product_compositions_product ON product_compositions(product_id);
CREATE INDEX idx_product_compositions_variant ON product_compositions(component_variant_id);
