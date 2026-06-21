-- ===========================================================================
-- Acabamento pode pertencer a mais de um grupo de compatibilidade (RN-05)
-- ===========================================================================
--
-- Nomes de acabamento são compartilhados entre tipos de componente muito
-- diferentes (ex.: "Preto"/"Branco" aparecem tanto como cor de Tampo —
-- grupo madeirado — quanto como cor de Estrutura — grupo metálico). A coluna
-- única `finishes.finish_group` só permitia um grupo por nome, escondendo o
-- acabamento do seletor compatível sempre que o grupo "errado" estivesse
-- selecionado. Substituída por uma tabela N:N.

CREATE TABLE finish_groups (
    finish_id     INTEGER NOT NULL REFERENCES finishes(id) ON DELETE CASCADE,
    finish_group  TEXT NOT NULL
                      CHECK (finish_group IN ('madeirado', 'metalico', 'pe_estrutura', 'outro')),
    PRIMARY KEY (finish_id, finish_group)
);

INSERT INTO finish_groups (finish_id, finish_group)
SELECT id, finish_group FROM finishes WHERE finish_group IS NOT NULL;

ALTER TABLE finishes DROP COLUMN finish_group;
