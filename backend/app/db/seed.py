"""Seed mínimo de dados de referência (docs/07, Fases 1 e 2).

Cria um usuário de teste por papel e uma ``price_table`` vazia em
status ``vigente``, evitando o erro ``NENHUMA_TABELA_VIGENTE`` ao
montar orçamentos (Fase 3), além de um pequeno catálogo manual real
(``seed_catalog``). Idempotente: rodar mais de uma vez não duplica
registros.

Mapeamento de papéis (docs/04, seção "Papéis"): a coluna ``users.role``
só aceita ``admin | importador | revisor | vendedor | colaborador``
(docs/schema/schema.sql). "Aprovador" é o papel ``admin``; "Auditor" —
que pode ser o próprio Admin — é semeado com o papel ``colaborador``
para ter um usuário de teste dedicado sem conflitar com o Admin/
Aprovador.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.auth.security import hash_password
from app.config import get_settings
from app.db.connection import get_connection
from app.db.migrate import apply_migrations

SEED_USERS = [
    ("Importador Teste", "importador@helence.local", "importador"),
    ("Revisor Teste", "revisor@helence.local", "revisor"),
    ("Aprovador Teste", "aprovador@helence.local", "admin"),
    ("Vendedor Teste", "vendedor@helence.local", "vendedor"),
    ("Auditor Teste", "auditor@helence.local", "colaborador"),
]

# Senha padrão dos usuários de teste — apenas para ambiente de
# desenvolvimento/demonstração (docs/07, Fase 11).
SEED_USER_PASSWORD = "helence123"

SEED_PRICE_TABLE_CODE = "SEED-VAZIA"

# Cliente de exemplo para a montagem manual de orçamentos (Fase 3).
SEED_CUSTOMER_NAME = "Studio Almeida Arquitetura"

# Catálogo manual de exemplo (Fase 2): replica as 9 variações de
# "Reunião 1200x900 — Tampo Inteiro Simples" do spike de extração
# (docs/samples/extracao-amostra.json, página 2), provando o modelo de
# dados com dados reais e gerando insumo para a montagem de orçamentos
# da Fase 3.
SEED_FAMILY_NAME = "Mesas de Reunião"
SEED_PRODUCT_NAME = "Reunião 1200x900"
SEED_COMPONENT_NAME = "Tampo"
SEED_DESCRIPTOR = "Inteiro Simples"

# (acabamento, código SKU, preço)
SEED_VARIANTS = [
    ("Argila", "3981113028", 382.75),
    ("Branco", "3981121234", 374.45),
    ("Preto", "3981130567", 493.80),
    ("Gianduia", "3981138901", 472.85),
    ("Amêndoa", "3981142345", 493.80),
    ("Carvalho", "3981144789", 493.80),
    ("Nogueira Cádiz", "3981146012", 493.80),
    ("Grafite", "3981148256", 472.85),
    ("Itapuã", "3981149472", 493.80),
]


def seed(connection: sqlite3.Connection) -> None:
    for name, email, role in SEED_USERS:
        connection.execute(
            "INSERT OR IGNORE INTO users (name, email, role) VALUES (?, ?, ?)",
            (name, email, role),
        )
        connection.execute(
            "UPDATE users SET password_hash = ? WHERE email = ? AND password_hash IS NULL",
            (hash_password(SEED_USER_PASSWORD), email),
        )

    connection.execute(
        """
        INSERT OR IGNORE INTO price_tables (code, name, status)
        VALUES (?, 'Tabela seed (vazia)', 'vigente')
        """,
        (SEED_PRICE_TABLE_CODE,),
    )

    existing_customer = connection.execute(
        "SELECT id FROM customers WHERE name = ?", (SEED_CUSTOMER_NAME,)
    ).fetchone()
    if existing_customer is None:
        connection.execute("INSERT INTO customers (name) VALUES (?)", (SEED_CUSTOMER_NAME,))

    seed_catalog(connection)

    connection.commit()


def seed_catalog(connection: sqlite3.Connection) -> None:
    price_table_id = connection.execute(
        "SELECT id FROM price_tables WHERE code = ?", (SEED_PRICE_TABLE_CODE,)
    ).fetchone()["id"]

    connection.execute(
        "INSERT OR IGNORE INTO product_families (name) VALUES (?)", (SEED_FAMILY_NAME,)
    )
    family_id = connection.execute(
        "SELECT id FROM product_families WHERE name = ?", (SEED_FAMILY_NAME,)
    ).fetchone()["id"]

    connection.execute(
        "INSERT OR IGNORE INTO dimensions (width_mm, depth_mm, raw_label) "
        "VALUES (1200, 900, '1200x900')"
    )
    dimension_id = connection.execute(
        "SELECT id FROM dimensions WHERE width_mm = 1200 AND depth_mm = 900"
    ).fetchone()["id"]

    connection.execute(
        "INSERT OR IGNORE INTO products (family_id, name, dimension_id) VALUES (?, ?, ?)",
        (family_id, SEED_PRODUCT_NAME, dimension_id),
    )
    product_id = connection.execute(
        "SELECT id FROM products WHERE family_id = ? AND name = ?", (family_id, SEED_PRODUCT_NAME)
    ).fetchone()["id"]

    connection.execute(
        "INSERT OR IGNORE INTO product_components (name) VALUES (?)", (SEED_COMPONENT_NAME,)
    )
    component_id = connection.execute(
        "SELECT id FROM product_components WHERE name = ?", (SEED_COMPONENT_NAME,)
    ).fetchone()["id"]

    for finish_name, sku_code, price in SEED_VARIANTS:
        connection.execute(
            "INSERT OR IGNORE INTO finishes (name, finish_group) VALUES (?, 'madeirado')",
            (finish_name,),
        )
        finish_id = connection.execute(
            "SELECT id FROM finishes WHERE name = ?", (finish_name,)
        ).fetchone()["id"]

        description = (
            f"Tampo Inteiro Simples Para Estrutura Reunião 1200x900 Caixa de Tomada {finish_name}"
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO component_variants
                (product_id, component_id, dimension_id, finish_id, descriptor, description)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (product_id, component_id, dimension_id, finish_id, SEED_DESCRIPTOR, description),
        )
        variant_id = connection.execute(
            """
            SELECT id FROM component_variants
            WHERE product_id = ? AND component_id = ? AND dimension_id = ?
              AND finish_id = ? AND descriptor = ?
            """,
            (product_id, component_id, dimension_id, finish_id, SEED_DESCRIPTOR),
        ).fetchone()["id"]

        connection.execute("INSERT OR IGNORE INTO skus (code) VALUES (?)", (sku_code,))
        sku_id = connection.execute("SELECT id FROM skus WHERE code = ?", (sku_code,)).fetchone()[
            "id"
        ]

        connection.execute(
            """
            INSERT OR IGNORE INTO prices (component_variant_id, sku_id, price_table_id, amount)
            VALUES (?, ?, ?, ?)
            """,
            (variant_id, sku_id, price_table_id, price),
        )


def main() -> None:
    settings = get_settings()
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as connection:
        apply_migrations(connection)
        seed(connection)

    print("Seed aplicado.")


if __name__ == "__main__":
    main()
