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


# ---------------------------------------------------------------------------
# Processamento (docs/06, seções 14.3/14.4; docs/07, Fase 5)
# ---------------------------------------------------------------------------


def mark_processing_started(
    connection: sqlite3.Connection, import_id: int, started_at: str
) -> None:
    connection.execute(
        """
        UPDATE imported_files
        SET status = 'processando',
            processing_started_at = ?,
            processing_finished_at = NULL,
            error_code = NULL,
            error_message = NULL,
            pages_total = NULL,
            pages_processed = 0
        WHERE id = ?
        """,
        (started_at, import_id),
    )
    connection.commit()


def set_pages_total(connection: sqlite3.Connection, import_id: int, pages_total: int) -> None:
    connection.execute(
        "UPDATE imported_files SET pages_total = ? WHERE id = ?", (pages_total, import_id)
    )
    connection.commit()


def set_pages_processed(
    connection: sqlite3.Connection, import_id: int, pages_processed: int
) -> None:
    connection.execute(
        "UPDATE imported_files SET pages_processed = ? WHERE id = ?",
        (pages_processed, import_id),
    )
    connection.commit()


def mark_processing_finished(
    connection: sqlite3.Connection, import_id: int, *, finished_at: str, page_count: int
) -> None:
    connection.execute(
        """
        UPDATE imported_files
        SET status = 'concluido', processing_finished_at = ?, page_count = ?
        WHERE id = ?
        """,
        (finished_at, page_count, import_id),
    )
    connection.commit()


def mark_processing_error(
    connection: sqlite3.Connection,
    import_id: int,
    *,
    finished_at: str,
    error_code: str,
    error_message: str,
) -> None:
    connection.execute(
        """
        UPDATE imported_files
        SET status = 'erro', processing_finished_at = ?, error_code = ?, error_message = ?
        WHERE id = ?
        """,
        (finished_at, error_code, error_message, import_id),
    )
    connection.commit()


def insert_imported_page(
    connection: sqlite3.Connection,
    *,
    imported_file_id: int,
    page_number: int,
    page_profile: str | None,
    section: str | None,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO imported_pages (imported_file_id, page_number, page_profile, section)
        VALUES (?, ?, ?, ?)
        """,
        (imported_file_id, page_number, page_profile, section),
    )
    return int(cursor.lastrowid)


def insert_extracted_row(
    connection: sqlite3.Connection,
    *,
    imported_page_id: int,
    sequence_no: int,
    y_coordinate: float | None,
    raw_text: str,
    is_vertical_text: bool,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO extracted_rows
            (imported_page_id, sequence_no, y_coordinate, raw_text, is_vertical_text)
        VALUES (?, ?, ?, ?, ?)
        """,
        (imported_page_id, sequence_no, y_coordinate, raw_text, 1 if is_vertical_text else 0),
    )
    return int(cursor.lastrowid)


def insert_extracted_item(
    connection: sqlite3.Connection,
    *,
    imported_page_id: int,
    family_raw: str | None,
    product_context_raw: str | None,
    component_type_raw: str | None,
    description_raw: str | None,
    dimension_raw: str | None,
    finish_raw: str | None,
    sku_raw: str | None,
    price_raw: str | None,
    currency: str,
    confidence: float,
    confidence_level: str,
    source_text: str | None,
    extraction_notes: str | None,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO extracted_items (
            imported_page_id, family_raw, product_context_raw, component_type_raw,
            description_raw, dimension_raw, finish_raw, sku_raw, price_raw, currency,
            confidence, confidence_level, source_text, extraction_notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            imported_page_id,
            family_raw,
            product_context_raw,
            component_type_raw,
            description_raw,
            dimension_raw,
            finish_raw,
            sku_raw,
            price_raw,
            currency,
            confidence,
            confidence_level,
            source_text,
            extraction_notes,
        ),
    )
    return int(cursor.lastrowid)


