CREATE TABLE IF NOT EXISTS component_variant_change_log (
    id INTEGER PRIMARY KEY,
    component_variant_id INTEGER NOT NULL REFERENCES component_variants(id) ON DELETE CASCADE,
    changed_by_user_id INTEGER NOT NULL REFERENCES users(id),
    reason TEXT NOT NULL,
    previous_data TEXT NOT NULL,
    new_data TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_component_variant_change_log_variant
    ON component_variant_change_log(component_variant_id, created_at DESC);
