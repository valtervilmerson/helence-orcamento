-- ===========================================================================
-- Migration 0010 — produtos compostos (kits) pré-cadastrados
-- ===========================================================================
--
-- Permite definir que um `products` (ex.: "Mesa de Reunião 1") é composto por
-- variações específicas (ex.: Tampo X + Estrutura Y). Ao adicionar esse
-- produto a um orçamento, a UI pode pré-popular os componentes — sem impedir
-- adicionar peças avulsas separadamente.

CREATE TABLE product_kit_items (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id            INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    component_variant_id  INTEGER NOT NULL REFERENCES component_variants(id),
    quantity              INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    UNIQUE (product_id, component_variant_id)
);

CREATE INDEX idx_product_kit_items_product ON product_kit_items(product_id);
CREATE INDEX idx_product_kit_items_variant ON product_kit_items(component_variant_id);
