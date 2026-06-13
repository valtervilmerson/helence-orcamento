-- ===========================================================================
-- Fase 9 — RN-05 (camada 1) e RN-07 (composição mínima por família)
-- ===========================================================================
--
-- RN-05: o seletor de acabamento deve mostrar apenas finish_groups
-- compatíveis com o tipo de componente selecionado (ex.: nunca oferecer
-- "Carvalho" — madeirado — para uma Estrutura). NULL = sem restrição
-- conhecida.
ALTER TABLE product_components
    ADD COLUMN finish_group TEXT
    CHECK (finish_group IN ('madeirado', 'metalico', 'pe_estrutura', 'outro'));

-- RN-07: matriz obrigatório/opcional por família × tipo de componente —
-- dado de configuração revisável (mesmo espírito de
-- component_compatibility_rules / RN-04, migration 0005). Ausência de
-- registro para um par família/componente significa "sem exigência
-- conhecida" (opcional por padrão).
CREATE TABLE family_component_requirements (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    family_id    INTEGER NOT NULL REFERENCES product_families(id),
    component_id INTEGER NOT NULL REFERENCES product_components(id),
    requirement  TEXT NOT NULL CHECK (requirement IN ('obrigatorio', 'opcional')),
    UNIQUE (family_id, component_id)
);

CREATE INDEX idx_family_component_requirements_family
    ON family_component_requirements(family_id);

-- RN-07: justificativa do vendedor para uma linha incompleta (sem
-- componente(s) obrigatório(s)) — registrar isso libera a transição
-- rascunho -> enviado sem o(s) componente(s) faltante(s).
ALTER TABLE quote_items ADD COLUMN composition_justification TEXT;
