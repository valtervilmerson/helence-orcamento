"""Cálculos de preço congelado e totais do orçamento (docs/06, 14.11/14.13; RN-08/15/16).

Mantido isolado da camada de service/repositório para permitir testes
unitários puros (docs/07, Fase 3 — "testes unitários das regras de
congelamento, isolados").
"""

from __future__ import annotations

from typing import Any


def component_total(components: list[dict[str, Any]], markup_factor: float = 1.0) -> float:
    """Soma de `frozen_unit_price * markup_factor * quantity` dos componentes de um item."""
    return sum(c["frozen_unit_price"] * markup_factor * c["quantity"] for c in components)


def item_discount(line_subtotal_raw: float, item: dict[str, Any]) -> float:
    """Valor de desconto da linha, a partir de `discount_percent` ou `discount_amount`."""
    if item.get("discount_percent") is not None:
        return line_subtotal_raw * item["discount_percent"] / 100
    if item.get("discount_amount") is not None:
        return float(item["discount_amount"])
    return 0.0


def line_subtotal(
    item: dict[str, Any], components: list[dict[str, Any]], markup_factor: float = 1.0
) -> float:
    """Subtotal da linha (RN-08), já com o desconto da linha aplicado."""
    raw = component_total(components, markup_factor) * item["quantity"]
    return raw - item_discount(raw, item)


def compute_totals(
    items: list[dict[str, Any]],
    currency: str = "BRL",
    markup_percent: float = 0.0,
    quote_discount_percent: float | None = None,
    quote_discount_amount: float | None = None,
) -> dict[str, Any]:
    """Totais do orçamento.

    `items` é uma lista de dicts no formato
    ``{"item": {...quote_items...}, "components": [{...quote_item_components...}]}``.

    O `markup_percent` é aplicado sobre cada `frozen_unit_price` e não é
    exibido no PDF ao cliente final. Os descontos são aplicados em cascata:
    primeiro por linha (item), depois no total do orçamento.
    """
    markup_factor = 1.0 + (markup_percent or 0.0) / 100.0
    raw_total = 0.0
    item_discount_total = 0.0

    for entry in items:
        item = entry["item"]
        components = entry["components"]
        raw = component_total(components, markup_factor) * item["quantity"]
        raw_total += raw
        item_discount_total += item_discount(raw, item)

    post_item = raw_total - item_discount_total

    if quote_discount_percent is not None:
        quote_disc = post_item * quote_discount_percent / 100.0
    elif quote_discount_amount is not None:
        quote_disc = float(quote_discount_amount)
    else:
        quote_disc = 0.0

    total_discount = item_discount_total + quote_disc
    total = raw_total - total_discount
    combined_pct = (total_discount / raw_total * 100.0) if raw_total else 0.0

    warnings: list[dict[str, Any]] = []

    return {
        "subtotal": round(raw_total, 2),
        "item_discount_amount": round(item_discount_total, 2),
        "quote_discount_amount": round(quote_disc, 2),
        "discount_percent": round(combined_pct, 2),
        "discount_amount": round(total_discount, 2),
        "tax_amount": 0.0,
        "freight_amount": 0.0,
        "total": round(total, 2),
        "currency": currency,
        "warnings": warnings,
    }
