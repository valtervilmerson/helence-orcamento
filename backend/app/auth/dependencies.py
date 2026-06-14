"""Dependências FastAPI de autenticação e autorização por papel."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable

from fastapi import Depends, Request

from app.auth import repository
from app.auth.security import verify_session_token
from app.db.connection import get_connection
from app.shared.errors import NaoAutenticadoError, PermissaoNegadaError

SESSION_COOKIE_NAME = "session"


def get_current_user(request: Request) -> sqlite3.Row:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user_id = verify_session_token(token) if token else None
    if user_id is None:
        raise NaoAutenticadoError()

    with get_connection() as connection:
        user = repository.get_user_by_id(connection, user_id)
    if user is None:
        raise NaoAutenticadoError()

    return user


def require_role(*roles: str) -> Callable[[sqlite3.Row], sqlite3.Row]:
    def dependency(user: sqlite3.Row = Depends(get_current_user)) -> sqlite3.Row:
        if user["role"] not in roles:
            raise PermissaoNegadaError()
        return user

    return dependency
