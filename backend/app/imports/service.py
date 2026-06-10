"""Regras de negócio de upload/listagem de importações (docs/06, 14.1/14.2).

Esta fase apenas recebe e guarda o arquivo (docs/07, Fase 4) — extração e
processamento são, deliberadamente, escopo da Fase 5.
"""

from __future__ import annotations

import hashlib
import sqlite3

from app.catalog.schemas import PriceTableSummary
from app.files.storage import FileStorage
from app.imports import repository
from app.imports.schemas import ImportedFileOut, ImportListItem, ImportListOut, UserSummary
from app.shared.errors import (
    ArquivoDuplicadoError,
    ArquivoInvalidoError,
    ArquivoMuitoGrandeError,
    ParametroInvalidoError,
)

PDF_MAGIC = b"%PDF-"

ALLOWED_STATUSES = {"recebido", "processando", "concluido", "erro"}


def _row_to_out(row: sqlite3.Row) -> ImportedFileOut:
    imported_by = None
    if row["imported_by_id"] is not None:
        imported_by = UserSummary(id=row["imported_by_id"], name=row["imported_by_name"])

    return ImportedFileOut(
        id=row["id"],
        original_filename=row["original_filename"],
        file_hash=row["file_hash"],
        page_count=row["page_count"],
        status=row["status"],
        imported_at=row["imported_at"],
        imported_by=imported_by,
        notes=row["notes"],
    )


def receive_upload(
    connection: sqlite3.Connection,
    storage: FileStorage,
    *,
    content: bytes,
    original_filename: str | None,
    notes: str | None,
    max_upload_size_bytes: int,
) -> ImportedFileOut:
    if len(content) > max_upload_size_bytes:
        raise ArquivoMuitoGrandeError(details={"max_bytes": max_upload_size_bytes})

    if not content.startswith(PDF_MAGIC):
        raise ArquivoInvalidoError()

    file_hash = hashlib.sha256(content).hexdigest()

    existing = repository.find_by_hash(connection, file_hash)
    if existing is not None:
        raise ArquivoDuplicadoError(details={"existing_import_id": existing["id"]})

    stored_path = storage.save(f"{file_hash}.pdf", content)

    import_id = repository.insert_imported_file(
        connection,
        file_path=str(stored_path),
        file_hash=file_hash,
        original_filename=original_filename,
        notes=notes,
    )
    row = repository.get_imported_file(connection, import_id)
    assert row is not None
    return _row_to_out(row)


def list_imports(
    connection: sqlite3.Connection,
    *,
    status: str | None,
    page: int,
    page_size: int,
) -> ImportListOut:
    if status is not None and status not in ALLOWED_STATUSES:
        raise ParametroInvalidoError(
            details={"status": status, "allowed": sorted(ALLOWED_STATUSES)}
        )

    rows, total = repository.list_imported_files(
        connection, status=status, page=page, page_size=page_size
    )

    items = []
    for row in rows:
        price_table_row = repository.get_linked_price_table(connection, row["id"])
        linked_price_table = (
            PriceTableSummary(
                id=price_table_row["id"],
                code=price_table_row["code"],
                status=price_table_row["status"],
            )
            if price_table_row is not None
            else None
        )
        items.append(
            ImportListItem(
                id=row["id"],
                original_filename=row["original_filename"],
                status=row["status"],
                page_count=row["page_count"],
                imported_at=row["imported_at"],
                items_extracted=repository.count_extracted_items(connection, row["id"]),
                items_pending_review=repository.count_pending_review_items(connection, row["id"]),
                linked_price_table=linked_price_table,
            )
        )

    return ImportListOut(items=items, page=page, page_size=page_size, total=total)
