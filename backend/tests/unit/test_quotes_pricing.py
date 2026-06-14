"""Testes unitários de congelamento/totais (docs/07, Fase 3) — sem HTTP/banco."""

from app.quotes import pricing


def _component(price: float, quantity: int = 1) -> dict:
    return {
        "frozen_unit_price": price,
        "quantity": quantity,
    }


def test_line_subtotal_propagates_item_quantity() -> None:
    item = {"quantity": 2, "discount_percent": None, "discount_amount": None}
    components = [_component(493.80), _component(612.40)]

    assert pricing.line_subtotal(item, components) == 2212.40


def test_line_subtotal_applies_percent_discount() -> None:
    item = {"quantity": 3, "discount_percent": 5, "discount_amount": None}
    components = [_component(100.0)]

    # raw = 300; desconto 5% = 15; subtotal = 285
    assert pricing.line_subtotal(item, components) == 285.0


def test_line_subtotal_applies_fixed_discount() -> None:
    item = {"quantity": 1, "discount_percent": None, "discount_amount": 10.0}
    components = [_component(100.0)]

    assert pricing.line_subtotal(item, components) == 90.0


def test_compute_totals_sums_items_and_discounts() -> None:
    entries = [
        {
            "item": {"quantity": 1, "discount_percent": None, "discount_amount": None},
            "components": [_component(100.0)],
        },
        {
            "item": {"quantity": 1, "discount_percent": 10, "discount_amount": None},
            "components": [_component(200.0)],
        },
    ]

    totals = pricing.compute_totals(entries)

    assert totals["subtotal"] == 300.0
    assert totals["discount_amount"] == 20.0
    assert totals["total"] == 280.0
    assert totals["currency"] == "BRL"
    assert totals["warnings"] == []
