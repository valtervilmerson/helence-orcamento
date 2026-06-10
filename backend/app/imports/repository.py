"""Acesso a dados de importações (docs/06, seções 14.1/14.2)."""

from __future__ import annotations

import sqlite3

_IMPORT_BASE = """
    SELECT
        f.*,
        u.id AS imported_by_id,
        u.name AS imported_by_name
    FROM imported_files f
    LEFT JOIN users u ON u.id = f.imported_by_user_id
"""


def find_by_hash(connection: sqlite3.Connection, file_hash: str) -> sqlite3.Row | None:
    return connection.execute(
        _IMPORT_BASE + " WHERE f.file_hash = ?", (file_hash,)
    ).fetchone()


def insert_imported_file(
    connection: sqlite3.Connection,
    *,
    file_path: str,
    file_hash: str,
    original_filename: str | None,
    notes: str | None,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO imported_files (file_path, file_hash, original_filename, status, notes)
        VALUES (?, ?, ?, 'recebido', ?)
        """,
        (file_path, file_hash, original_filename, notes),
    )
    connection.commit()
    return int(cursor.lastrowid)


def get_imported_file(connection: sqlite3.Connection, import_id: int) -> sqlite3.Row | None:
    return connection.execute(_IMPORT_BASE + " WHERE f.id = ?", (import_id,)).fetchone()


def list_imported_files(
    connection: sqlite3.Connection,
    *,
    status: str | None,
    page: int,
    page_size: int,
) -> tuple[list[sqlite3.Row], int]:
    where = ""
    params: list[str] = []
    if status is not None:
        where = "WHERE f.status = ?"
        params.append(status)

    total = connection.execute(
        f"SELECT COUNT(*) AS c FROM imported_files f {where}", params
    ).fetchone()["c"]

    offset = (page - 1) * page_size
    rows = connection.execute(
        f"""
        {_IMPORT_BASE}
        {where}
        ORDER BY f.imported_at DESC, f.id DESC
        LIMIT ? OFFSET ?
        """,
        [*params, page_size, offset],
    ).fetchall()
    return rows, total


def count_extracted_items(connection: sqlite3.Connection, import_id: int) -> int:
    return connection.execute(
        """
        SELECT COUNT(*) AS c
        FROM extracted_items ei
        JOIN imported_pages p ON p.id = ei.imported_page_id
        WHERE p.imported_file_id = ?
        """,
        (import_id,),
    ).fetchone()["c"]


def count_pending_review_items(connection: sqlite3.Connection, import_id: int) -> int:
    return connection.execute(
        """
        SELECT COUNT(*) AS c
        FROM extracted_items ei
        JOIN imported_pages p ON p.id = ei.imported_page_id
        WHERE p.imported_file_id = ? AND ei.review_status = 'pendente'
        """,
        (import_id,),
    ).fetchone()["c"]


def get_linked_price_table(connection: sqlite3.Connection, import_id: int) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT id, code, status FROM price_tables WHERE source_imported_file_id = ?",
        (import_id,),
    ).fetchone()
