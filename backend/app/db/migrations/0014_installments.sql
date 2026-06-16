-- Parcelamento por orçamento: número de parcelas e taxa de juros.
--
-- quotes: configuração do parcelamento escolhido pelo vendedor.
-- quote_totals: snapshot dos valores calculados no momento do congelamento.

ALTER TABLE quotes ADD COLUMN installment_count    INTEGER NOT NULL DEFAULT 1;
ALTER TABLE quotes ADD COLUMN installment_interest_percent REAL NOT NULL DEFAULT 0;

ALTER TABLE quote_totals ADD COLUMN installment_count             INTEGER NOT NULL DEFAULT 1;
ALTER TABLE quote_totals ADD COLUMN installment_interest_percent  REAL    NOT NULL DEFAULT 0;
ALTER TABLE quote_totals ADD COLUMN installment_interest_amount   REAL    NOT NULL DEFAULT 0;
ALTER TABLE quote_totals ADD COLUMN installment_total             REAL    NOT NULL DEFAULT 0;
ALTER TABLE quote_totals ADD COLUMN installment_value             REAL    NOT NULL DEFAULT 0;
