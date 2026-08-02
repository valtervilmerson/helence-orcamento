"""Geração do PDF comercial a partir do snapshot congelado do orçamento.

O documento é deliberadamente uma visão para o cliente: não expõe SKU,
markup, custo, tabela de preço, confiança de importação ou auditoria. Os
totais usados vêm exclusivamente de ``quote_totals``; os preços por linha são
distribuídos proporcionalmente a partir desse snapshot, sem reler a margem
global atual (RN-16).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

import fitz

from app.quotes import repository

_PAGE_WIDTH = 595.0
_PAGE_HEIGHT = 842.0
_LEFT = 45.0
_RIGHT = _PAGE_WIDTH - _LEFT
_BOTTOM = _PAGE_HEIGHT - 48.0

_GREEN = (23 / 255, 55 / 255, 42 / 255)
_GREEN_LIGHT = (241 / 255, 247 / 255, 243 / 255)
_GOLD = (233 / 255, 201 / 255, 122 / 255)
_INK = (28 / 255, 33 / 255, 30 / 255)
_MUTED = (110 / 255, 120 / 255, 115 / 255)
_LINE = (227 / 255, 225 / 255, 218 / 255)


def _currency(value: float, currency: str) -> str:
    number = f"{abs(value):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    prefix = "− " if value < 0 else ""
    return f"{prefix}R$ {number}" if currency == "BRL" else f"{prefix}{number} {currency}"


def _date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%d/%m/%Y")
    except ValueError:
        return value


def _commercial_description(components: list[dict[str, Any]]) -> str:
    parts = [component.get("description") or component.get("descriptor") or component.get("component") for component in components]
    text = " · ".join(part for part in parts if part)
    if not text:
        return "Composição personalizada Helence."
    return f"{text[:1].upper()}{text[1:]}."


def _line_values(items: list[sqlite3.Row], connection: sqlite3.Connection, subtotal: float) -> list[dict[str, Any]]:
    """Distribui o subtotal congelado entre linhas sem ler markup atual."""
    prepared: list[dict[str, Any]] = []
    raw_total = 0.0
    for item in items:
        components = [dict(row) for row in repository.get_item_components(connection, item["id"])]
        raw = sum(float(component["frozen_unit_price"]) * float(component["quantity"]) for component in components) * item["quantity"]
        raw_total += raw
        prepared.append({"item": dict(item), "components": components, "raw": raw})
    scale = subtotal / raw_total if raw_total else 0.0
    for entry in prepared:
        item = entry["item"]
        line_before_discount = entry["raw"] * scale
        if item.get("discount_percent") is not None:
            discount = line_before_discount * float(item["discount_percent"]) / 100
        elif item.get("discount_amount") is not None:
            discount = float(item["discount_amount"])
        else:
            discount = 0.0
        entry["line_total"] = max(0.0, line_before_discount - discount)
        entry["unit_value"] = entry["line_total"] / item["quantity"] if item["quantity"] else 0.0
    return prepared


class _ProposalPdf:
    def __init__(self, quote_number: str, issued_at: str) -> None:
        self.doc = fitz.open()
        self.quote_number = quote_number
        self.issued_at = issued_at
        self.page = self.doc.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
        self.y = _LEFT
        self._page_header()

    def _page_header(self) -> None:
        page = self.page
        page.draw_rect(fitz.Rect(_LEFT, self.y, _LEFT + 40, self.y + 40), color=None, fill=_GREEN)
        page.insert_text((_LEFT + 13, self.y + 27), "h", fontsize=22, fontname="tiro", color=_GOLD)
        page.insert_text((_LEFT + 52, self.y + 18), "Helence Mobiliário", fontsize=19, fontname="tibo", color=_GREEN)
        page.insert_text((_LEFT + 52, self.y + 34), "Mesas de reunião sob medida · desde 1998", fontsize=8.8, fontname="helv", color=_MUTED)
        page.insert_textbox(fitz.Rect(400, self.y, _RIGHT, self.y + 14), "PROPOSTA", fontsize=8.5, fontname="hebo", color=_MUTED, align=fitz.TEXT_ALIGN_RIGHT)
        page.insert_textbox(fitz.Rect(400, self.y + 13, _RIGHT, self.y + 31), self.quote_number, fontsize=13, fontname="hebo", color=_GREEN, align=fitz.TEXT_ALIGN_RIGHT)
        page.insert_textbox(fitz.Rect(400, self.y + 30, _RIGHT, self.y + 44), f"Emitida em {self.issued_at}", fontsize=8.5, fontname="helv", color=_MUTED, align=fitz.TEXT_ALIGN_RIGHT)
        self.y += 58
        page.draw_line(fitz.Point(_LEFT, self.y), fitz.Point(_RIGHT, self.y), color=_GREEN, width=1.5)
        self.y += 20

    def _new_page(self) -> None:
        self.page = self.doc.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
        self.y = _LEFT
        self._page_header()

    def _space(self, height: float) -> None:
        if self.y + height > _BOTTOM:
            self._new_page()

    def text(self, rect: fitz.Rect, value: str, *, size: float, font: str = "helv", color: tuple[float, float, float] = _INK, align: int = fitz.TEXT_ALIGN_LEFT) -> None:
        self.page.insert_textbox(rect, value, fontsize=size, fontname=font, color=color, align=align, lineheight=1.3)

    def metadata(self, customer: sqlite3.Row, quote: sqlite3.Row, payment: str) -> None:
        self._space(98)
        left = fitz.Rect(_LEFT, self.y, 294, self.y + 82)
        right = fitz.Rect(324, self.y, _RIGHT, self.y + 82)
        self.text(fitz.Rect(left.x0, left.y0, left.x1, left.y0 + 12), "PREPARADA PARA", size=8.5, font="hebo", color=_GREEN)
        self.text(fitz.Rect(left.x0, left.y0 + 17, left.x1, left.y0 + 40), quote["customer_name"], size=16, font="tibo", color=_GREEN)
        contact = " · ".join(value for value in (customer["document"], customer["email"], customer["phone"]) if value)
        details = "\n".join(value for value in (contact, customer["address"]) if value) or "Proposta comercial preparada especialmente para este projeto."
        self.text(fitz.Rect(left.x0, left.y0 + 44, left.x1, left.y1), details, size=8.8, color=_MUTED)
        self.text(fitz.Rect(right.x0, right.y0, right.x1, right.y0 + 12), "CONDIÇÕES", size=8.5, font="hebo", color=_GREEN)
        validity = _date(quote["valid_until"]) or "a definir"
        consultant = quote["created_by_name"] or "Equipe comercial Helence"
        self.text(fitz.Rect(right.x0, right.y0 + 18, right.x1, right.y1), f"Validade: {validity}\nPagamento: {payment}\nConsultora: {consultant}", size=8.8, color=_INK)
        self.y += 92
        self.page.draw_line(fitz.Point(_LEFT, self.y), fitz.Point(_RIGHT, self.y), color=_LINE, width=.7)
        self.y += 22

    def item_header(self) -> None:
        self._space(30)
        self.text(fitz.Rect(_LEFT, self.y, _RIGHT, self.y + 12), "ITENS DA PROPOSTA", size=8.5, font="hebo", color=_GREEN)
        self.y += 18
        self.page.draw_line(fitz.Point(_LEFT, self.y), fitz.Point(_RIGHT, self.y), color=_GREEN, width=.8)
        self.text(fitz.Rect(_LEFT, self.y + 4, 325, self.y + 18), "DESCRIÇÃO", size=8, font="hebo", color=_GREEN)
        self.text(fitz.Rect(330, self.y + 4, 375, self.y + 18), "QTD", size=8, font="hebo", color=_GREEN, align=fitz.TEXT_ALIGN_RIGHT)
        self.text(fitz.Rect(380, self.y + 4, 462, self.y + 18), "UNITÁRIO", size=8, font="hebo", color=_GREEN, align=fitz.TEXT_ALIGN_RIGHT)
        self.text(fitz.Rect(468, self.y + 4, _RIGHT, self.y + 18), "TOTAL", size=8, font="hebo", color=_GREEN, align=fitz.TEXT_ALIGN_RIGHT)
        self.y += 23

    def item(self, entry: dict[str, Any], currency: str) -> None:
        item = entry["item"]
        description = _commercial_description(entry["components"])
        lines = max(1, len(description) // 70 + 1)
        height = 28 + lines * 11
        self._space(height + 8)
        self.text(fitz.Rect(_LEFT, self.y, 318, self.y + 18), item["label"], size=11.5, font="tibo", color=_GREEN)
        self.text(fitz.Rect(_LEFT, self.y + 16, 318, self.y + height), description, size=8.5, color=_MUTED)
        self.text(fitz.Rect(330, self.y + 5, 375, self.y + 20), f"{item['quantity']:g}", size=9.5, align=fitz.TEXT_ALIGN_RIGHT)
        self.text(fitz.Rect(380, self.y + 5, 462, self.y + 20), _currency(entry["unit_value"], currency), size=9.2, align=fitz.TEXT_ALIGN_RIGHT)
        self.text(fitz.Rect(468, self.y + 5, _RIGHT, self.y + 20), _currency(entry["line_total"], currency), size=9.2, font="hebo", color=_GREEN, align=fitz.TEXT_ALIGN_RIGHT)
        self.y += height
        self.page.draw_line(fitz.Point(_LEFT, self.y), fitz.Point(_RIGHT, self.y), color=_LINE, width=.6)
        self.y += 8

    def totals(self, totals: sqlite3.Row, quote: sqlite3.Row) -> None:
        self._space(132)
        x0, width = 308, 242
        subtotal = float(totals["subtotal"])
        item_discount = float(totals["item_discount_amount"] or 0)
        quote_discount = float(totals["quote_discount_amount"] or totals["discount_amount"] or 0) - item_discount
        discount = item_discount + max(0.0, quote_discount)
        rows = [("Subtotal", subtotal, _INK)]
        if discount > 0:
            rows.append(("Desconto comercial", -discount, _GREEN))
        for index, (label, value, color) in enumerate(rows):
            y = self.y + index * 19
            self.text(fitz.Rect(x0, y, x0 + 125, y + 15), label, size=9.5, color=color)
            self.text(fitz.Rect(x0 + 125, y, _RIGHT, y + 15), _currency(value, totals["currency"]), size=9.5, font="hebo", color=color, align=fitz.TEXT_ALIGN_RIGHT)
        total_y = self.y + len(rows) * 19 + 4
        self.page.draw_line(fitz.Point(x0, total_y), fitz.Point(_RIGHT, total_y), color=_GREEN, width=.9)
        self.text(fitz.Rect(x0, total_y + 8, x0 + 130, total_y + 30), "Total da proposta", size=13, font="tibo", color=_GREEN)
        self.text(fitz.Rect(x0 + 120, total_y + 5, _RIGHT, total_y + 33), _currency(float(totals["total"]), totals["currency"]), size=18, font="tibo", color=_GREEN, align=fitz.TEXT_ALIGN_RIGHT)
        self.y = total_y + 42
        count = int(totals["installment_count"] or 1)
        if count > 1:
            self._space(48)
            box = fitz.Rect(x0, self.y, _RIGHT, self.y + 47)
            self.page.draw_rect(box, color=None, fill=_GREEN_LIGHT)
            entry = float(quote["entrada_amount"] or 0)
            if quote["entrada_percent"]:
                entry = float(totals["installment_total"] or totals["total"]) * float(quote["entrada_percent"]) / 100
            prefix = f"Entrada de {_currency(entry, totals['currency'])} e mais " if entry > 0 else ""
            interest = "sem juros" if not totals["installment_interest_amount"] else "com juros"
            self.text(fitz.Rect(x0 + 12, self.y + 9, _RIGHT - 12, self.y + 38), f"{prefix}{count} × {_currency(float(totals['installment_value']), totals['currency'])}\n{interest} · primeira parcela 30 dias após a entrega", size=8.8, font="hebo", color=_GREEN)
            self.y += 58

    def footer(self, validity: str | None) -> None:
        self._space(82)
        self.y = max(self.y + 20, _BOTTOM - 62)
        self.page.draw_line(fitz.Point(_LEFT, self.y), fitz.Point(_RIGHT, self.y), color=_LINE, width=.7)
        self.text(fitz.Rect(_LEFT, self.y + 9, 330, self.y + 40), f"Valores em reais, impostos inclusos. Instalação em Curitiba e região metropolitana inclusa. Esta proposta perde a validade em {validity or 'data a definir'}.", size=7.8, color=_MUTED)
        self.text(fitz.Rect(355, self.y + 12, _RIGHT, self.y + 40), "_______________________________\nAceite do cliente · data e assinatura", size=7.8, color=_MUTED, align=fitz.TEXT_ALIGN_CENTER)

    def close(self) -> bytes:
        pages = len(self.doc)
        for index, page in enumerate(self.doc):
            page.insert_textbox(fitz.Rect(_LEFT, _PAGE_HEIGHT - 28, _RIGHT, _PAGE_HEIGHT - 15), f"Página {index + 1} de {pages}", fontsize=7.5, fontname="helv", color=_MUTED, align=fitz.TEXT_ALIGN_RIGHT)
        result = self.doc.tobytes()
        self.doc.close()
        return result


def generate_pdf(connection: sqlite3.Connection, quote_id: int) -> bytes:
    quote = repository.get_quote_row(connection, quote_id)
    customer = repository.get_customer(connection, quote["customer_id"])
    totals = repository.get_quote_totals_row(connection, quote_id)
    if customer is None or totals is None:
        raise ValueError("Dados congelados do orçamento não encontrados.")
    installment_count = int(totals["installment_count"] or 1)
    payment = "Pagamento à vista."
    if installment_count > 1:
        payment = f"{installment_count} parcelas de {_currency(float(totals['installment_value']), totals['currency'])}."
    writer = _ProposalPdf(quote["quote_number"], _date(quote["created_at"]) or datetime.now().strftime("%d/%m/%Y"))
    writer.metadata(customer, quote, payment)
    writer.item_header()
    for entry in _line_values(repository.list_items_with_components(connection, quote_id), connection, float(totals["subtotal"])):
        writer.item(entry, totals["currency"])
    writer.totals(totals, quote)
    writer.footer(_date(quote["valid_until"]))
    return writer.close()
