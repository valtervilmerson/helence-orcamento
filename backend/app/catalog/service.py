"""Regras de negócio do catálogo manual (docs/06, seções 14.8/14.9)."""

from __future__ import annotations

import logging
import re
import sqlite3
from typing import Any

from app.catalog import repository
from app.catalog.repository import SimpleRepository
from app.catalog.schemas import (
    ComponentVariantIn,
    ComponentVariantOut,
    ComponentVariantPatch,
    ComponentVariantSearchResult,
    DimensionSummary,
    PriceSummary,
    PublishIn,
    PublishOut,
)
from app.imports import repository as imports_repository
from app.imports.extraction import PRICE_VALUE_PATTERN
from app.shared.errors import (
    AcabamentoNaoCadastradoError,
    ComponenteEmUsoError,
    ComponenteNaoEncontradoError,
    ConfirmacaoAusenteError,
    ItemPublicacaoInvalidoError,
    ItensPendentesDeRevisaoError,
    PrecoDuplicadoError,
    ReferenciaInvalidaError,
    RegistroDuplicadoError,
    RegistroEmUsoError,
    RegistroNaoEncontradoError,
    VariacaoDuplicadaError,
)

logger = logging.getLogger("app.domain.catalog")

# ---------------------------------------------------------------------------
# CRUD genérico para entidades de referência simples
# ---------------------------------------------------------------------------


def list_entities(connection: sqlite3.Connection, repo: SimpleRepository) -> list[sqlite3.Row]:
    return repo.list(connection)


def get_entity(connection: sqlite3.Connection, repo: SimpleRepository, id_: int) -> sqlite3.Row:
    row = repo.get(connection, id_)
    if row is None:
        raise RegistroNaoEncontradoError(details={"id": id_})
    return row


def create_entity(
    connection: sqlite3.Connection, repo: SimpleRepository, data: dict[str, Any]
) -> sqlite3.Row:
    try:
        new_id = repo.create(connection, data)
    except sqlite3.IntegrityError as exc:
        raise _map_integrity_error(exc) from exc
    return get_entity(connection, repo, new_id)


def update_entity(
    connection: sqlite3.Connection, repo: SimpleRepository, id_: int, data: dict[str, Any]
) -> sqlite3.Row:
    get_entity(connection, repo, id_)
    try:
        repo.update(connection, id_, data)
    except sqlite3.IntegrityError as exc:
        raise _map_integrity_error(exc) from exc
    return get_entity(connection, repo, id_)


def delete_entity(connection: sqlite3.Connection, repo: SimpleRepository, id_: int) -> None:
    get_entity(connection, repo, id_)
    try:
        repo.delete(connection, id_)
    except sqlite3.IntegrityError as exc:
        raise RegistroEmUsoError(details={"id": id_}) from exc


def _map_integrity_error(exc: sqlite3.IntegrityError) -> Exception:
    message = str(exc)
    if "FOREIGN KEY" in message:
        return ReferenciaInvalidaError()
    if "UNIQUE" in message:
        return RegistroDuplicadoError()
    return RegistroEmUsoError()


# ---------------------------------------------------------------------------
# Variações vendáveis (component_variants + sku + price) — 14.9
# ---------------------------------------------------------------------------


def _row_exists(connection: sqlite3.Connection, table: str, id_: int) -> bool:
    return connection.execute(f"SELECT 1 FROM {table} WHERE id = ?", (id_,)).fetchone() is not None


def _validate_variant_references(connection: sqlite3.Connection, payload: dict[str, Any]) -> None:
    checks = {
        "product_id": "products",
        "component_id": "product_components",
        "dimension_id": "dimensions",
        "finish_id": "finishes",
    }
    for field, table in checks.items():
        value = payload.get(field)
        if value is not None and not _row_exists(connection, table, value):
            raise ReferenciaInvalidaError(details={"field": field, "value": value})


def _row_to_variant_out(row: sqlite3.Row) -> ComponentVariantOut:
    dimension = None
    dim_fields = (
        "dim_width_mm",
        "dim_depth_mm",
        "dim_diameter_mm",
        "dim_height_mm",
        "dim_raw_label",
    )
    if any(row[field] is not None for field in dim_fields):
        dimension = DimensionSummary(
            width_mm=row["dim_width_mm"],
            depth_mm=row["dim_depth_mm"],
            diameter_mm=row["dim_diameter_mm"],
            height_mm=row["dim_height_mm"],
            raw_label=row["dim_raw_label"],
        )

    price = None
    if row["price_amount"] is not None:
        price = PriceSummary(amount=row["price_amount"], currency=row["price_currency"])

    return ComponentVariantOut(
        component_variant_id=row["component_variant_id"],
        family_id=row["family_id"],
        family=row["family"],
        product=row["product"],
        component=row["component"],
        descriptor=row["descriptor"],
        description=row["description"],
        dimension=dimension,
        finish=row["finish"],
        finish_group=row["finish_group"],
        sku=row["sku"],
        price=price,
    )


