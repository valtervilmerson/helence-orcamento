"""Seed mínimo de dados de referência (docs/07, Fase 1).

Cria um usuário de teste por papel e uma ``price_table`` vazia em
status ``vigente``, evitando o erro ``NENHUMA_TABELA_VIGENTE`` ao
montar orçamentos (Fase 3). Idempotente: rodar mais de uma vez não
duplica registros.

Mapeamento de papéis (docs/04, seção "Papéis"): a coluna ``users.role``
só aceita ``admin | importador | revisor | vendedor | colaborador``
(docs/schema/schema.sql). "Aprovador" é o papel ``admin``; "Auditor" —
que pode ser o próprio Admin — é semeado com o papel ``colaborador``
para ter um usuário de teste dedicado sem conflitar com o Admin/
Aprovador.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.config import get_settings
from app.db.connection import get_connection
from app.db.migrate import apply_migrations

SEED_USERS = [
    ("Importador Teste", "importador@helence.local", "importador"),
    ("Revisor Teste", "revisor@helence.local", "revisor"),
    ("Aprovador Teste", "aprovador@helence.local", "admin"),
    ("Vendedor Teste", "vendedor@helence.local", "vendedor"),
    ("Auditor Teste", "auditor@helence.local", "colaborador"),
]

SEED_PRICE_TABLE_CODE = "SEED-VAZIA"


def seed(connection: sqlite3.Connection) -> None:
    for name, email, role in SEED_USERS:
        connection.execute(
            "INSERT OR IGNORE INTO users (name, email, role) VALUES (?, ?, ?)",
            (name, email, role),
        )

    connection.execute(
        """
        INSERT OR IGNORE INTO price_tables (code, name, status)
        VALUES (?, 'Tabela seed (vazia)', 'vigente')
        """,
        (SEED_PRICE_TABLE_CODE,),
    )

    connection.commit()


def main() -> None:
    settings = get_settings()
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as connection:
        apply_migrations(connection)
        seed(connection)

    print("Seed aplicado.")


if __name__ == "__main__":
    main()
