"""Conexão SQLite com PRAGMA foreign_keys=ON ativado a cada conexão.

A pragma não é persistida pelo SQLite (docs/03, nota da seção 3) — por
isso é configurada aqui, no único ponto de abertura de conexão usado
pela aplicação.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from app.config import get_settings


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    settings = get_settings()
    connection = sqlite3.connect(settings.database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()
