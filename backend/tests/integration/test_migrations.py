import sqlite3

import pytest

from app.db.migrate import apply_migrations

KEY_TABLES = ["imported_files", "component_variants", "quotes"]


@pytest.fixture
def connection(tmp_path):
    conn = sqlite3.connect(tmp_path / "test.db")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row["name"] for row in rows}


def test_migrations_create_key_tables(connection) -> None:
    apply_migrations(connection)

    tables = _table_names(connection)

    for table in KEY_TABLES:
        assert table in tables


def test_migrations_are_idempotent(connection) -> None:
    first = apply_migrations(connection)
    second = apply_migrations(connection)

    assert first == [
        "0001_initial",
        "0002_quote_item_discounts",
        "0003_imported_files_status",
        "0004_import_processing",
        "0005_compatibility_rules",
        "0006_family_component_requirements",
        "0007_quote_duplication",
    ]
    assert second == []

    versions = connection.execute("SELECT version FROM schema_migrations").fetchall()
    assert [row["version"] for row in versions] == [
        "0001_initial",
        "0002_quote_item_discounts",
        "0003_imported_files_status",
        "0004_import_processing",
        "0005_compatibility_rules",
        "0006_family_component_requirements",
        "0007_quote_duplication",
    ]


def test_foreign_key_chain_is_enforced(connection) -> None:
    apply_migrations(connection)

    connection.execute("INSERT INTO product_families (name) VALUES ('Mesas de Reunião')")
    family_id = connection.execute(
        "SELECT id FROM product_families WHERE name = 'Mesas de Reunião'"
    ).fetchone()["id"]

    connection.execute(
        "INSERT INTO products (family_id, name) VALUES (?, 'Reunião 1200x900')",
        (family_id,),
    )
    connection.commit()

    product = connection.execute(
        "SELECT id FROM products WHERE name = 'Reunião 1200x900'"
    ).fetchone()
    assert product is not None

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO products (family_id, name) VALUES (?, 'Família inexistente')",
            (9999,),
        )
