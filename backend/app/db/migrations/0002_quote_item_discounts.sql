-- ===========================================================================
-- Fase 3 — desconto por linha de orçamento (docs/06, seção 14.12; RN-09)
-- ===========================================================================

ALTER TABLE quote_items ADD COLUMN discount_percent NUMERIC;
ALTER TABLE quote_items ADD COLUMN discount_amount NUMERIC;
ALTER TABLE quote_items ADD COLUMN discount_reason TEXT;
