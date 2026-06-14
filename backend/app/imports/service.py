"""Regras de negócio de upload/listagem de importações (docs/06, 14.1/14.2).

Esta fase apenas recebe e guarda o arquivo (docs/07, Fase 4) — extração e
processamento são, deliberadamente, escopo da Fase 5.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from datetime import datetime

import fitz

from app.catalog.schemas import PriceTableSummary
from app.db.connection import get_connection
from app.files.storage import FileStorage
from app.imports import repository
from app.imports.extraction import extract_page
from app.imports.schemas import (
    BatchCorrectionApplyIn,
    BatchCorrectionApplyOut,
    BatchCorrectionCandidate,
    BatchCorrectionPreviewOut,
    BatchReviewIn,
    BatchReviewOut,
    BatchReviewResultItem,
    ExtractedItemOut,
    ExtractedItemsListOut,
    ImportedFileOut,
    ImportError,
    ImportListItem,
    ImportListOut,
    ImportProgress,
    ImportStatusOut,
    ImportSummary,
    ProcessImportOut,
    ReviewDecisionOut,
    ReviewItemIn,
    ReviewItemOut,
    UserSummary,
)
from app.shared.errors import (
    ArquivoDuplicadoError,
    ArquivoInvalidoError,
    ArquivoMuitoGrandeError,
    CampoNaoCorrigivelError,
    CampoObrigatorioAusenteError,
    CorrecaoOrigemNaoEncontradaError,
    DomainError,
    EstrategiaIndisponivelError,
    ImportacaoNaoEncontradaError,
    ImportacaoStatusInvalidoError,
    ItemNaoEncontradoError,
    ItemRevisaoStatusInvalidoError,
    ParametroInvalidoError,
    ValorIncompativelError,
)

logger = logging.getLogger("app.domain.imports")

PDF_MAGIC = b"%PDF-"

ALLOWED_STATUSES = {"recebido", "processando", "concluido", "erro"}

SUPPORTED_STRATEGIES = {"pymupdf"}

ALLOWED_REVIEW_STATUSES = {"pendente", "revisado", "aprovado", "rejeitado", "corrigido"}

ALLOWED_CONFIDENCE_LEVELS = {"alta", "media", "baixa"}

# Campos do item extraído que o revisor pode corrigir manualmente
# (docs/04, seção 4 — capacidades 3-6: SKU, preço, acabamento, dimensão e
# tipo de componente; descrição é somente leitura).
CORRECTABLE_FIELDS = {
    "sku_raw",
    "price_raw",
    "finish_raw",
    "dimension_raw",
    "component_type_raw",
}

FINAL_REVIEW_STATUSES = {"aprovado", "rejeitado"}


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

    items = [_build_import_list_item(connection, row) for row in rows]

    return ImportListOut(items=items, page=page, page_size=page_size, total=total)


def get_import_summary(connection: sqlite3.Connection, import_id: int) -> ImportListItem:
    row = repository.get_imported_file(connection, import_id)
    if row is None:
        raise ImportacaoNaoEncontradaError()
    return _build_import_list_item(connection, row)


def _build_import_list_item(connection: sqlite3.Connection, row: sqlite3.Row) -> ImportListItem:
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

    return ImportListItem(
        id=row["id"],
        original_filename=row["original_filename"],
        status=row["status"],
        page_count=row["page_count"],
        imported_at=row["imported_at"],
        items_extracted=repository.count_extracted_items(connection, row["id"]),
        items_pending_review=repository.count_pending_review_items(connection, row["id"]),
        items_blocking_publication=repository.count_unreviewed_items(connection, row["id"]),
        linked_price_table=linked_price_table,
    )


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
    logger.info("Importação #%s: processamento iniciado (%s)", import_id, file_path)
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
            logger.info(
                "Importação #%s: processamento concluído (%s páginas)",
                import_id,
                document.page_count,
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
            logger.error("Importação #%s: processamento falhou", import_id, exc_info=exc)


def _extracted_item_row_to_out(row: sqlite3.Row) -> ExtractedItemOut:
    return ExtractedItemOut(
        id=row["id"],
        imported_page_id=row["imported_page_id"],
        page_number=row["page_number"],
        family_raw=row["family_raw"],
        product_context_raw=row["product_context_raw"],
        component_type_raw=row["component_type_raw"],
        description_raw=row["description_raw"],
        dimension_raw=row["dimension_raw"],
        finish_raw=row["finish_raw"],
        sku_raw=row["sku_raw"],
        price_raw=row["price_raw"],
        confidence=row["confidence"],
        confidence_level=row["confidence_level"],
        review_status=row["review_status"],
        source_text=row["source_text"],
    )


def list_items(
    connection: sqlite3.Connection,
    import_id: int,
    *,
    review_status: str | None,
    confidence_level: str | None,
    page_number: int | None,
    search: str | None,
    page: int,
    page_size: int,
) -> ExtractedItemsListOut:
    if repository.get_imported_file(connection, import_id) is None:
        raise ImportacaoNaoEncontradaError()

    if review_status is not None and review_status not in ALLOWED_REVIEW_STATUSES:
        raise ParametroInvalidoError(
            details={"review_status": review_status, "allowed": sorted(ALLOWED_REVIEW_STATUSES)}
        )
    if confidence_level is not None and confidence_level not in ALLOWED_CONFIDENCE_LEVELS:
        raise ParametroInvalidoError(
            details={
                "confidence_level": confidence_level,
                "allowed": sorted(ALLOWED_CONFIDENCE_LEVELS),
            }
        )

    rows, total = repository.list_extracted_items(
        connection,
        import_id,
        review_status=review_status,
        confidence_level=confidence_level,
        page_number=page_number,
        search=search,
        page=page,
        page_size=page_size,
    )

    return ExtractedItemsListOut(
        items=[_extracted_item_row_to_out(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


def review_item(
    connection: sqlite3.Connection, item_id: int, payload: ReviewItemIn
) -> ReviewItemOut:
    row = repository.get_extracted_item(connection, item_id)
    if row is None:
        raise ItemNaoEncontradoError()

    if row["review_status"] in FINAL_REVIEW_STATUSES:
        raise ItemRevisaoStatusInvalidoError()

    field_corrected: str | None = None
    previous_value: str | None = None
    corrected_value: str | None = None

    if payload.decision == "rejeitado":
        if not payload.notes:
            raise CampoObrigatorioAusenteError(
                details={"field": "notes", "reason": "obrigatório ao rejeitar um item"}
            )
        new_review_status = "rejeitado"

    elif payload.decision == "corrigido":
        if not payload.field or payload.corrected_value is None:
            raise CampoObrigatorioAusenteError(
                details={
                    "fields": ["field", "corrected_value"],
                    "reason": "obrigatórios ao corrigir um item",
                }
            )
        if payload.field not in CORRECTABLE_FIELDS:
            raise CampoNaoCorrigivelError(
                details={"field": payload.field, "allowed": sorted(CORRECTABLE_FIELDS)}
            )
        if payload.field == "price_raw":
            try:
                if float(payload.corrected_value) <= 0:
                    raise ValueError
            except ValueError as exc:
                raise ValorIncompativelError(
                    details={"field": payload.field, "corrected_value": payload.corrected_value}
                ) from exc

        if payload.new_finish_name is not None:
            if payload.field != "finish_raw":
                raise CampoNaoCorrigivelError(
                    details={
                        "field": payload.field,
                        "reason": "new_finish_name só é aplicável ao corrigir finish_raw",
                    }
                )
            if not payload.new_finish_group:
                raise CampoObrigatorioAusenteError(
                    details={
                        "field": "new_finish_group",
                        "reason": "obrigatório ao cadastrar um novo acabamento",
                    }
                )

        field_corrected = payload.field
        previous_value = row[payload.field]
        corrected_value = payload.corrected_value

        repository.update_extracted_item_field(
            connection, item_id, payload.field, payload.corrected_value
        )
        new_review_status = "corrigido"

    else:  # aprovado
        new_review_status = "aprovado"

    repository.set_extracted_item_review_status(connection, item_id, new_review_status)
    logger.info("Item extraído #%s: decisão de revisão -> %s", item_id, new_review_status)

    decision_id = repository.insert_review_decision(
        connection,
        extracted_item_id=item_id,
        decision=payload.decision,
        reviewed_by_user_id=payload.reviewed_by_user_id,
        field_corrected=field_corrected,
        previous_value=previous_value,
        corrected_value=corrected_value,
        notes=payload.notes,
    )

    if payload.new_finish_name is not None:
        repository.insert_import_warning(
            connection,
            imported_file_id=row["imported_file_id"],
            imported_page_id=row["imported_page_id"],
            extracted_item_id=item_id,
            severity="atencao",
            message=(
                f"Novo acabamento sugerido na revisão do item #{item_id}: "
                f"'{payload.new_finish_name}' (grupo: {payload.new_finish_group}). "
                "Requer cadastro em finishes antes da publicação no catálogo."
            ),
        )

    connection.commit()

    decision_row = repository.get_review_decision(connection, decision_id)
    assert decision_row is not None

    reviewed_by = None
    if decision_row["reviewed_by_id"] is not None:
        reviewed_by = UserSummary(
            id=decision_row["reviewed_by_id"], name=decision_row["reviewed_by_name"]
        )

    return ReviewItemOut(
        id=item_id,
        review_status=new_review_status,
        decision=ReviewDecisionOut(
            id=decision_row["id"],
            decision=decision_row["decision"],
            field_corrected=decision_row["field_corrected"],
            previous_value=decision_row["previous_value"],
            corrected_value=decision_row["corrected_value"],
            reviewed_by=reviewed_by,
            reviewed_at=decision_row["reviewed_at"],
        ),
    )


# ---------------------------------------------------------------------------
# Aprovação/rejeição em lote (docs/04, seção 3 — barra de ações em lote)
# ---------------------------------------------------------------------------


def batch_review_items(connection: sqlite3.Connection, payload: BatchReviewIn) -> BatchReviewOut:
    if not payload.item_ids:
        raise ParametroInvalidoError(
            details={"item_ids": payload.item_ids, "reason": "seleção vazia"}
        )

    if payload.decision == "rejeitado" and not payload.notes:
        raise CampoObrigatorioAusenteError(
            details={"field": "notes", "reason": "obrigatório para rejeitar itens em lote"}
        )

    results: list[BatchReviewResultItem] = []
    for item_id in payload.item_ids:
        try:
            review_item(
                connection,
                item_id,
                ReviewItemIn(decision=payload.decision, notes=payload.notes),
            )
            results.append(BatchReviewResultItem(item_id=item_id, success=True))
        except DomainError as exc:
            results.append(
                BatchReviewResultItem(
                    item_id=item_id, success=False, error_code=exc.code, error_message=exc.message
                )
            )

    succeeded = sum(1 for r in results if r.success)
    return BatchReviewOut(
        decision=payload.decision,
        requested_count=len(payload.item_ids),
        succeeded_count=succeeded,
        failed_count=len(results) - succeeded,
        results=results,
    )


# ---------------------------------------------------------------------------
# Correção em lote (docs/04, seção 4 — fluxo de correção em lote)
# ---------------------------------------------------------------------------

ALLOWED_BATCH_SCOPES = {"page", "page_profile", "import"}


def _resolve_batch_correction_source(
    connection: sqlite3.Connection, item_id: int, field: str | None, scope: str | None
) -> tuple[sqlite3.Row, sqlite3.Row]:
    if field is None or scope is None:
        raise CampoObrigatorioAusenteError(
            details={"fields": ["field", "scope"], "reason": "obrigatórios para correção em lote"}
        )
    if scope not in ALLOWED_BATCH_SCOPES:
        raise ParametroInvalidoError(
            details={"scope": scope, "allowed": sorted(ALLOWED_BATCH_SCOPES)}
        )

    row = repository.get_extracted_item(connection, item_id)
    if row is None:
        raise ItemNaoEncontradoError()

    if field not in CORRECTABLE_FIELDS:
        raise CampoNaoCorrigivelError(
            details={"field": field, "allowed": sorted(CORRECTABLE_FIELDS)}
        )

    decision_row = repository.get_latest_correction_decision(connection, item_id, field)
    if decision_row is None:
        raise CorrecaoOrigemNaoEncontradaError(details={"item_id": item_id, "field": field})

    return row, decision_row


def preview_batch_correction(
    connection: sqlite3.Connection, item_id: int, *, field: str | None, scope: str | None
) -> BatchCorrectionPreviewOut:
    row, decision_row = _resolve_batch_correction_source(connection, item_id, field, scope)
    assert field is not None and scope is not None

    candidates = repository.find_batch_correction_candidates(
        connection,
        field=field,
        previous_value=decision_row["previous_value"],
        scope=scope,
        exclude_item_id=item_id,
        imported_page_id=row["imported_page_id"],
        imported_file_id=row["imported_file_id"],
        page_profile=row["page_profile"],
    )

    eligible = [c for c in candidates if c["review_status"] == "pendente"]
    already_decided = [c for c in candidates if c["review_status"] != "pendente"]

    return BatchCorrectionPreviewOut(
        field=field,
        previous_value=decision_row["previous_value"],
        corrected_value=decision_row["corrected_value"],
        scope=scope,
        eligible_count=len(eligible),
        already_decided_count=len(already_decided),
        already_decided_item_ids=[c["id"] for c in already_decided],
        candidates=[
            BatchCorrectionCandidate(
                id=c["id"],
                page_number=c["page_number"],
                confidence_level=c["confidence_level"],
                previous_value=c[field],
                corrected_value=decision_row["corrected_value"],
            )
            for c in eligible[:20]
        ],
    )


def apply_batch_correction(
    connection: sqlite3.Connection, item_id: int, payload: BatchCorrectionApplyIn
) -> BatchCorrectionApplyOut:
    row, decision_row = _resolve_batch_correction_source(
        connection, item_id, payload.field, payload.scope
    )
    field = payload.field
    assert field is not None

    candidates = repository.find_batch_correction_candidates(
        connection,
        field=field,
        previous_value=decision_row["previous_value"],
        scope=payload.scope,
        exclude_item_id=item_id,
        imported_page_id=row["imported_page_id"],
        imported_file_id=row["imported_file_id"],
        page_profile=row["page_profile"],
    )

    eligible = [c for c in candidates if c["review_status"] == "pendente"]
    already_decided = [c for c in candidates if c["review_status"] != "pendente"]

    corrected_value = decision_row["corrected_value"]
    notes = f"Correção em lote a partir do item #{item_id}."
    if payload.notes:
        notes = f"{notes} {payload.notes}"

    for candidate in eligible:
        repository.update_extracted_item_field(connection, candidate["id"], field, corrected_value)
        repository.set_extracted_item_review_status(connection, candidate["id"], "corrigido")
        repository.insert_review_decision(
            connection,
            extracted_item_id=candidate["id"],
            decision="corrigido",
            reviewed_by_user_id=None,
            field_corrected=field,
            previous_value=candidate[field],
            corrected_value=corrected_value,
            notes=notes,
        )

    connection.commit()

    return BatchCorrectionApplyOut(
        field=field,
        previous_value=decision_row["previous_value"],
        corrected_value=corrected_value,
        scope=payload.scope,
        applied_count=len(eligible),
        applied_item_ids=[c["id"] for c in eligible],
        skipped_item_ids=[c["id"] for c in already_decided],
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
