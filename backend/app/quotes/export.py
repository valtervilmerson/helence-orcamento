"""Geração de PDF do orçamento (docs/06 §14.14; docs/04 Tela 9).

O PDF é montado a partir do snapshot congelado (`quote_totals` +
`quote_item_components`) — não recalcula preços. Distingue observações do
vendedor (`quote_items.notes`) de observações de catálogo/fabricante
(`business_rules`, RN-11).
"""

from __future__ import annotations

import sqlite3

import fitz

from app.quotes import pricing, repository

_PAGE_WIDTH = 595.0
_PAGE_HEIGHT = 842.0
_MARGIN = 50.0
_LINE_HEIGHT = 16.0


class _PdfWriter:
    """Escreve linhas de texto sequenciais, paginando quando necessário."""

    def __init__(self, doc: fitz.Document) -> None:
        self._doc = doc
        self._page = doc.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
        self._y = _MARGIN

    def _ensure_space(self) -> None:
        if self._y > _PAGE_HEIGHT - _MARGIN:
            self._page = self._doc.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
            self._y = _MARGIN

    def line(self, text: str, *, size: float = 10, bold: bool = False) -> None:
        self._ensure_space()
        fontname = "hebo" if bold else "helv"
        self._page.insert_text(
            (_MARGIN, self._y), text, fontsize=size, fontname=fontname
        )
        self._y += _LINE_HEIGHT * (size / 10)

    def spacer(self, height: float = _LINE_HEIGHT / 2) -> None:
        self._y += height


def generate_pdf(connection: sqlite3.Connection, quote_id: int) -> bytes:
    quote_row = repository.get_quote_row(connection, quote_id)
    item_rows = repository.list_items_with_components(connection, quote_id)
    totals_row = repository.get_quote_totals_row(connection, quote_id)
    catalog_observations = repository.get_catalog_observations_for_quote(connection, quote_id)

    doc = fitz.open()
    writer = _PdfWriter(doc)

    writer.line(f"Orçamento {quote_row['quote_number']}", size=16, bold=True)
    writer.line(f"Cliente: {quote_row['customer_name']}")
    writer.line(f"Data: {quote_row['created_at']}")
    if quote_row["valid_until"]:
        writer.line(f"Válido até: {quote_row['valid_until']}")
    writer.line(f"Tabela de preços: {quote_row['price_table_code']}")
    writer.spacer()

    writer.line("Itens", size=12, bold=True)
    writer.spacer()
    for item_row in item_rows:
        component_rows = repository.get_item_components(connection, item_row["id"])
        subtotal = pricing.line_subtotal(dict(item_row), [dict(row) for row in component_rows])

        writer.line(f"{item_row['label']} (qtd. {item_row['quantity']})", bold=True)
        for component_row in component_rows:
            writer.line(
                f"    SKU {component_row['sku']} — "
                f"{component_row['frozen_unit_price']:.2f} {component_row['frozen_currency']}"
            )
        if item_row["notes"]:
            writer.line(f"    Observação do vendedor: {item_row['notes']}")
        writer.line(f"    Subtotal da linha: {subtotal:.2f}")
        writer.spacer()

    writer.line("Totais", size=12, bold=True)
    writer.spacer()
    writer.line(f"Subtotal: {totals_row['subtotal']:.2f} {totals_row['currency']}")
    if totals_row["discount_amount"]:
        writer.line(f"Desconto: {totals_row['discount_amount']:.2f} {totals_row['currency']}")
    if totals_row["tax_amount"]:
        writer.line(f"Impostos: {totals_row['tax_amount']:.2f} {totals_row['currency']}")
    if totals_row["freight_amount"]:
        writer.line(f"Frete: {totals_row['freight_amount']:.2f} {totals_row['currency']}")
    writer.line(f"Total: {totals_row['total']:.2f} {totals_row['currency']}", bold=True)
    writer.spacer()

    if catalog_observations:
        writer.line("Observações do fabricante/catálogo", size=12, bold=True)
        writer.spacer()
        for observation in catalog_observations:
            writer.line(f"- {observation}")

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes
