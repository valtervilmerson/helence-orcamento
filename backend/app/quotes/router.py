"""Endpoints REST do ciclo de vida básico de orçamentos (docs/06, 14.10-14.13)."""

import sqlite3

from fastapi import APIRouter, Depends, status

from app.db.connection import get_connection
from app.quotes import service
from app.quotes.schemas import (
    CustomerSummary,
    QuoteCreateIn,
    QuoteItemComponentCreateIn,
    QuoteItemComponentSwapIn,
    QuoteItemComponentSwapOut,
    QuoteItemCreateIn,
    QuoteItemOut,
    QuoteItemPatchIn,
    QuoteOut,
    QuoteStatusPatchIn,
    QuoteTotalsOut,
)

router = APIRouter(prefix="/quotes", tags=["quotes"])
customers_router = APIRouter(tags=["quotes"])


def get_db() -> sqlite3.Connection:
    with get_connection() as connection:
        yield connection


@customers_router.get("/customers", response_model=list[CustomerSummary])
def list_customers(connection: sqlite3.Connection = Depends(get_db)) -> list[CustomerSummary]:
    return service.list_customers(connection)


@router.post("", response_model=QuoteOut, status_code=status.HTTP_201_CREATED)
def create_quote(
    payload: QuoteCreateIn, connection: sqlite3.Connection = Depends(get_db)
) -> QuoteOut:
    return service.create_quote(connection, payload.customer_id, payload.valid_until, payload.notes)


@router.get("", response_model=list[QuoteOut])
def list_quotes(connection: sqlite3.Connection = Depends(get_db)) -> list[QuoteOut]:
    return service.list_quotes(connection)


@router.get("/{quote_id}", response_model=QuoteOut)
def get_quote(quote_id: int, connection: sqlite3.Connection = Depends(get_db)) -> QuoteOut:
    return service.get_quote(connection, quote_id)


@router.patch("/{quote_id}", response_model=QuoteOut)
def update_quote_status(
    quote_id: int, payload: QuoteStatusPatchIn, connection: sqlite3.Connection = Depends(get_db)
) -> QuoteOut:
    return service.update_status(connection, quote_id, payload.status)


@router.post("/{quote_id}/items", response_model=QuoteItemOut, status_code=status.HTTP_201_CREATED)
def add_item(
    quote_id: int, payload: QuoteItemCreateIn, connection: sqlite3.Connection = Depends(get_db)
) -> QuoteItemOut:
    return service.add_item(connection, quote_id, payload)


@router.get("/{quote_id}/items", response_model=list[QuoteItemOut])
def list_items(
    quote_id: int, connection: sqlite3.Connection = Depends(get_db)
) -> list[QuoteItemOut]:
    return service.list_items(connection, quote_id)


@router.get("/{quote_id}/items/{item_id}", response_model=QuoteItemOut)
def get_item(
    quote_id: int, item_id: int, connection: sqlite3.Connection = Depends(get_db)
) -> QuoteItemOut:
    return service.get_item(connection, quote_id, item_id)


@router.post(
    "/{quote_id}/items/{item_id}/components",
    response_model=QuoteItemOut,
    status_code=status.HTTP_201_CREATED,
)
def add_component(
    quote_id: int,
    item_id: int,
    payload: QuoteItemComponentCreateIn,
    connection: sqlite3.Connection = Depends(get_db),
) -> QuoteItemOut:
    return service.add_component(connection, quote_id, item_id, payload)


@router.patch(
    "/{quote_id}/items/{item_id}/components/{component_id}",
    response_model=QuoteItemComponentSwapOut,
)
def update_item_component(
    quote_id: int,
    item_id: int,
    component_id: int,
    payload: QuoteItemComponentSwapIn,
    connection: sqlite3.Connection = Depends(get_db),
) -> QuoteItemComponentSwapOut:
    return service.update_item_component(connection, quote_id, item_id, component_id, payload)


@router.patch("/{quote_id}/items/{item_id}", response_model=QuoteItemOut)
def update_item(
    quote_id: int,
    item_id: int,
    payload: QuoteItemPatchIn,
    connection: sqlite3.Connection = Depends(get_db),
) -> QuoteItemOut:
    return service.update_item(connection, quote_id, item_id, payload)


@router.delete("/{quote_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_item(
    quote_id: int, item_id: int, connection: sqlite3.Connection = Depends(get_db)
) -> None:
    service.remove_item(connection, quote_id, item_id)


@router.delete("/{quote_id}/items/{item_id}/components/{component_id}", response_model=QuoteItemOut)
def remove_component(
    quote_id: int,
    item_id: int,
    component_id: int,
    connection: sqlite3.Connection = Depends(get_db),
) -> QuoteItemOut:
    return service.remove_component(connection, quote_id, item_id, component_id)


@router.get("/{quote_id}/totals", response_model=QuoteTotalsOut)
def get_totals(quote_id: int, connection: sqlite3.Connection = Depends(get_db)) -> QuoteTotalsOut:
    return service.get_totals(connection, quote_id)


@router.post("/{quote_id}/totals/freeze", response_model=QuoteTotalsOut)
def freeze_totals(
    quote_id: int, connection: sqlite3.Connection = Depends(get_db)
) -> QuoteTotalsOut:
    return service.freeze_totals(connection, quote_id)
