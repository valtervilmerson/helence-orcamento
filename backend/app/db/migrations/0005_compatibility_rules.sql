-- ===========================================================================
-- Fase 9 — regras de compatibilidade entre componentes (docs/05, RN-04)
-- ===========================================================================
--
-- RN-04: o descritor de um componente (ex.: Tampo "Inteiro") determina qual
-- descritor de outro componente (ex.: Estrutura "Reunião Tampo Inteiro") é
-- compatível. Como o catálogo de origem não declara essa relação de forma
-- estruturada, ela é modelada como dado de configuração revisável pela área
-- comercial (docs/05), em vez de comparação de texto no código.
--
-- Ausência de regra para um par de tipos de componente significa "sem
-- restrição conhecida ainda" (compatível por padrão). Quando existir pelo
-- menos uma regra para o par, a combinação de descritores precisa
-- corresponder a uma delas.

CREATE TABLE component_compatibility_rules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    component_a_id INTEGER NOT NULL REFERENCES product_components(id),
    descriptor_a    TEXT NOT NULL,
    component_b_id INTEGER NOT NULL REFERENCES product_components(id),
    descriptor_b    TEXT NOT NULL,
    notes           TEXT,
    UNIQUE (component_a_id, descriptor_a, component_b_id, descriptor_b)
);

CREATE INDEX idx_compat_rules_a ON component_compatibility_rules(component_a_id, descriptor_a);
CREATE INDEX idx_compat_rules_b ON component_compatibility_rules(component_b_id, descriptor_b);