def search_variants(
    connection: sqlite3.Connection,
    *,
    family: str | None = None,
    product: str | None = None,
    component: str | None = None,
    dimension: str | None = None,
    finish: str | None = None,
    finish_group: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> ComponentVariantSearchResult:
    rows, total = repository.search_variants(
        connection,
        family=family,
        product=product,
        component=component,
        dimension=dimension,
        finish=finish,
        finish_group=finish_group,
        q=q,
        page=page,
        page_size=page_size,
    )
    return ComponentVariantSearchResult(
        items=[_row_to_variant_out(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


def get_variant(connection: sqlite3.Connection, variant_id: int) -> ComponentVariantOut:
    row = repository.get_variant_row(connection, variant_id)
    if row is None:
        raise ComponenteNaoEncontradoError(details={"id": variant_id})

    return _row_to_variant_out(row)


def create_variant(
    connection: sqlite3.Connection, payload: ComponentVariantIn
) -> ComponentVariantOut:
    data = payload.model_dump(exclude={"sku", "price"})
    _validate_variant_references(connection, data)

    if data.get("product_id") is not None:
        product_row = repository.products.get(connection, data["product_id"])
        data["family_id"] = product_row["family_id"]

    try:
        variant_id = repository.insert_variant(connection, data)
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        if "UNIQUE" in str(exc):
            raise VariacaoDuplicadaError() from exc
        raise ReferenciaInvalidaError() from exc

    if payload.price is not None:
        sku_id = None
        if payload.sku is not None:
            sku_id = repository.get_or_create_sku(connection, payload.sku.code, payload.sku.notes)

        try:
            repository.upsert_price(
                connection,
                component_variant_id=variant_id,
                sku_id=sku_id,
                amount=payload.price.amount,
                currency=payload.price.currency,
            )
        except sqlite3.IntegrityError as exc:
            connection.rollback()
            raise PrecoDuplicadoError() from exc

    connection.commit()
    return get_variant(connection, variant_id)


def update_variant(
    connection: sqlite3.Connection, variant_id: int, payload: ComponentVariantPatch
) -> ComponentVariantOut:
    if not repository.variant_exists(connection, variant_id):
        raise ComponenteNaoEncontradoError(details={"id": variant_id})

    data = payload.model_dump(exclude_unset=True)
    _validate_variant_references(connection, data)

    try:
        repository.update_variant(connection, variant_id, data)
        connection.commit()
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        if "UNIQUE" in str(exc):
            raise VariacaoDuplicadaError() from exc
        raise ReferenciaInvalidaError() from exc

    return get_variant(connection, variant_id)


def delete_variant(connection: sqlite3.Connection, variant_id: int) -> None:
    if not repository.variant_exists(connection, variant_id):
        raise ComponenteNaoEncontradoError(details={"id": variant_id})

    references = repository.referenced_by(connection, variant_id)
    if references.get("quote_item_components"):
        raise ComponenteEmUsoError(details={"referenced_by": references})

    repository.delete_variant(connection, variant_id)


# ---------------------------------------------------------------------------
# Publicação de tabela de preços (docs/06, seção 14.7; docs/07, Fase 7)
# ---------------------------------------------------------------------------

# Reconhece "1200x900", "1200 x 900 x 1000" e variações com "mm" opcional.
_DIM_XYZ_PATTERN = re.compile(r"(\d{2,4})\s*[xX]\s*(\d{2,4})\s*[xX]\s*(\d{2,4})")
_DIM_XY_PATTERN = re.compile(r"(\d{2,4})\s*[xX]\s*(\d{2,4})")
# Reconhece "900MM", "900 mm" e "Diam. 900mm" — dimensão única = diâmetro.
_DIM_DIAMETER_PATTERN = re.compile(r"(?:di[aâ]m\.?\s*)?(\d{2,4})\s*mm", re.IGNORECASE)


def _parse_dimension(raw: str) -> dict[str, int] | None:
    text = raw.strip()

    match = _DIM_XYZ_PATTERN.search(text)
    if match:
        return {
            "width_mm": int(match.group(1)),
            "depth_mm": int(match.group(2)),
            "height_mm": int(match.group(3)),
        }

    match = _DIM_XY_PATTERN.search(text)
    if match:
        return {"width_mm": int(match.group(1)), "depth_mm": int(match.group(2))}

    match = _DIM_DIAMETER_PATTERN.search(text)
    if match:
        return {"diameter_mm": int(match.group(1))}

    return None


def _parse_price_amount(price_raw: str) -> float:
    text = price_raw.strip()
    if PRICE_VALUE_PATTERN.match(text):
        text = text.replace(".", "").replace(",", ".")
    return round(float(text), 2)


def _resolve_dimension(connection: sqlite3.Connection, dimension_raw: str | None) -> int | None:
    if not dimension_raw:
        return None
    parsed = _parse_dimension(dimension_raw)
    if parsed is None:
        return None
    return repository.get_or_create_dimension(
        connection,
        width_mm=parsed.get("width_mm"),
        depth_mm=parsed.get("depth_mm"),
        diameter_mm=parsed.get("diameter_mm"),
        height_mm=parsed.get("height_mm"),
        raw_label=dimension_raw,
    )


def publish_item(connection: sqlite3.Connection, item: sqlite3.Row) -> None:
    item_id = item["id"]

    missing = [
        field
        for field in ("family_raw", "component_type_raw", "price_raw")
        if not item[field]
    ]
    if missing:
        raise ItemPublicacaoInvalidoError(
            details={"extracted_item_id": item_id, "missing_fields": missing}
        )

    try:
        amount = _parse_price_amount(item["price_raw"])
    except ValueError as exc:
        raise ItemPublicacaoInvalidoError(
            details={
                "extracted_item_id": item_id,
                "field": "price_raw",
                "value": item["price_raw"],
            }
        ) from exc

    family_id = repository.get_or_create_family(connection, item["family_raw"])

    component_id = repository.get_or_create_component_type(connection, item["component_type_raw"])

    dimension_id = _resolve_dimension(connection, item["dimension_raw"])

    product_id = None
    if item["product_context_raw"]:
        product_id = repository.get_or_create_product(
            connection, family_id, item["product_context_raw"], dimension_id
        )

    finish_id = None
    if item["finish_raw"]:
        finish_row = repository.find_finish_by_name(connection, item["finish_raw"])
        if finish_row is None:
            raise AcabamentoNaoCadastradoError(
                details={"extracted_item_id": item_id, "finish": item["finish_raw"]}
            )
        finish_id = int(finish_row["id"])

    existing_variant = repository.find_variant(
        connection,
        family_id=family_id,
        product_id=product_id,
        component_id=component_id,
        dimension_id=dimension_id,
        finish_id=finish_id,
        descriptor=None,
    )
    if existing_variant is not None:
        variant_id = int(existing_variant["id"])
    else:
        try:
            variant_id = repository.insert_variant(
                connection,
                {
                    "product_id": product_id,
                    "family_id": family_id,
                    "component_id": component_id,
                    "dimension_id": dimension_id,
                    "finish_id": finish_id,
                    "descriptor": None,
                    "description": item["description_raw"],
                },
            )
        except sqlite3.IntegrityError as exc:
            connection.rollback()
            raise VariacaoDuplicadaError(details={"extracted_item_id": item_id}) from exc

    sku_id = None
    if item["sku_raw"]:
        sku_id = repository.get_or_create_sku(connection, item["sku_raw"], None)

    try:
        repository.upsert_price(
            connection,
            component_variant_id=variant_id,
            sku_id=sku_id,
            amount=amount,
            currency=item["currency"] or "BRL",
            source_extracted_item_id=item_id,
        )
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise ItemPublicacaoInvalidoError(details={"extracted_item_id": item_id}) from exc


def publish_import(
    connection: sqlite3.Connection, import_id: int, payload: PublishIn
) -> PublishOut:
    import_row = imports_repository.get_imported_file(connection, import_id)
    if import_row is None:
        raise RegistroNaoEncontradoError(details={"id": import_id})

    if not payload.confirm:
        raise ConfirmacaoAusenteError()

    pending_count = imports_repository.count_unreviewed_items(connection, import_id)
    if pending_count > 0:
        raise ItensPendentesDeRevisaoError(
            details={
                "pending_count": pending_count,
                "review_url": f"/api/v1/imports/{import_id}/items?review_status=pendente",
            }
        )

    items = imports_repository.list_approved_items(connection, import_id)
    for item in items:
        publish_item(connection, item)

    connection.commit()

    logger.info(
        "Importação #%s: %s itens publicados no catálogo",
        import_id,
        len(items),
    )

    return PublishOut(imported_file_id=import_id, items_published=len(items))
