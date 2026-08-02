"""Acesso a dados de usuários para autenticação."""

from __future__ import annotations

import sqlite3


def get_user_by_email(connection: sqlite3.Connection, email: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT id, name, email, role, password_hash FROM users WHERE email = ?", (email,)
    ).fetchone()


def get_user_by_id(connection: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT id, name, email, role FROM users WHERE id = ?", (user_id,)
    ).fetchone()


def list_users(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return connection.execute(
        "SELECT id, name, email, role FROM users ORDER BY CASE role WHEN 'admin' THEN 0 ELSE 1 END, name"
    ).fetchall()
