"""Acesso a dados do ciclo de vida básico de orçamentos (docs/06, 14.10-14.13)."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any


def get_current_price_table(connection: sqlite3.Connection) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT id, code, status FROM price_tables WHERE status = 'vigente' LIMIT 1"
    ).fetchone()


def get_price_table(connection: sqlite3.Connection, price_table_id: int) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT id, code, status FROM price_tables WHERE id = ?", (price_table_id,)
    ).fetchone()


def get_customer(connection: sqlite3.Connection, customer_id: int) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT id, name FROM customers WHERE id = ?", (customer_id,)
    ).fetchone()


def list_customers(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return connection.execute("SELECT id, name FROM customers ORDER BY name").fetchall()


def next_quote_number(connection: sqlite3.Connection) -> str:
    year = datetime.now().year
    row = connection.execute(
        "SELECT COUNT(*) AS n FROM quotes WHERE quote_number LIKE ?", (f"ORC-{year}-%",)
    ).fetchone()
    sequence = row["n"] + 1
    return f"ORC-{year}-{sequence:04d}"


def insert_quote(
    connection: sqlite3.Connection,
    *,
    quote_number: str,
    customer_id: int,
    price_table_id: int,
    valid_until: str | None,
    notes: str | None,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO quotes (quote_number, customer_id, price_table_id, status, valid_until, notes)
        VALUES (?, ?, ?, 'rascunho', ?, ?)
        """,
        (quote_number, customer_id, price_table_id, valid_until, notes),
    )
    connection.commit()
    return int(cursor.lastrowid)


_QUOTE_BASE = """
    SELECT
        q.id AS id,
        q.quote_number AS quote_number,
        q.status AS status,
        q.created_at AS created_at,
        q.valid_until AS valid_until,
        q.notes AS notes,
        c.id AS customer_id,
        c.name AS customer_name,
        pt.id AS price_table_id,
        pt.code AS price_table_code,
        pt.status AS price_table_status,
        u.id AS created_by_id,
        u.name AS created_by_name
    FROM quotes q
    JOIN customers c ON c.id = q.customer_id
    JOIN price_tables pt ON pt.id = q.price_table_id
    LEFT JOIN users u ON u.id = q.created_by_user_id
"""


def get_quote_row(connection: sqlite3.Connection, quote_id: int) -> sqlite3.Row | None:
    return connection.execute(f"{_QUOTE_BASE} WHERE q.id = ?", (quote_id,)).fetchone()


def list_quote_rows(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return connection.execute(f"{_QUOTE_BASE} ORDER BY q.id").fetchall()


def quote_exists(connection: sqlite3.Connection, quote_id: int) -> bool:
    row = connection.execute("SELECT 1 FROM quotes WHERE id = ?", (quote_id,)).fetchone()
    return row is not None


def get_quote_status(connection: sqlite3.Connection, quote_id: int) -> str | None:
    row = connection.execute("SELECT status FROM quotes WHERE id = ?", (quote_id,)).fetchone()
    return row["status"] if row else None


def get_quote_price_table_id(connection: sqlite3.Connection, quote_id: int) -> int | None:
    row = connection.execute(
        "SELECT price_table_id FROM quotes WHERE id = ?", (quote_id,)
    ).fetchone()
    return row["price_table_id"] if row else None


def update_quote_status(connection: sqlite3.Connection, quote_id: int, new_status: str) -> None:
    connection.execute("UPDATE quotes SET status = ? WHERE id = ?", (new_status, quote_id))
    connection.commit()


# ---------------------------------------------------------------------------
# Variações + preço congelável (RN-12/13/15/16)
# ---------------------------------------------------------------------------


def variant_exists(connection: sqlite3.Connection, variant_id: int) -> bool:
    row = connection.execute(
        "SELECT 1 FROM component_variants WHERE id = ?", (variant_id,)
    ).fetchone()
    return row is not None


def get_variant_price(
    connection: sqlite3.Connection, variant_id: int, price_table_id: int
) -> sqlite3.Row | None:
    """Preço da variação na tabela informada, com SKU associado (RN-12/13/15)."""
    return connection.execute(
        """
        SELECT pr.id AS price_id, pr.amount AS amount, pr.currency AS currency,
               pr.sku_id AS sku_id, s.code AS sku_code
        FROM prices pr
        JOIN skus s ON s.id = pr.sku_id
        WHERE pr.component_variant_id = ? AND pr.price_table_id = ?
        """,
        (variant_id, price_table_id),
    ).fetchone()


# ---------------------------------------------------------------------------
# Itens e componentes do item (14.11/14.12)
# ---------------------------------------------------------------------------


def insert_item(
    connection: sqlite3.Connection,
    *,
    quote_id: int,
    product_id: int | None,
    label: str,
    quantity: int,
    notes: str | None,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO quote_items (quote_id, product_id, label, quantity, notes)
        VALUES (?, ?, ?, ?, ?)
        """,
        (quote_id, product_id, label, quantity, notes),
    )
    connection.commit()
    return int(cursor.lastrowid)


def insert_item_component(
    connection: sqlite3.Connection,
    *,
    quote_item_id: int,
    component_variant_id: int,
    sku_id: int,
    frozen_unit_price: float,
    frozen_currency: str,
    price_source_id: int,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO quote_item_components
            (quote_item_id, component_variant_id, sku_id, frozen_unit_price,
             frozen_currency, price_source_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            quote_item_id,
            component_variant_id,
            sku_id,
            frozen_unit_price,
            frozen_currency,
            price_source_id,
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def get_item_row(connection: sqlite3.Connection, quote_id: int, item_id: int) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM quote_items WHERE id = ? AND quote_id = ?", (item_id, quote_id)
    ).fetchone()


def get_item_components(connection: sqlite3.Connection, item_id: int) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT qic.id AS id, qic.component_variant_id AS component_variant_id,
               s.code AS sku, qic.frozen_unit_price AS frozen_unit_price,
               qic.frozen_currency AS frozen_currency, qic.frozen_at AS frozen_at,
               qic.quantity AS quantity, pr.price_table_id AS price_table_id,
               pt.code AS price_table_code
        FROM quote_item_components qic
        JOIN skus s ON s.id = qic.sku_id
        LEFT JOIN prices pr ON pr.id = qic.price_source_id
        LEFT JOIN price_tables pt ON pt.id = pr.price_table_id
        WHERE qic.quote_item_id = ?
        ORDER BY qic.id
        """,
        (item_id,),
    ).fetchall()


def list_items_with_components(connection: sqlite3.Connection, quote_id: int) -> list[sqlite3.Row]:
    return connection.execute(
        "SELECT * FROM quote_items WHERE quote_id = ? ORDER BY id", (quote_id,)
    ).fetchall()


def update_item(connection: sqlite3.Connection, item_id: int, data: dict[str, Any]) -> None:
    cols = [
        c
        for c in ("quantity", "discount_percent", "discount_amount", "discount_reason", "notes")
        if c in data
    ]
    if not cols:
        return
    set_clause = ", ".join(f"{c} = ?" for c in cols)
    connection.execute(
        f"UPDATE quote_items SET {set_clause} WHERE id = ?",
        (*(data[c] for c in cols), item_id),
    )
    connection.commit()


# ---------------------------------------------------------------------------
# Totais (14.13)
# ---------------------------------------------------------------------------


def get_quote_totals_row(connection: sqlite3.Connection, quote_id: int) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM quote_totals WHERE quote_id = ?", (quote_id,)
    ).fetchone()


def upsert_quote_totals(
    connection: sqlite3.Connection,
    *,
    quote_id: int,
    subtotal: float,
    discount_percent: float,
    discount_amount: float,
    tax_amount: float,
    freight_amount: float,
    total: float,
    currency: str,
) -> sqlite3.Row:
    connection.execute(
        """
        INSERT INTO quote_totals
            (quote_id, subtotal, discount_percent, discount_amount, tax_amount,
             freight_amount, total, currency, calculated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(quote_id) DO UPDATE SET
            subtotal = excluded.subtotal,
            discount_percent = excluded.discount_percent,
            discount_amount = excluded.discount_amount,
            tax_amount = excluded.tax_amount,
            freight_amount = excluded.freight_amount,
            total = excluded.total,
            currency = excluded.currency,
            calculated_at = excluded.calculated_at
        """,
        (
            quote_id,
            subtotal,
            discount_percent,
            discount_amount,
            tax_amount,
            freight_amount,
            total,
            currency,
        ),
    )
    connection.commit()
    return get_quote_totals_row(connection, quote_id)
