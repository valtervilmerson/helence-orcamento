"""Regras de negócio do catálogo manual (docs/06, seções 14.8/14.9)."""

from __future__ import annotations

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
    PriceHistoryEntry,
    PriceSummary,
    PriceTableSummary,
)
from app.shared.errors import (
    ComponenteEmUsoError,
    ComponenteNaoEncontradoError,
    PrecoDuplicadoError,
    ReferenciaInvalidaError,
    RegistroDuplicadoError,
    RegistroEmUsoError,
    RegistroNaoEncontradoError,
    VariacaoDuplicadaError,
)

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


def _row_to_variant_out(
    row: sqlite3.Row, price_history: list[PriceHistoryEntry] | None = None
) -> ComponentVariantOut:
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
    price_table = None
    if row["price_amount"] is not None:
        price = PriceSummary(amount=row["price_amount"], currency=row["price_currency"])
        price_table = PriceTableSummary(
            id=row["price_table_id"], code=row["price_table_code"], status=row["price_table_status"]
        )

    return ComponentVariantOut(
        component_variant_id=row["component_variant_id"],
        family=row["family"],
        product=row["product"],
        component=row["component"],
        descriptor=row["descriptor"],
        description=row["description"],
        dimension=dimension,
        finish=row["finish"],
        sku=row["sku"],
        price=price,
        price_table=price_table,
        price_history=price_history,
    )


def search_variants(
    connection: sqlite3.Connection,
    *,
    family: str | None = None,
    product: str | None = None,
    component: str | None = None,
    dimension: str | None = None,
    finish: str | None = None,
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

    history_rows = repository.get_price_history(connection, variant_id)
    history = [
        PriceHistoryEntry(
            price_table=PriceTableSummary(
                id=h["price_table_id"], code=h["price_table_code"], status=h["price_table_status"]
            ),
            price=PriceSummary(amount=h["price_amount"], currency=h["price_currency"]),
        )
        for h in history_rows
    ]
    return _row_to_variant_out(row, price_history=history)


def create_variant(
    connection: sqlite3.Connection, payload: ComponentVariantIn
) -> ComponentVariantOut:
    data = payload.model_dump(exclude={"sku", "price"})
    _validate_variant_references(connection, data)

    try:
        variant_id = repository.insert_variant(connection, data)
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        if "UNIQUE" in str(exc):
            raise VariacaoDuplicadaError() from exc
        raise ReferenciaInvalidaError() from exc

    if payload.price is not None:
        if not _row_exists(connection, "price_tables", payload.price.price_table_id):
            connection.rollback()
            raise ReferenciaInvalidaError(
                details={"field": "price.price_table_id", "value": payload.price.price_table_id}
            )

        sku_code = payload.sku.code if payload.sku is not None else None
        if sku_code is None:
            connection.rollback()
            raise ReferenciaInvalidaError(
                details={"field": "sku", "message": "obrigatório com price"}
            )

        sku_id = repository.get_or_create_sku(
            connection, sku_code, payload.sku.notes if payload.sku else None
        )

        try:
            repository.insert_price(
                connection,
                component_variant_id=variant_id,
                sku_id=sku_id,
                price_table_id=payload.price.price_table_id,
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
    if references.get("quote_item_components") or references.get("prices", 0) > 1:
        raise ComponenteEmUsoError(details={"referenced_by": references})

    repository.delete_variant(connection, variant_id)
