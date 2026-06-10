-- ===========================================================================
-- Fase 4 — status do ciclo de importação (docs/06, seções 14.1/14.2)
-- ===========================================================================

ALTER TABLE imported_files ADD COLUMN status TEXT NOT NULL DEFAULT 'recebido'
    CHECK (status IN ('recebido', 'processando', 'concluido', 'erro'));
