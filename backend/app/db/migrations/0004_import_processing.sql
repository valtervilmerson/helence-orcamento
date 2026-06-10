-- ===========================================================================
-- Fase 5 — progresso/erro do processamento assíncrono (docs/06, 14.3/14.4)
-- ===========================================================================

ALTER TABLE imported_files ADD COLUMN pages_total INTEGER;
ALTER TABLE imported_files ADD COLUMN pages_processed INTEGER;
ALTER TABLE imported_files ADD COLUMN processing_started_at TEXT;
ALTER TABLE imported_files ADD COLUMN processing_finished_at TEXT;
ALTER TABLE imported_files ADD COLUMN error_code TEXT;
ALTER TABLE imported_files ADD COLUMN error_message TEXT;
