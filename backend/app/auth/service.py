"""Regras de autenticação (login por e-mail/senha)."""

from __future__ import annotations

import sqlite3

from app.auth import repository
from app.auth.security import verify_password
from app.shared.errors import CredenciaisInvalidasError


def authenticate(connection: sqlite3.Connection, email: str, password: str) -> sqlite3.Row:
    user = repository.get_user_by_email(connection, email)
    password_hash = user["password_hash"] if user is not None else None
    if not password_hash or not verify_password(password, password_hash):
        raise CredenciaisInvalidasError()
    return user
