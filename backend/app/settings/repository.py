"""Acesso a dados das configurações globais da aplicação."""

from __future__ import annotations

import sqlite3


def get_setting(connection: sqlite3.Connection, key: str, default: str = "0") -> str:
    row = connection.execute(
        "SELECT value FROM app_settings WHERE key = ?", (key,)
    ).fetchone()
    return row["value"] if row else default


def set_setting(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        """
        INSERT INTO app_settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )
    connection.commit()


def get_global_markup(connection: sqlite3.Connection) -> float:
    return float(get_setting(connection, "global_markup_percent", "0"))


def set_global_markup(connection: sqlite3.Connection, value: float) -> None:
    set_setting(connection, "global_markup_percent", str(value))


def get_discount_limit_percent(connection: sqlite3.Connection) -> float:
    return float(get_setting(connection, "discount_limit_percent", "8"))


def get_default_validity_days(connection: sqlite3.Connection) -> int:
    return int(float(get_setting(connection, "default_validity_days", "30")))