def insert_import_warning(
    connection: sqlite3.Connection,
    *,
    imported_file_id: int,
    imported_page_id: int | None,
    severity: str,
    message: str,
    extracted_item_id: int | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO import_warnings
            (imported_file_id, imported_page_id, extracted_item_id, severity, message)
        VALUES (?, ?, ?, ?, ?)
        """,
        (imported_file_id, imported_page_id, extracted_item_id, severity, message),
    )


def count_warnings(connection: sqlite3.Connection, import_id: int) -> int:
    return connection.execute(
        "SELECT COUNT(*) AS c FROM import_warnings WHERE imported_file_id = ?",
        (import_id,),
    ).fetchone()["c"]


# ---------------------------------------------------------------------------
# Itens extraídos e revisão (docs/06, seções 14.5/14.6; docs/07, Fase 6)
# ---------------------------------------------------------------------------

_EXTRACTED_ITEM_BASE = """
    SELECT ei.*, p.page_number, p.imported_file_id, p.page_profile
    FROM extracted_items ei
    JOIN imported_pages p ON p.id = ei.imported_page_id
"""


def list_extracted_items(
    connection: sqlite3.Connection,
    import_id: int,
    *,
    review_status: str | None,
    confidence_level: str | None,
    page_number: int | None,
    search: str | None,
    page: int,
    page_size: int,
) -> tuple[list[sqlite3.Row], int]:
    where = ["p.imported_file_id = ?"]
    params: list[object] = [import_id]

    if review_status is not None:
        where.append("ei.review_status = ?")
        params.append(review_status)
    if confidence_level is not None:
        where.append("ei.confidence_level = ?")
        params.append(confidence_level)
    if page_number is not None:
        where.append("p.page_number = ?")
        params.append(page_number)
    if search is not None:
        where.append("(ei.description_raw LIKE ? OR ei.sku_raw LIKE ? OR ei.price_raw LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like])

    where_sql = " AND ".join(where)

    total = connection.execute(
        f"SELECT COUNT(*) AS c FROM extracted_items ei JOIN imported_pages p "
        f"ON p.id = ei.imported_page_id WHERE {where_sql}",
        params,
    ).fetchone()["c"]

    offset = (page - 1) * page_size
    rows = connection.execute(
        f"""
        {_EXTRACTED_ITEM_BASE}
        WHERE {where_sql}
        ORDER BY ei.confidence ASC, ei.id ASC
        LIMIT ? OFFSET ?
        """,
        [*params, page_size, offset],
    ).fetchall()
    return rows, total


def get_extracted_item(connection: sqlite3.Connection, item_id: int) -> sqlite3.Row | None:
    return connection.execute(_EXTRACTED_ITEM_BASE + " WHERE ei.id = ?", (item_id,)).fetchone()


def update_extracted_item_field(
    connection: sqlite3.Connection, item_id: int, field: str, value: str | None
) -> None:
    connection.execute(f"UPDATE extracted_items SET {field} = ? WHERE id = ?", (value, item_id))


def set_extracted_item_review_status(
    connection: sqlite3.Connection, item_id: int, review_status: str
) -> None:
    connection.execute(
        "UPDATE extracted_items SET review_status = ? WHERE id = ?", (review_status, item_id)
    )


def insert_review_decision(
    connection: sqlite3.Connection,
    *,
    extracted_item_id: int,
    decision: str,
    reviewed_by_user_id: int | None,
    field_corrected: str | None,
    previous_value: str | None,
    corrected_value: str | None,
    notes: str | None,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO import_review_decisions (
            extracted_item_id, decision, reviewed_by_user_id,
            field_corrected, previous_value, corrected_value, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            extracted_item_id,
            decision,
            reviewed_by_user_id,
            field_corrected,
            previous_value,
            corrected_value,
            notes,
        ),
    )
    return int(cursor.lastrowid)


def get_review_decision(connection: sqlite3.Connection, decision_id: int) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT d.*, u.id AS reviewed_by_id, u.name AS reviewed_by_name
        FROM import_review_decisions d
        LEFT JOIN users u ON u.id = d.reviewed_by_user_id
        WHERE d.id = ?
        """,
        (decision_id,),
    ).fetchone()


def get_latest_correction_decision(
    connection: sqlite3.Connection, extracted_item_id: int, field: str
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT * FROM import_review_decisions
        WHERE extracted_item_id = ? AND decision = 'corrigido' AND field_corrected = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (extracted_item_id, field),
    ).fetchone()


def find_batch_correction_candidates(
    connection: sqlite3.Connection,
    *,
    field: str,
    previous_value: str | None,
    scope: str,
    exclude_item_id: int,
    imported_page_id: int,
    imported_file_id: int,
    page_profile: str | None,
) -> list[sqlite3.Row]:
    where = [f"ei.{field} = ?", "ei.id != ?"]
    params: list[object] = [previous_value, exclude_item_id]

    if scope == "page":
        where.append("ei.imported_page_id = ?")
        params.append(imported_page_id)
    elif scope == "page_profile":
        where.append("p.imported_file_id = ?")
        where.append("p.page_profile IS ?")
        params.extend([imported_file_id, page_profile])
    else:  # import
        where.append("p.imported_file_id = ?")
        params.append(imported_file_id)

    where_sql = " AND ".join(where)
    return connection.execute(
        f"""
        SELECT ei.*, p.page_number, p.page_profile
        FROM extracted_items ei
        JOIN imported_pages p ON p.id = ei.imported_page_id
        WHERE {where_sql}
        ORDER BY p.page_number ASC, ei.id ASC
        """,
        params,
    ).fetchall()
