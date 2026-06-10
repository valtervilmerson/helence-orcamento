"""Regras de negócio de upload/listagem de importações (docs/06, 14.1/14.2).

Esta fase apenas recebe e guarda o arquivo (docs/07, Fase 4) — extração e
processamento são, deliberadamente, escopo da Fase 5.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime

import fitz

from app.catalog.schemas import PriceTableSummary
from app.db.connection import get_connection
from app.files.storage import FileStorage
from app.imports import repository
from app.imports.extraction import extract_page
from app.imports.schemas import (
    ImportedFileOut,
    ImportError,
    ImportListItem,
    ImportListOut,
    ImportProgress,
    ImportStatusOut,
    ImportSummary,
    ProcessImportOut,
    UserSummary,
)
from app.shared.errors import (
    ArquivoDuplicadoError,
    ArquivoInvalidoError,
    ArquivoMuitoGrandeError,
    EstrategiaIndisponivelError,
    ImportacaoNaoEncontradaError,
    ImportacaoStatusInvalidoError,
    ParametroInvalidoError,
)

PDF_MAGIC = b"%PDF-"

ALLOWED_STATUSES = {"recebido", "processando", "concluido", "erro"}

SUPPORTED_STRATEGIES = {"pymupdf"}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


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


# ---------------------------------------------------------------------------
# Processamento (docs/06, 14.3/14.4; docs/07, Fase 5)
# ---------------------------------------------------------------------------


def start_processing(
    connection: sqlite3.Connection, import_id: int, *, strategy: str | None
) -> ProcessImportOut:
    row = repository.get_imported_file(connection, import_id)
    if row is None:
        raise ImportacaoNaoEncontradaError()

    if strategy is not None and strategy not in SUPPORTED_STRATEGIES:
        raise EstrategiaIndisponivelError(
            details={"strategy": strategy, "allowed": sorted(SUPPORTED_STRATEGIES)}
        )

    if row["status"] in ("processando", "concluido"):
        raise ImportacaoStatusInvalidoError()

    started_at = _now()
    repository.mark_processing_started(connection, import_id, started_at)
    return ProcessImportOut(id=import_id, status="processando", started_at=started_at)


def run_processing(import_id: int, file_path: str) -> None:
    """Extração em segundo plano (docs/06, seção 7 — sem fila externa).

    Roda fora do ciclo de vida da requisição original: abre sua própria
    conexão e faz commit incremental por página, para que o polling em
    `GET /imports/{id}/status` reflita o progresso real.
    """
    with get_connection() as connection:
        try:
            document = fitz.open(file_path)
            repository.set_pages_total(connection, import_id, document.page_count)

            for page_number in range(1, document.page_count + 1):
                page = document.load_page(page_number - 1)
                extraction = extract_page(page, page_number)

                imported_page_id = repository.insert_imported_page(
                    connection,
                    imported_file_id=import_id,
                    page_number=page_number,
                    page_profile=extraction.page_profile,
                    section=extraction.section,
                )

                for raw_row in extraction.raw_rows:
                    repository.insert_extracted_row(
                        connection,
                        imported_page_id=imported_page_id,
                        sequence_no=raw_row.sequence_no,
                        y_coordinate=raw_row.y,
                        raw_text=raw_row.text,
                        is_vertical_text=raw_row.is_vertical,
                    )

                for item in extraction.items:
                    repository.insert_extracted_item(
                        connection,
                        imported_page_id=imported_page_id,
                        family_raw=item.family_raw,
                        product_context_raw=item.product_context_raw,
                        component_type_raw=item.component_type_raw,
                        description_raw=item.description_raw,
                        dimension_raw=item.dimension_raw,
                        finish_raw=item.finish_raw,
                        sku_raw=item.sku_raw,
                        price_raw=item.price_raw,
                        currency=item.currency,
                        confidence=item.confidence,
                        confidence_level=item.confidence_level,
                        source_text=item.source_text,
                        extraction_notes=json.dumps(item.extraction_notes, ensure_ascii=False),
                    )

                for warning in extraction.warnings:
                    repository.insert_import_warning(
                        connection,
                        imported_file_id=import_id,
                        imported_page_id=imported_page_id,
                        severity="info",
                        message=warning,
                    )

                connection.commit()
                repository.set_pages_processed(connection, import_id, page_number)

            repository.mark_processing_finished(
                connection, import_id, finished_at=_now(), page_count=document.page_count
            )
        except Exception as exc:  # noqa: BLE001 - registrado como erro de domínio na importação
            connection.rollback()
            repository.mark_processing_error(
                connection,
                import_id,
                finished_at=_now(),
                error_code="ERRO_PROCESSAMENTO",
                error_message=str(exc),
            )


def get_status(connection: sqlite3.Connection, import_id: int) -> ImportStatusOut:
    row = repository.get_imported_file(connection, import_id)
    if row is None:
        raise ImportacaoNaoEncontradaError()

    error = None
    if row["status"] == "erro":
        error = ImportError(
            code=row["error_code"] or "ERRO_PROCESSAMENTO",
            message=row["error_message"] or "",
        )

    return ImportStatusOut(
        id=row["id"],
        status=row["status"],
        progress=ImportProgress(
            pages_total=row["pages_total"], pages_processed=row["pages_processed"]
        ),
        started_at=row["processing_started_at"],
        finished_at=row["processing_finished_at"],
        summary=ImportSummary(
            items_extracted=repository.count_extracted_items(connection, import_id),
            warnings=repository.count_warnings(connection, import_id),
        ),
        error=error,
    )
