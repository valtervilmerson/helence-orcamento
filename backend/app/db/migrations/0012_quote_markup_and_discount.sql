-- ===========================================================================
-- Migration 0012 — margem de venda e desconto global do orçamento
-- ===========================================================================

-- Campos na tabela de orçamento:
--   markup_percent     — margem interna (não exibida no PDF ao cliente)
--   quote_discount_*   — desconto no total do orçamento (% OU valor fixo)
ALTER TABLE quotes ADD COLUMN markup_percent        NUMERIC NOT NULL DEFAULT 0;
ALTER TABLE quotes ADD COLUMN quote_discount_percent NUMERIC;
ALTER TABLE quotes ADD COLUMN quote_discount_amount  NUMERIC;
ALTER TABLE quotes ADD COLUMN quote_discount_reason  TEXT;

-- Campos no snapshot de totais: guarda os dois níveis de desconto
-- separados para o PDF poder exibi-los corretamente.
ALTER TABLE quote_totals ADD COLUMN item_discount_amount  NUMERIC NOT NULL DEFAULT 0;
ALTER TABLE quote_totals ADD COLUMN quote_discount_amount NUMERIC NOT NULL DEFAULT 0;
