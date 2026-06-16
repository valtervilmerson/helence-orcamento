-- Configurações globais da aplicação e override de markup por orçamento.
--
-- app_settings: pares chave/valor para configurações globais (ex: markup padrão).
-- quotes.markup_uses_global: quando TRUE (padrão), o orçamento herda o markup
-- global em tempo de cálculo. Quando FALSE, usa quotes.markup_percent diretamente.

CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO app_settings (key, value) VALUES ('global_markup_percent', '0');

ALTER TABLE quotes ADD COLUMN markup_uses_global BOOLEAN NOT NULL DEFAULT 1;

-- Orçamentos que já tinham markup_percent != 0 ficam como override.
UPDATE quotes SET markup_uses_global = 0 WHERE markup_percent != 0;
