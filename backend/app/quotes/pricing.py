"""Cálculos de preço congelado e totais do orçamento (docs/06, 14.11/14.13; RN-08/15/16).

Mantido isolado da camada de service/repositório para permitir testes
unitários puros (docs/07, Fase 3 — "testes unitários das regras de
congelamento, isolados").
"""

from __future__ import annotations

from typing import Any


def component_total(components: list[dict[str, Any]]) -> float:
    """Soma de `frozen_unit_price * quantity` dos componentes de um item."""
    return sum(c["frozen_unit_price"] * c["quantity"] for c in components)


def item_discount(line_subtotal_raw: float, item: dict[str, Any]) -> float:
    """Valor de desconto da linha, a partir de `discount_percent` ou `discount_amount`."""
    if item.get("discount_percent") is not None:
        return line_subtotal_raw * item["discount_percent"] / 100
    if item.get("discount_amount") is not None:
        return item["discount_amount"]
    return 0.0


def line_subtotal(item: dict[str, Any], components: list[dict[str, Any]]) -> float:
    """Subtotal da linha (RN-08), já com o desconto da linha aplicado."""
    raw = component_total(components) * item["quantity"]
    return raw - item_discount(raw, item)


def compute_totals(items: list[dict[str, Any]], currency: str = "BRL") -> dict[str, Any]:
    """Totais do orçamento a partir das linhas com seus componentes.

    `items` é uma lista de dicts no formato
    ``{"item": {...quote_items...}, "components": [{...quote_item_components...}]}``.
    """
    subtotal = 0.0
    discount_amount = 0.0

    for entry in items:
        item = entry["item"]
        components = entry["components"]

        raw = component_total(components) * item["quantity"]
        subtotal += raw
        discount_amount += item_discount(raw, item)

    total = subtotal - discount_amount
    discount_percent = (discount_amount / subtotal * 100) if subtotal else 0.0

    warnings: list[dict[str, Any]] = []

    return {
        "subtotal": round(subtotal, 2),
        "discount_percent": round(discount_percent, 2),
        "discount_amount": round(discount_amount, 2),
        "tax_amount": 0.0,
        "freight_amount": 0.0,
        "total": round(total, 2),
        "currency": currency,
        "warnings": warnings,
    }
