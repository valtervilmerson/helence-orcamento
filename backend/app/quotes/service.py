"""Regras de negócio do ciclo de vida básico de orçamentos (docs/06, 14.10-14.13).

Forma simplificada da Fase 3 (docs/07): cada `quote_item` tem exatamente um
`quote_item_component` — sem composição múltipla (isso é a Fase 9).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from app.catalog.schemas import PriceTableSummary
from app.quotes import pricing, repository
from app.quotes.schemas import (
    CustomerSummary,
    QuoteItemComponentOut,
    QuoteItemCreateIn,
    QuoteItemOut,
    QuoteItemPatchIn,
    QuoteOut,
    QuoteTotalsOut,
    QuoteTotalWarning,
    UserSummary,
)
from app.shared.errors import (
    ClienteNaoEncontradoError,
    DescontoInvalidoError,
    DescontoSemJustificativaError,
    ItemNaoEncontradoError,
    ItemSemPrecoError,
    ItemSemSkuError,
    NenhumaTabelaVigenteError,
    OrcamentoNaoEncontradoError,
    OrcamentoVazioError,
    QuantidadeInvalidaError,
    StatusInvalidoError,
    TransicaoInvalidaError,
    VariacaoNaoEncontradaError,
)

# RN-18 (revisão final) é deliberadamente adiada — aqui validamos apenas que
# a transição respeita a ordem natural do ciclo de vida.
ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "rascunho": {"enviado", "rejeitado", "expirado"},
    "enviado": {"aprovado", "rejeitado", "expirado"},
    "aprovado": {"expirado"},
    "rejeitado": set(),
    "expirado": set(),
}


# ---------------------------------------------------------------------------
# Orçamento — 14.10
# ---------------------------------------------------------------------------


def _row_to_quote_out(row: sqlite3.Row) -> QuoteOut:
    created_by = None
    if row["created_by_id"] is not None:
        created_by = UserSummary(id=row["created_by_id"], name=row["created_by_name"])

    return QuoteOut(
        id=row["id"],
        quote_number=row["quote_number"],
        status=row["status"],
        customer=CustomerSummary(id=row["customer_id"], name=row["customer_name"]),
        price_table=PriceTableSummary(
            id=row["price_table_id"], code=row["price_table_code"], status=row["price_table_status"]
        ),
        created_by=created_by,
        created_at=row["created_at"],
        valid_until=row["valid_until"],
        notes=row["notes"],
    )


def get_quote(connection: sqlite3.Connection, quote_id: int) -> QuoteOut:
    row = repository.get_quote_row(connection, quote_id)
    if row is None:
        raise OrcamentoNaoEncontradoError(details={"id": quote_id})
    return _row_to_quote_out(row)


def list_quotes(connection: sqlite3.Connection) -> list[QuoteOut]:
    return [_row_to_quote_out(row) for row in repository.list_quote_rows(connection)]


def list_customers(connection: sqlite3.Connection) -> list[CustomerSummary]:
    return [
        CustomerSummary(id=row["id"], name=row["name"])
        for row in repository.list_customers(connection)
    ]


def create_quote(
    connection: sqlite3.Connection,
    customer_id: int,
    valid_until: str | None,
    notes: str | None,
) -> QuoteOut:
    customer = repository.get_customer(connection, customer_id)
    if customer is None:
        raise ClienteNaoEncontradoError(details={"customer_id": customer_id})

    price_table = repository.get_current_price_table(connection)
    if price_table is None:
        raise NenhumaTabelaVigenteError()

    quote_number = repository.next_quote_number(connection)
    quote_id = repository.insert_quote(
        connection,
        quote_number=quote_number,
        customer_id=customer_id,
        price_table_id=price_table["id"],
        valid_until=valid_until,
        notes=notes,
    )
    return get_quote(connection, quote_id)


def _require_draft_quote(connection: sqlite3.Connection, quote_id: int) -> str:
    status_value = repository.get_quote_status(connection, quote_id)
    if status_value is None:
        raise OrcamentoNaoEncontradoError(details={"id": quote_id})
    if status_value != "rascunho":
        raise StatusInvalidoError(details={"status": status_value})
    return status_value


# ---------------------------------------------------------------------------
# Itens — 14.11/14.12 (um único componente por item)
# ---------------------------------------------------------------------------


def _component_row_to_out(row: sqlite3.Row) -> QuoteItemComponentOut:
    return QuoteItemComponentOut(
        id=row["id"],
        component_variant_id=row["component_variant_id"],
        sku=row["sku"],
        frozen_unit_price=row["frozen_unit_price"],
        frozen_currency=row["frozen_currency"],
        frozen_at=row["frozen_at"],
    )


def _build_item_out(connection: sqlite3.Connection, item_row: sqlite3.Row) -> QuoteItemOut:
    component_rows = repository.get_item_components(connection, item_row["id"])
    components = [_component_row_to_out(row) for row in component_rows]

    subtotal = pricing.line_subtotal(
        dict(item_row),
        [dict(row) for row in component_rows],
    )

    return QuoteItemOut(
        id=item_row["id"],
        quote_id=item_row["quote_id"],
        label=item_row["label"],
        quantity=item_row["quantity"],
        discount_percent=item_row["discount_percent"],
        discount_amount=item_row["discount_amount"],
        discount_reason=item_row["discount_reason"],
        notes=item_row["notes"],
        components=components,
        line_subtotal=round(subtotal, 2),
    )


def add_item(
    connection: sqlite3.Connection, quote_id: int, payload: QuoteItemCreateIn
) -> QuoteItemOut:
    _require_draft_quote(connection, quote_id)

    if not repository.variant_exists(connection, payload.component_variant_id):
        raise VariacaoNaoEncontradaError(
            details={"component_variant_id": payload.component_variant_id}
        )

    price_table_id = repository.get_quote_price_table_id(connection, quote_id)
    price_row = repository.get_variant_price(
        connection, payload.component_variant_id, price_table_id
    )
    if price_row is None:
        raise ItemSemPrecoError(
            details={
                "component_variant_id": payload.component_variant_id,
                "price_table_id": price_table_id,
            }
        )
    if not price_row["sku_code"]:
        raise ItemSemSkuError(details={"component_variant_id": payload.component_variant_id})

    item_id = repository.insert_item(
        connection,
        quote_id=quote_id,
        product_id=payload.product_id,
        label=payload.label,
        quantity=payload.quantity,
        notes=payload.notes,
    )
    repository.insert_item_component(
        connection,
        quote_item_id=item_id,
        component_variant_id=payload.component_variant_id,
        sku_id=price_row["sku_id"],
        frozen_unit_price=price_row["amount"],
        frozen_currency=price_row["currency"],
        price_source_id=price_row["price_id"],
    )

    item_row = repository.get_item_row(connection, quote_id, item_id)
    return _build_item_out(connection, item_row)


def list_items(connection: sqlite3.Connection, quote_id: int) -> list[QuoteItemOut]:
    if not repository.quote_exists(connection, quote_id):
        raise OrcamentoNaoEncontradoError(details={"id": quote_id})
    item_rows = repository.list_items_with_components(connection, quote_id)
    return [_build_item_out(connection, row) for row in item_rows]


def get_item(connection: sqlite3.Connection, quote_id: int, item_id: int) -> QuoteItemOut:
    if not repository.quote_exists(connection, quote_id):
        raise OrcamentoNaoEncontradoError(details={"id": quote_id})
    item_row = repository.get_item_row(connection, quote_id, item_id)
    if item_row is None:
        raise ItemNaoEncontradoError(details={"id": item_id})
    return _build_item_out(connection, item_row)


def update_item(
    connection: sqlite3.Connection, quote_id: int, item_id: int, payload: QuoteItemPatchIn
) -> QuoteItemOut:
    _require_draft_quote(connection, quote_id)

    item_row = repository.get_item_row(connection, quote_id, item_id)
    if item_row is None:
        raise ItemNaoEncontradoError(details={"id": item_id})

    data = payload.model_dump(exclude_unset=True)

    if "quantity" in data and data["quantity"] is not None and data["quantity"] <= 0:
        raise QuantidadeInvalidaError(details={"quantity": data["quantity"]})

    has_percent = data.get("discount_percent") is not None
    has_amount = data.get("discount_amount") is not None
    if has_percent and has_amount:
        raise DescontoInvalidoError(
            details={"message": "Informe discount_percent OU discount_amount, não ambos."}
        )
    if has_percent and not (0 <= data["discount_percent"] <= 100):
        raise DescontoInvalidoError(details={"discount_percent": data["discount_percent"]})
    if has_amount and data["discount_amount"] < 0:
        raise DescontoInvalidoError(details={"discount_amount": data["discount_amount"]})

    has_reason = data.get("discount_reason") or item_row["discount_reason"]
    if (has_percent or has_amount) and not has_reason:
        raise DescontoSemJustificativaError()

    repository.update_item(connection, item_id, data)

    item_row = repository.get_item_row(connection, quote_id, item_id)
    return _build_item_out(connection, item_row)


# ---------------------------------------------------------------------------
# Status — mudança de etapa do ciclo de vida
# ---------------------------------------------------------------------------


def update_status(connection: sqlite3.Connection, quote_id: int, new_status: str) -> QuoteOut:
    current_status = repository.get_quote_status(connection, quote_id)
    if current_status is None:
        raise OrcamentoNaoEncontradoError(details={"id": quote_id})

    allowed = ALLOWED_STATUS_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise TransicaoInvalidaError(
            details={"from": current_status, "to": new_status, "allowed": sorted(allowed)}
        )

    repository.update_quote_status(connection, quote_id, new_status)
    return get_quote(connection, quote_id)


# ---------------------------------------------------------------------------
# Totais — 14.13
# ---------------------------------------------------------------------------


def _items_with_components(connection: sqlite3.Connection, quote_id: int) -> list[dict[str, Any]]:
    items = repository.list_items_with_components(connection, quote_id)
    return [
        {
            "item": dict(item_row),
            "components": [
                dict(row) for row in repository.get_item_components(connection, item_row["id"])
            ],
        }
        for item_row in items
    ]


def get_totals(connection: sqlite3.Connection, quote_id: int) -> QuoteTotalsOut:
    if not repository.quote_exists(connection, quote_id):
        raise OrcamentoNaoEncontradoError(details={"id": quote_id})

    entries = _items_with_components(connection, quote_id)
    totals = pricing.compute_totals(entries)

    return QuoteTotalsOut(
        quote_id=quote_id,
        is_snapshot=False,
        calculated_at=_now(),
        warnings=[QuoteTotalWarning(**w) for w in totals["warnings"]],
        **{k: v for k, v in totals.items() if k != "warnings"},
    )


def freeze_totals(connection: sqlite3.Connection, quote_id: int) -> QuoteTotalsOut:
    if not repository.quote_exists(connection, quote_id):
        raise OrcamentoNaoEncontradoError(details={"id": quote_id})

    entries = _items_with_components(connection, quote_id)
    if not entries:
        raise OrcamentoVazioError(details={"quote_id": quote_id})

    totals = pricing.compute_totals(entries)
    row = repository.upsert_quote_totals(
        connection,
        quote_id=quote_id,
        subtotal=totals["subtotal"],
        discount_percent=totals["discount_percent"],
        discount_amount=totals["discount_amount"],
        tax_amount=totals["tax_amount"],
        freight_amount=totals["freight_amount"],
        total=totals["total"],
        currency=totals["currency"],
    )

    return QuoteTotalsOut(
        quote_id=quote_id,
        subtotal=row["subtotal"],
        discount_percent=row["discount_percent"],
        discount_amount=row["discount_amount"],
        tax_amount=row["tax_amount"],
        freight_amount=row["freight_amount"],
        total=row["total"],
        currency=row["currency"],
        is_snapshot=True,
        calculated_at=row["calculated_at"],
        warnings=[QuoteTotalWarning(**w) for w in totals["warnings"]],
    )


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
