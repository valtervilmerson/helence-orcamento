import sqlite3

import pytest

from app.db.migrate import apply_migrations
from app.db.seed import SEED_USERS, seed


@pytest.fixture
def connection(tmp_path):
    conn = sqlite3.connect(tmp_path / "test.db")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    apply_migrations(conn)
    try:
        yield conn
    finally:
        conn.close()


def test_seed_creates_one_user_per_role(connection) -> None:
    seed(connection)

    rows = connection.execute("SELECT email, role FROM users").fetchall()
    roles = {row["role"] for row in rows}

    assert len(rows) == len(SEED_USERS)
    assert roles == {role for _, _, role in SEED_USERS}


def test_seed_is_idempotent(connection) -> None:
    seed(connection)
    seed(connection)

    user_count = connection.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
    price_count = connection.execute("SELECT COUNT(*) AS n FROM prices").fetchone()["n"]

    assert user_count == len(SEED_USERS)
    assert price_count > 0
