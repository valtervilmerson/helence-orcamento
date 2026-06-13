"""Ingestão via contrato JSON (docs/10; docs/07, Fase 13).

Recebe um JSON já normalizado por um agente de IA externo a partir de
planilhas Excel. Cada item gera uma linha em ``extracted_items`` para manter
a mesma trilha de auditoria/revisão do pipeline de PDF (Fases 4-6). Itens
"limpos" (revisão por exceção, seção 3.3 de docs/10) são publicados direto no
catálogo (reaproveitando `catalog.service.publish_item`, Fase 7); os demais
caem na fila de revisão com `import_warnings` explicando o motivo.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3

from app.catalog import repository as catalog_repository
from app.catalog import service as catalog_service
from app.catalog.schemas import PriceTableSummary
from app.files.storage import FileStorage
from app.imports import repository
from app.imports.schemas import ImportJsonIn, ImportJsonItemResult, ImportJsonOut
from app.shared.errors import ArquivoDuplicadoError

CONFIDENCE_ALTA = 0.9
CONFIDENCE_MEDIA = 0.7


def _confidence_level(confidence: float | None) -> str:
    if confidence is None:
        return "baixa"
    if confidence >= CONFIDENCE_ALTA:
        return "alta"
    if confidence >= CONFIDENCE_MEDIA:
        return "media"
    return "baixa"


def _family_id_if_exists(connection: sqlite3.Connection, name: str) -> int | None:
    row = connection.execute("SELECT id FROM product_families WHERE name = ?", (name,)).fetchone()
    return int(row["id"]) if row is not None else None


def _product_exists(connection: sqlite3.Connection, family_id: int | None, name: str) -> bool:
    if family_id is None:
        return False
    row = connection.execute(
        "SELECT id FROM products WHERE family_id = ? AND name = ?", (family_id, name)
    ).fetchone()
    return row is not None


def _component_type_exists(connection: sqlite3.Connection, name: str) -> bool:
    row = connection.execute("SELECT id FROM product_components WHERE name = ?", (name,)).fetchone()
    return row is not None


def ingest_json(
    connection: sqlite3.Connection,
    payload: ImportJsonIn,
    *,
    storage: FileStorage,
    original_filename: str | None = None,
) -> ImportJsonOut:
    raw_content = json.dumps(
        payload.model_dump(mode="json"), ensure_ascii=False, sort_keys=True
    ).encode("utf-8")
    file_hash = hashlib.sha256(raw_content).hexdigest()

    existing = repository.find_by_hash(connection, file_hash)
    if existing is not None:
        raise ArquivoDuplicadoError(details={"existing_import_id": existing["id"]})

    stored_path = storage.save(f"{file_hash}.json", raw_content)

    notes = None
    if payload.source is not None:
        notes = json.dumps(payload.source.model_dump(exclude_none=True), ensure_ascii=False)

    import_id = repository.insert_imported_file_json(
        connection,
        file_path=str(stored_path),
        file_hash=file_hash,
        original_filename=original_filename,
        notes=notes,
    )
    page_id = repository.insert_imported_page(
        connection,
        imported_file_id=import_id,
        page_number=1,
        page_profile="json_import",
        section=None,
    )

    price_table_row = catalog_repository.get_price_table_by_code(
        connection, payload.price_table.code
    )
    if price_table_row is None:
        price_table_id = catalog_repository.insert_price_table(
            connection,
            code=payload.price_table.code,
            name=payload.price_table.name,
            valid_from=payload.price_table.valid_from,
            source_imported_file_id=import_id,
        )
    else:
        price_table_id = int(price_table_row["id"])

    results: list[ImportJsonItemResult] = []
    items_published = 0
    items_pending = 0

    for item in payload.items:
        confidence_level = _confidence_level(item.confidence)

        family_id = _family_id_if_exists(connection, item.family)
        finish_row = catalog_repository.find_finish_by_name(connection, item.finish)

        reasons: list[str] = []
        if confidence_level != "alta":
            reasons.append(f"Confiança {confidence_level} — revisão necessária.")
        if item.notes:
            reasons.append(item.notes)
        if family_id is None:
            reasons.append(f"Família '{item.family}' ainda não existe no catálogo.")
        elif not _product_exists(connection, family_id, item.product_context):
            reasons.append(f"Produto '{item.product_context}' ainda não existe no catálogo.")
        if not _component_type_exists(connection, item.component_type):
            reasons.append(
                f"Tipo de componente '{item.component_type}' ainda não existe no catálogo."
            )
        if finish_row is None:
            suggestion = f" (grupo sugerido: '{item.finish_group}')" if item.finish_group else ""
            reasons.append(f"Acabamento '{item.finish}' ainda não está cadastrado{suggestion}.")

        fast_path = not reasons
        review_status = "aprovado" if fast_path else "pendente"

        extracted_item_id = repository.insert_extracted_item(
            connection,
            imported_page_id=page_id,
            family_raw=item.family,
            product_context_raw=item.product_context,
            component_type_raw=item.component_type,
            description_raw=item.description,
            dimension_raw=item.dimension,
            finish_raw=item.finish,
            sku_raw=item.sku,
            price_raw=str(item.price),
            currency=item.currency,
            confidence=item.confidence,
            confidence_level=confidence_level,
            source_text=item.ref,
            extraction_notes="[]",
        )
        repository.set_extracted_item_review_status(connection, extracted_item_id, review_status)

        if fast_path:
            item_row = repository.get_extracted_item(connection, extracted_item_id)
            assert item_row is not None
            catalog_service.publish_item(connection, item_row, price_table_id)
            items_published += 1
        else:
            for reason in reasons:
                repository.insert_import_warning(
                    connection,
                    imported_file_id=import_id,
                    imported_page_id=page_id,
                    extracted_item_id=extracted_item_id,
                    severity="atencao",
                    message=reason,
                )
            items_pending += 1

        results.append(
            ImportJsonItemResult(
                ref=item.ref,
                extracted_item_id=extracted_item_id,
                review_status=review_status,
                reasons=reasons or None,
            )
        )

    connection.commit()

    price_table_row = catalog_repository.get_price_table(connection, price_table_id)
    assert price_table_row is not None

    return ImportJsonOut(
        imported_file_id=import_id,
        price_table=PriceTableSummary(
            id=price_table_row["id"],
            code=price_table_row["code"],
            status=price_table_row["status"],
        ),
        items_total=len(payload.items),
        items_published=items_published,
        items_pending_review=items_pending,
        warnings_count=repository.count_warnings(connection, import_id),
        items=results,
    )
