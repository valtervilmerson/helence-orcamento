"""Executor de migrations (docs/06, seção 10).

Lê os scripts numerados em ``app/db/migrations/*.sql``, compara com a
tabela de controle ``schema_migrations`` e aplica os que faltam, em
ordem, dentro de uma transação por migration. Idempotente: rodar duas
vezes seguidas não falha nem reaplica nada.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.config import get_settings
from app.db.connection import get_connection

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def _ensure_schema_migrations_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version     TEXT PRIMARY KEY,
            applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    connection.commit()


def _applied_versions(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute("SELECT version FROM schema_migrations").fetchall()
    return {row["version"] for row in rows}


def _migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def apply_migrations(connection: sqlite3.Connection) -> list[str]:
    """Aplica as migrations pendentes em ordem. Retorna as versões aplicadas."""
    _ensure_schema_migrations_table(connection)
    applied = _applied_versions(connection)

    newly_applied = []
    for path in _migration_files():
        version = path.stem
        if version in applied:
            continue

        sql = path.read_text(encoding="utf-8")
        connection.executescript(sql)
        connection.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
        connection.commit()
        newly_applied.append(version)

    return newly_applied


def main() -> None:
    settings = get_settings()
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as connection:
        applied = apply_migrations(connection)

    if applied:
        print(f"Migrations aplicadas: {', '.join(applied)}")
    else:
        print("Nenhuma migration pendente.")


if __name__ == "__main__":
    main()
