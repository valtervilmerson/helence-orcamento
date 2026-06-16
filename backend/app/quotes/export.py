"""Geração de PDF do orçamento (docs/06 §14.14; docs/04 Tela 9).

O PDF é montado a partir do snapshot congelado (`quote_totals` +
`quote_item_components`) — não recalcula preços. Distingue observações do
vendedor (`quote_items.notes`) de observações de catálogo/fabricante
(`business_rules`, RN-11).

Layout "executivo": cabeçalho com a logo da empresa em todas as páginas,
dados do cliente, tabela de itens com cabeçalho destacado e caixa de totais
com o valor final em evidência.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import fitz

from app.quotes import pricing, repository

_PAGE_WIDTH = 595.0
_PAGE_HEIGHT = 842.0
_MARGIN = 50.0
_CONTENT_WIDTH = _PAGE_WIDTH - 2 * _MARGIN
_TABLE_RIGHT = _MARGIN + _CONTENT_WIDTH

_NAVY = (0.13, 0.20, 0.32)
_ACCENT = (0.72, 0.45, 0.18)
_GRAY = (0.45, 0.45, 0.45)
_LIGHT_GRAY = (0.90, 0.90, 0.92)
_WHITE = (1.0, 1.0, 1.0)

_LOGO_PATH = Path(__file__).resolve().parent / "assets" / "logo.png"
_LOGO_RATIO = 89 / 359  # altura / largura da imagem original

_HEADER_HEIGHT = 60.0
_FOOTER_HEIGHT = 26.0

# Colunas da tabela de itens.
_COL_DESC = _MARGIN
_COL_QTY = _MARGIN + 275
_COL_UNIT = _COL_QTY + 40
_COL_SUBTOTAL = _COL_UNIT + 85


def _format_currency(value: float, currency: str) -> str:
    sign = "-" if value < 0 else ""
    text = f"{abs(value):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    if currency == "BRL":
        return f"{sign}R$ {text}"
    return f"{sign}{text} {currency}"


def _wrap_text(text: str, fontsize: float, fontname: str, max_width: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if fitz.get_text_length(candidate, fontname=fontname, fontsize=fontsize) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    lines.append(current)
    return lines


class _PdfWriter:
    """Monta o PDF do orçamento com cabeçalho/rodapé recorrentes e tabela de itens."""

    def __init__(self, doc: fitz.Document, *, quote_number: str, generated_at: str) -> None:
        self._doc = doc
        self._quote_number = quote_number
        self._generated_at = generated_at
        self._table_header_pending = False
        self._page = self._new_page()

    # -- páginas -------------------------------------------------------

    def _new_page(self) -> fitz.Page:
        page = self._doc.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
        self._draw_header(page)
        self._y = _MARGIN + _HEADER_HEIGHT
        return page

    def _draw_header(self, page: fitz.Page) -> None:
        if _LOGO_PATH.exists():
            logo_width = 110.0
            logo_height = logo_width * _LOGO_RATIO
            logo_rect = fitz.Rect(
                _MARGIN, _MARGIN - 8, _MARGIN + logo_width, _MARGIN - 8 + logo_height
            )
            page.insert_image(logo_rect, filename=str(_LOGO_PATH))

        title_rect = fitz.Rect(_MARGIN, _MARGIN - 10, _TABLE_RIGHT, _MARGIN + 16)
        page.insert_textbox(
            title_rect,
            f"Orçamento {self._quote_number}",
            fontsize=14,
            fontname="hebo",
            color=_NAVY,
            align=fitz.TEXT_ALIGN_RIGHT,
        )
        subtitle_rect = fitz.Rect(_MARGIN, _MARGIN + 12, _TABLE_RIGHT, _MARGIN + 28)
        page.insert_textbox(
            subtitle_rect,
            f"Gerado em {self._generated_at}",
            fontsize=9,
            fontname="helv",
            color=_GRAY,
            align=fitz.TEXT_ALIGN_RIGHT,
        )

        line_y = _MARGIN + _HEADER_HEIGHT - 12
        page.draw_line(
            fitz.Point(_MARGIN, line_y),
            fitz.Point(_TABLE_RIGHT, line_y),
            color=_ACCENT,
            width=1.5,
        )

    def _ensure_space(self, height: float) -> None:
        if self._y + height > _PAGE_HEIGHT - _MARGIN - _FOOTER_HEIGHT:
            self._page = self._new_page()
            if self._table_header_pending:
                self.table_header()

    # -- texto simples ---------------------------------------------------

    def line(
        self,
        text: str,
        *,
        size: float = 10,
        bold: bool = False,
        color: tuple[float, float, float] = (0, 0, 0),
        indent: float = 0.0,
    ) -> None:
        self._ensure_space(14.0 * (size / 10))
        fontname = "hebo" if bold else "helv"
        self._page.insert_text(
            (_MARGIN + indent, self._y + size), text, fontsize=size, fontname=fontname, color=color
        )
        self._y += 14.0 * (size / 10)

    def spacer(self, height: float = 8.0) -> None:
        self._y += height

    def section_title(self, text: str) -> None:
        self._ensure_space(24.0)
        self._page.insert_text(
            (_MARGIN, self._y + 12), text, fontsize=12, fontname="hebo", color=_NAVY
        )
        self._y += 16.0
        self._page.draw_line(
            fitz.Point(_MARGIN, self._y),
            fitz.Point(_TABLE_RIGHT, self._y),
            color=_LIGHT_GRAY,
            width=0.75,
        )
        self._y += 10.0

    # -- tabela de itens --------------------------------------------------

    def table_header(self) -> None:
        self._table_header_pending = True
        self._ensure_space(20.0)
        header_rect = fitz.Rect(_MARGIN, self._y, _TABLE_RIGHT, self._y + 18)
        self._page.draw_rect(header_rect, color=None, fill=_NAVY)
        self._page.insert_text(
            (_COL_DESC + 4, self._y + 13), "Descrição", fontsize=9, fontname="hebo", color=_WHITE
        )
        self._page.insert_textbox(
            fitz.Rect(_COL_QTY, self._y, _COL_UNIT, self._y + 18),
            "Qtd",
            fontsize=9,
            fontname="hebo",
            color=_WHITE,
            align=fitz.TEXT_ALIGN_CENTER,
        )
        self._page.insert_textbox(
            fitz.Rect(_COL_UNIT, self._y, _COL_SUBTOTAL - 4, self._y + 18),
            "Valor unit.",
            fontsize=9,
            fontname="hebo",
            color=_WHITE,
            align=fitz.TEXT_ALIGN_RIGHT,
        )
        self._page.insert_textbox(
            fitz.Rect(_COL_SUBTOTAL, self._y, _TABLE_RIGHT - 4, self._y + 18),
            "Subtotal",
            fontsize=9,
            fontname="hebo",
            color=_WHITE,
            align=fitz.TEXT_ALIGN_RIGHT,
        )
        self._y += 22.0

    def item_row(
        self,
        description: str,
        quantity: float,
        unit_value: float | None,
        subtotal: float,
        currency: str,
    ) -> None:
        desc_lines = _wrap_text(description, 10, "hebo", _COL_QTY - _COL_DESC - 6)
        row_height = max(18.0, 14.0 * len(desc_lines))
        self._ensure_space(row_height)

        for index, desc_line in enumerate(desc_lines):
            self._page.insert_text(
                (_COL_DESC, self._y + 11 + 14 * index),
                desc_line,
                fontsize=10,
                fontname="hebo",
                color=_NAVY,
            )

        cell_rect = fitz.Rect(_COL_QTY, self._y, _COL_UNIT, self._y + 16)
        self._page.insert_textbox(
            cell_rect, f"{quantity:g}", fontsize=10, fontname="helv", align=fitz.TEXT_ALIGN_CENTER
        )
        unit_text = _format_currency(unit_value, currency) if unit_value is not None else "—"
        self._page.insert_textbox(
            fitz.Rect(_COL_UNIT, self._y, _COL_SUBTOTAL - 4, self._y + 16),
            unit_text,
            fontsize=10,
            fontname="helv",
            align=fitz.TEXT_ALIGN_RIGHT,
        )
        self._page.insert_textbox(
            fitz.Rect(_COL_SUBTOTAL, self._y, _TABLE_RIGHT - 4, self._y + 16),
            _format_currency(subtotal, currency),
            fontsize=10,
            fontname="hebo",
            color=_NAVY,
            align=fitz.TEXT_ALIGN_RIGHT,
        )
        self._y += row_height + 4.0

    def row_separator(self) -> None:
        self._ensure_space(6.0)
        self._page.draw_line(
            fitz.Point(_MARGIN, self._y),
            fitz.Point(_TABLE_RIGHT, self._y),
            color=_LIGHT_GRAY,
            width=0.5,
        )
        self._y += 8.0

    # -- caixa de totais ---------------------------------------------------

    def totals_box(self, rows: list[tuple[str, float, str, bool]]) -> None:
        box_width = 220.0
        box_x0 = _TABLE_RIGHT - box_width
        row_height = 20.0
        box_height = row_height * len(rows)
        self._ensure_space(box_height + 6.0)

        self._page.draw_rect(
            fitz.Rect(box_x0, self._y, _TABLE_RIGHT, self._y + box_height),
            color=_LIGHT_GRAY,
            fill=_WHITE,
            width=0.75,
        )
        for index, (label, value, currency, is_total) in enumerate(rows):
            row_y0 = self._y + row_height * index
            row_y1 = row_y0 + row_height
            if is_total:
                self._page.draw_rect(
                    fitz.Rect(box_x0, row_y0, _TABLE_RIGHT, row_y1), color=None, fill=_NAVY
                )
                color = _WHITE
                fontname = "hebo"
            else:
                color = (0.0, 0.0, 0.0)
                fontname = "helv"
            self._page.insert_textbox(
                fitz.Rect(box_x0 + 10, row_y0, box_x0 + 120, row_y1),
                label,
                fontsize=10,
                fontname=fontname,
                color=color,
                align=fitz.TEXT_ALIGN_LEFT,
            )
            self._page.insert_textbox(
                fitz.Rect(box_x0 + 110, row_y0, _TABLE_RIGHT - 10, row_y1),
                _format_currency(value, currency),
                fontsize=10,
                fontname=fontname,
                color=color,
                align=fitz.TEXT_ALIGN_RIGHT,
            )
        self._y += box_height

    # -- finalização ---------------------------------------------------

    def finalize(self) -> None:
        total_pages = len(self._doc)
        for index in range(total_pages):
            page = self._doc[index]
            footer_y = _PAGE_HEIGHT - _MARGIN + 6
            page.draw_line(
                fitz.Point(_MARGIN, footer_y - 8),
                fitz.Point(_TABLE_RIGHT, footer_y - 8),
                color=_LIGHT_GRAY,
                width=0.75,
            )
            page.insert_text(
                (_MARGIN, footer_y + 4),
                "Helence Móveis Corporativos e Planejados",
                fontsize=8,
                fontname="helv",
                color=_GRAY,
            )
            page.insert_textbox(
                fitz.Rect(_MARGIN, footer_y, _TABLE_RIGHT, footer_y + 16),
                f"Página {index + 1} de {total_pages}",
                fontsize=8,
                fontname="helv",
                color=_GRAY,
                align=fitz.TEXT_ALIGN_RIGHT,
            )


def generate_pdf(connection: sqlite3.Connection, quote_id: int) -> bytes:
    quote_row = repository.get_quote_row(connection, quote_id)
    customer_row = repository.get_customer(connection, quote_row["customer_id"])
    item_rows = repository.list_items_with_components(connection, quote_id)
    totals_row = repository.get_quote_totals_row(connection, quote_id)
    catalog_observations = repository.get_catalog_observations_for_quote(connection, quote_id)
    currency = totals_row["currency"] if totals_row else "BRL"

    doc = fitz.open()
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    writer = _PdfWriter(doc, quote_number=quote_row["quote_number"], generated_at=generated_at)

    # Dados do cliente
    writer.section_title("Dados do cliente")
    writer.line(quote_row["customer_name"], size=11, bold=True)
    if customer_row["document"]:
        writer.line(f"CNPJ/CPF: {customer_row['document']}")
    contact_parts = [part for part in (customer_row["email"], customer_row["phone"]) if part]
    if contact_parts:
        writer.line("  •  ".join(contact_parts))
    if customer_row["address"]:
        writer.line(customer_row["address"])
    writer.spacer(4)

    info_parts = [f"Data: {quote_row['created_at']}"]
    if quote_row["valid_until"]:
        info_parts.append(f"Válido até: {quote_row['valid_until']}")
    if quote_row["created_by_name"]:
        info_parts.append(f"Vendedor: {quote_row['created_by_name']}")
    writer.line("   |   ".join(info_parts), size=9, color=_GRAY)
    writer.spacer(14)

    # Itens
    writer.section_title("Itens do orçamento")
    writer.table_header()
    for item_row in item_rows:
        component_rows = [
            dict(row) for row in repository.get_item_components(connection, item_row["id"])
        ]
        item_dict = dict(item_row)
        is_composite = len(component_rows) > 1
        unit_value = pricing.component_total(component_rows)
        subtotal = pricing.line_subtotal(item_dict, component_rows)

        label = item_row["label"]
        if is_composite:
            label = f"[Composto] {label}"
        writer.item_row(label, item_row["quantity"], unit_value, subtotal, currency)
        for idx, component_row in enumerate(component_rows):
            if component_row["sku"]:
                price_text = _format_currency(
                    component_row["frozen_unit_price"], component_row["frozen_currency"]
                )
                prefix = "BASE — " if (is_composite and idx == 0) else ""
                writer.line(
                    f"{prefix}SKU {component_row['sku']} — {price_text} × {component_row['quantity']:g}",
                    size=8.5,
                    color=_GRAY,
                    indent=10,
                )
        if item_dict.get("discount_reason"):
            writer.line(
                f"Desconto: {item_dict['discount_reason']}", size=8.5, color=_GRAY, indent=10
            )
        if item_row["notes"]:
            writer.line(f"Observação: {item_row['notes']}", size=8.5, color=_GRAY, indent=10)
        if item_dict.get("composition_justification"):
            writer.line(
                f"Justificativa de composição: {item_dict['composition_justification']}",
                size=8.5,
                color=_GRAY,
                indent=10,
            )
        writer.row_separator()
    writer.spacer(10)

    # Totais
    totals_rows: list[tuple[str, float, str, bool]] = [
        ("Subtotal", totals_row["subtotal"], currency, False)
    ]
    if totals_row["discount_amount"]:
        totals_rows.append(("Desconto", -totals_row["discount_amount"], currency, False))
    if totals_row["tax_amount"]:
        totals_rows.append(("Impostos", totals_row["tax_amount"], currency, False))
    if totals_row["freight_amount"]:
        totals_rows.append(("Frete", totals_row["freight_amount"], currency, False))
    totals_rows.append(("Total", totals_row["total"], currency, True))
    writer.totals_box(totals_rows)

    if catalog_observations:
        writer.spacer(14)
        writer.section_title("Observações do fabricante/catálogo")
        for observation in catalog_observations:
            writer.line(f"•  {observation}", size=9, color=_GRAY)

    writer.finalize()
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes
