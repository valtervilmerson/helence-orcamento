"""Acesso a dados do catálogo manual (docs/06, seções 14.8/14.9)."""

from __future__ import annotations

import sqlite3
from typing import Any


class SimpleRepository:
    """CRUD genérico para tabelas de referência simples (id + colunas próprias).

    `table` e `columns` são definidos internamente por este módulo (não vêm de
    entrada do usuário), então a interpolação direta no SQL é segura.
    """

    def __init__(self, table: str, columns: list[str]) -> None:
        self.table = table
        self.columns = columns

    def list(self, connection: sqlite3.Connection) -> list[sqlite3.Row]:
        return connection.execute(f"SELECT * FROM {self.table} ORDER BY id").fetchall()

    def get(self, connection: sqlite3.Connection, id_: int) -> sqlite3.Row | None:
        return connection.execute(f"SELECT * FROM {self.table} WHERE id = ?", (id_,)).fetchone()

    def create(self, connection: sqlite3.Connection, data: dict[str, Any]) -> int:
        cols = [c for c in self.columns if c in data]
        placeholders = ", ".join("?" for _ in cols)
        cursor = connection.execute(
            f"INSERT INTO {self.table} ({', '.join(cols)}) VALUES ({placeholders})",
            tuple(data[c] for c in cols),
        )
        connection.commit()
        return int(cursor.lastrowid)

    def update(self, connection: sqlite3.Connection, id_: int, data: dict[str, Any]) -> None:
        cols = [c for c in self.columns if c in data]
        if not cols:
            return
        set_clause = ", ".join(f"{c} = ?" for c in cols)
        connection.execute(
            f"UPDATE {self.table} SET {set_clause} WHERE id = ?",
            (*(data[c] for c in cols), id_),
        )
        connection.commit()

    def delete(self, connection: sqlite3.Connection, id_: int) -> None:
        connection.execute(f"DELETE FROM {self.table} WHERE id = ?", (id_,))
        connection.commit()


def list_price_tables(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return connection.execute("SELECT id, code, status FROM price_tables ORDER BY id").fetchall()


def get_price_table(connection: sqlite3.Connection, price_table_id: int) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM price_tables WHERE id = ?", (price_table_id,)
    ).fetchone()


def get_price_table_by_code(connection: sqlite3.Connection, code: str) -> sqlite3.Row | None:
    return connection.execute("SELECT * FROM price_tables WHERE code = ?", (code,)).fetchone()


def insert_price_table(
    connection: sqlite3.Connection,
    *,
    code: str,
    name: str | None,
    valid_from: str | None,
    source_imported_file_id: int | None,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO price_tables (code, name, valid_from, source_imported_file_id)
        VALUES (?, ?, ?, ?)
        """,
        (code, name, valid_from, source_imported_file_id),
    )
    return int(cursor.lastrowid)


def get_vigente_price_table(connection: sqlite3.Connection) -> sqlite3.Row | None:
    return connection.execute("SELECT * FROM price_tables WHERE status = 'vigente'").fetchone()


def set_price_table_status(
    connection: sqlite3.Connection, price_table_id: int, new_status: str
) -> None:
    connection.execute(
        "UPDATE price_tables SET status = ? WHERE id = ?", (new_status, price_table_id)
    )


# ---------------------------------------------------------------------------
# Resolução/criação de entidades por nome (Fase 7 — publicação)
# ---------------------------------------------------------------------------


def get_or_create_family(connection: sqlite3.Connection, name: str) -> int:
    row = connection.execute("SELECT id FROM product_families WHERE name = ?", (name,)).fetchone()
    if row is not None:
        return int(row["id"])
    cursor = connection.execute("INSERT INTO product_families (name) VALUES (?)", (name,))
    return int(cursor.lastrowid)


def get_or_create_component_type(connection: sqlite3.Connection, name: str) -> int:
    row = connection.execute("SELECT id FROM product_components WHERE name = ?", (name,)).fetchone()
    if row is not None:
        return int(row["id"])
    cursor = connection.execute("INSERT INTO product_components (name) VALUES (?)", (name,))
    return int(cursor.lastrowid)


def get_or_create_product(
    connection: sqlite3.Connection, family_id: int, name: str, dimension_id: int | None
) -> int:
    row = connection.execute(
        "SELECT id FROM products WHERE family_id = ? AND name = ?", (family_id, name)
    ).fetchone()
    if row is not None:
        return int(row["id"])
    cursor = connection.execute(
        "INSERT INTO products (family_id, name, dimension_id) VALUES (?, ?, ?)",
        (family_id, name, dimension_id),
    )
    return int(cursor.lastrowid)


def find_finish_by_name(connection: sqlite3.Connection, name: str) -> sqlite3.Row | None:
    return connection.execute("SELECT id FROM finishes WHERE name = ?", (name,)).fetchone()


def get_or_create_dimension(
    connection: sqlite3.Connection,
    *,
    width_mm: int | None,
    depth_mm: int | None,
    diameter_mm: int | None,
    height_mm: int | None,
    raw_label: str | None,
) -> int:
    row = connection.execute(
        """
        SELECT id FROM dimensions
        WHERE width_mm IS ? AND depth_mm IS ? AND diameter_mm IS ? AND height_mm IS ?
        """,
        (width_mm, depth_mm, diameter_mm, height_mm),
    ).fetchone()
    if row is not None:
        return int(row["id"])
    cursor = connection.execute(
        """
        INSERT INTO dimensions (width_mm, depth_mm, diameter_mm, height_mm, raw_label)
        VALUES (?, ?, ?, ?, ?)
        """,
        (width_mm, depth_mm, diameter_mm, height_mm, raw_label),
    )
    return int(cursor.lastrowid)


def find_variant(
    connection: sqlite3.Connection,
    *,
    product_id: int | None,
    component_id: int,
    dimension_id: int | None,
    finish_id: int | None,
    descriptor: str | None,
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT id FROM component_variants
        WHERE product_id IS ? AND component_id = ? AND dimension_id IS ?
          AND finish_id IS ? AND descriptor IS ?
        """,
        (product_id, component_id, dimension_id, finish_id, descriptor),
    ).fetchone()


product_families = SimpleRepository("product_families", ["name", "description"])
dimensions = SimpleRepository(
    "dimensions", ["width_mm", "depth_mm", "diameter_mm", "height_mm", "raw_label"]
)
finishes = SimpleRepository("finishes", ["name", "finish_group", "description"])
product_components = SimpleRepository("product_components", ["name", "description", "finish_group"])
products = SimpleRepository("products", ["family_id", "name", "dimension_id"])
compatibility_rules = SimpleRepository(
    "component_compatibility_rules",
    ["component_a_id", "descriptor_a", "component_b_id", "descriptor_b", "notes"],
)
family_component_requirements = SimpleRepository(
    "family_component_requirements", ["family_id", "component_id", "requirement"]
)


# ---------------------------------------------------------------------------
# component_variants + skus + prices (14.9)
# ---------------------------------------------------------------------------

_VARIANT_SEARCH_BASE = """
    SELECT
        cv.id AS component_variant_id,
        pf.name AS family,
        p.name AS product,
        pc.name AS component,
        cv.descriptor AS descriptor,
        cv.description AS description,
        d.width_mm AS dim_width_mm,
        d.depth_mm AS dim_depth_mm,
        d.diameter_mm AS dim_diameter_mm,
        d.height_mm AS dim_height_mm,
        d.raw_label AS dim_raw_label,
        f.name AS finish,
        f.finish_group AS finish_group,
        s.code AS sku,
        pr.amount AS price_amount,
        pr.currency AS price_currency,
        pt.id AS price_table_id,
        pt.code AS price_table_code,
        pt.status AS price_table_status
    FROM component_variants cv
    LEFT JOIN products p ON p.id = cv.product_id
    LEFT JOIN product_families pf ON pf.id = p.family_id
    JOIN product_components pc ON pc.id = cv.component_id
    LEFT JOIN dimensions d ON d.id = cv.dimension_id
    LEFT JOIN finishes f ON f.id = cv.finish_id
    LEFT JOIN prices pr ON pr.component_variant_id = cv.id
        AND pr.price_table_id = (SELECT id FROM price_tables WHERE status = 'vigente' LIMIT 1)
    LEFT JOIN skus s ON s.id = pr.sku_id
    LEFT JOIN price_tables pt ON pt.id = pr.price_table_id
"""


def search_variants(
    connection: sqlite3.Connection,
    *,
    family: str | None = None,
    product: str | None = None,
    component: str | None = None,
    dimension: str | None = None,
    finish: str | None = None,
    finish_group: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[sqlite3.Row], int]:
    conditions: list[str] = []
    params: list[Any] = []

    if family:
        conditions.append("pf.name = ?")
        params.append(family)
    if product:
        conditions.append("p.name = ?")
        params.append(product)
    if component:
        conditions.append("pc.name = ?")
        params.append(component)
    if dimension:
        conditions.append("d.raw_label = ?")
        params.append(dimension)
    if finish:
        conditions.append("f.name = ?")
        params.append(finish)
    if finish_group:
        conditions.append("f.finish_group = ?")
        params.append(finish_group)
    if q:
        conditions.append("(cv.description LIKE ? OR cv.descriptor LIKE ? OR s.code LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    total = connection.execute(
        f"SELECT COUNT(*) AS n FROM ({_VARIANT_SEARCH_BASE} {where_clause})", params
    ).fetchone()["n"]

    offset = (page - 1) * page_size
    rows = connection.execute(
        f"{_VARIANT_SEARCH_BASE} {where_clause} ORDER BY cv.id LIMIT ? OFFSET ?",
        (*params, page_size, offset),
    ).fetchall()

    return rows, total


def get_variant_row(connection: sqlite3.Connection, variant_id: int) -> sqlite3.Row | None:
    return connection.execute(f"{_VARIANT_SEARCH_BASE} WHERE cv.id = ?", (variant_id,)).fetchone()


def get_price_history(connection: sqlite3.Connection, variant_id: int) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT pt.id AS price_table_id, pt.code AS price_table_code,
               pt.status AS price_table_status,
               pr.amount AS price_amount, pr.currency AS price_currency
        FROM prices pr
        JOIN price_tables pt ON pt.id = pr.price_table_id
        WHERE pr.component_variant_id = ?
        ORDER BY pt.id
        """,
        (variant_id,),
    ).fetchall()


def variant_exists(connection: sqlite3.Connection, variant_id: int) -> bool:
    row = connection.execute(
        "SELECT 1 FROM component_variants WHERE id = ?", (variant_id,)
    ).fetchone()
    return row is not None


def get_or_create_sku(connection: sqlite3.Connection, code: str, notes: str | None) -> int:
    row = connection.execute("SELECT id FROM skus WHERE code = ?", (code,)).fetchone()
    if row is not None:
        return int(row["id"])
    cursor = connection.execute("INSERT INTO skus (code, notes) VALUES (?, ?)", (code, notes))
    return int(cursor.lastrowid)


def insert_variant(connection: sqlite3.Connection, data: dict[str, Any]) -> int:
    cursor = connection.execute(
        """
        INSERT INTO component_variants
            (product_id, component_id, dimension_id, finish_id, descriptor, description)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            data.get("product_id"),
            data["component_id"],
            data.get("dimension_id"),
            data.get("finish_id"),
            data.get("descriptor"),
            data.get("description"),
        ),
    )
    return int(cursor.lastrowid)


def insert_price(
    connection: sqlite3.Connection,
    *,
    component_variant_id: int,
    sku_id: int,
    price_table_id: int,
    amount: float,
    currency: str,
    source_extracted_item_id: int | None = None,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO prices
            (component_variant_id, sku_id, price_table_id, amount, currency,
             source_extracted_item_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (component_variant_id, sku_id, price_table_id, amount, currency, source_extracted_item_id),
    )
    return int(cursor.lastrowid)


def upsert_price(
    connection: sqlite3.Connection,
    *,
    component_variant_id: int,
    sku_id: int,
    price_table_id: int,
    amount: float,
    currency: str,
    source_extracted_item_id: int | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO prices
            (component_variant_id, sku_id, price_table_id, amount, currency,
             source_extracted_item_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (component_variant_id, price_table_id) DO UPDATE SET
            sku_id = excluded.sku_id,
            amount = excluded.amount,
            currency = excluded.currency,
            source_extracted_item_id = excluded.source_extracted_item_id
        """,
        (component_variant_id, sku_id, price_table_id, amount, currency, source_extracted_item_id),
    )


def update_variant(connection: sqlite3.Connection, variant_id: int, data: dict[str, Any]) -> None:
    cols = [
        c
        for c in (
            "product_id",
            "component_id",
            "dimension_id",
            "finish_id",
            "descriptor",
            "description",
        )
        if c in data
    ]
    if not cols:
        return
    set_clause = ", ".join(f"{c} = ?" for c in cols)
    connection.execute(
        f"UPDATE component_variants SET {set_clause} WHERE id = ?",
        (*(data[c] for c in cols), variant_id),
    )


def referenced_by(connection: sqlite3.Connection, variant_id: int) -> dict[str, int]:
    references: dict[str, int] = {}

    price_table_count = connection.execute(
        "SELECT COUNT(*) AS n FROM prices WHERE component_variant_id = ?", (variant_id,)
    ).fetchone()["n"]
    if price_table_count:
        references["prices"] = price_table_count

    quote_count = connection.execute(
        "SELECT COUNT(*) AS n FROM quote_item_components WHERE component_variant_id = ?",
        (variant_id,),
    ).fetchone()["n"]
    if quote_count:
        references["quote_item_components"] = quote_count

    return references


def delete_variant(connection: sqlite3.Connection, variant_id: int) -> None:
    connection.execute("DELETE FROM accessories WHERE component_variant_id = ?", (variant_id,))
    connection.execute("DELETE FROM prices WHERE component_variant_id = ?", (variant_id,))
    connection.execute("DELETE FROM component_variants WHERE id = ?", (variant_id,))
    connection.commit()
