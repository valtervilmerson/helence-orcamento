-- ===========================================================================
-- Fase 9 — RN-17 (duplicação de orçamento)
-- ===========================================================================
--
-- Rastreabilidade: o orçamento duplicado mantém referência ao orçamento de
-- origem (para contexto do vendedor e auditoria).
ALTER TABLE quotes ADD COLUMN source_quote_id INTEGER REFERENCES quotes(id);

-- Pendências de reprecificação detectadas na duplicação (lista de mensagens
-- em JSON) — persistidas para reaparecer em consultas futuras do item.
ALTER TABLE quote_items ADD COLUMN duplication_pendencias TEXT;
