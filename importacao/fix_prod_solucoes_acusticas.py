"""Remediação de variantes mescladas na importação de Soluções Acústicas.

O bug original: publish_item sempre usava descriptor=None, fazendo "Baffle Inclinado",
"Baffle Ondas" e "Baffle Retangular" (mesma dimensão/acabamento) colapsarem na mesma
component_variant. Só o ÚLTIMO upsert_price sobrevivia (UNIQUE(component_variant_id)).

Este script re-executa a lógica corrigida para todos os extracted_items aprovados da
importação, criando variantes separadas via descriptor=description_raw quando há colisão.
É idempotente — pode ser executado mais de uma vez com segurança.

Uso:
    python fix_prod_solucoes_acusticas.py --dry-run   # mostra o que faria
    python fix_prod_solucoes_acusticas.py              # aplica
"""

from __future__ import annotations
import os, re, sqlite3, sys

DRY_RUN = "--dry-run" in sys.argv
DB_PATH = os.environ.get("DATABASE_PATH", "./data/helence.db")
print(f"Banco: {DB_PATH}  |  dry-run={DRY_RUN}\n")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys = ON")

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _get_or_create(conn, table, key_col, key_val, extra_cols=None):
    r = conn.execute(f"SELECT id FROM {table} WHERE {key_col} = ?", (key_val,)).fetchone()
    if r:
        return int(r["id"])
    data = {key_col: key_val, **(extra_cols or {})}
    cols = ", ".join(data)
    placeholders = ", ".join("?" * len(data))
    c = conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", list(data.values()))
    return int(c.lastrowid)


def _resolve_dimension(conn, raw):
    if not raw:
        return None
    dm = re.match(r"^D(\d+)$", raw, re.IGNORECASE)
    if dm:
        d = int(dm.group(1))
        r = conn.execute(
            "SELECT id FROM dimensions WHERE diameter_mm = ? AND width_mm IS NULL",
            (d,),
        ).fetchone()
        if r:
            return int(r["id"])
        c = conn.execute(
            "INSERT INTO dimensions(diameter_mm, raw_label) VALUES(?, ?)", (d, raw)
        )
        return int(c.lastrowid)
    nums = [int(x) for x in re.findall(r"\d+", raw)]
    if len(nums) < 2:
        return None
    w, dep = nums[0], nums[1]
    h = nums[2] if len(nums) > 2 else None
    r = conn.execute(
        "SELECT id FROM dimensions WHERE width_mm=? AND depth_mm=? AND height_mm IS ?",
        (w, dep, h),
    ).fetchone()
    if r:
        return int(r["id"])
    c = conn.execute(
        "INSERT INTO dimensions(width_mm, depth_mm, height_mm, raw_label) VALUES(?,?,?,?)",
        (w, dep, h, raw),
    )
    return int(c.lastrowid)


def _find_variant(conn, family_id, product_id, component_id, dimension_id, finish_id, descriptor):
    return conn.execute(
        """SELECT id, description FROM component_variants
           WHERE family_id IS ? AND product_id IS ? AND component_id=?
             AND dimension_id IS ? AND finish_id IS ? AND descriptor IS ?""",
        (family_id, product_id, component_id, dimension_id, finish_id, descriptor),
    ).fetchone()


def _create_variant(conn, family_id, product_id, component_id, dimension_id, finish_id, descriptor, description):
    c = conn.execute(
        """INSERT INTO component_variants
           (family_id, product_id, component_id, dimension_id, finish_id, descriptor, description)
           VALUES (?,?,?,?,?,?,?)""",
        (family_id, product_id, component_id, dimension_id, finish_id, descriptor, description),
    )
    return int(c.lastrowid)


def _upsert_price(conn, variant_id, sku_id, amount, currency, ei_id):
    conn.execute(
        """INSERT INTO prices (component_variant_id, sku_id, amount, currency, source_extracted_item_id)
           VALUES (?,?,?,?,?)
           ON CONFLICT(component_variant_id) DO UPDATE SET
               sku_id = excluded.sku_id,
               amount = excluded.amount,
               currency = excluded.currency,
               source_extracted_item_id = excluded.source_extracted_item_id""",
        (variant_id, sku_id, amount, currency, ei_id),
    )

# ---------------------------------------------------------------------------
# busca extracted_items aprovados da importação SA
# ---------------------------------------------------------------------------
items = conn.execute(
    """SELECT ei.*
       FROM extracted_items ei
       JOIN imported_pages ip  ON ip.id  = ei.imported_page_id
       JOIN imported_files imf ON imf.id = ip.imported_file_id
       WHERE ei.review_status = 'aprovado'
         AND (imf.original_filename LIKE '%solucoes%'
              OR imf.notes         LIKE '%SOLUCOES%')
       ORDER BY ei.id""",
).fetchall()

if not items:
    print("Nenhum extracted_item aprovado de 'Soluções Acústicas' encontrado — verifique o filtro.")
    conn.close()
    sys.exit(0)

print(f"Encontrados {len(items)} extracted_items aprovados.\n")

fixed = 0
skipped = 0

for ei in items:
    family_id    = _get_or_create(conn, "product_families", "name", ei["family_raw"])
    component_id = _get_or_create(conn, "product_components", "name", ei["component_type_raw"])
    dimension_id = _resolve_dimension(conn, ei["dimension_raw"])

    product_id = None
    if ei["product_context_raw"]:
        r = conn.execute(
            "SELECT id FROM products WHERE family_id=? AND name=?",
            (family_id, ei["product_context_raw"]),
        ).fetchone()
        if r:
            product_id = int(r["id"])
        else:
            if not DRY_RUN:
                c = conn.execute(
                    "INSERT INTO products(family_id, name, dimension_id) VALUES(?,?,?)",
                    (family_id, ei["product_context_raw"], dimension_id),
                )
                product_id = int(c.lastrowid)
            else:
                product_id = None  # placeholder for dry-run

    finish_id = None
    if ei["finish_raw"]:
        fr = conn.execute("SELECT id FROM finishes WHERE name=?", (ei["finish_raw"],)).fetchone()
        if fr:
            finish_id = int(fr["id"])

    # --- lógica corrigida de resolução de variante ---
    descriptor: str | None = None
    existing = _find_variant(conn, family_id, product_id, component_id, dimension_id, finish_id, None)
    if existing and existing["description"] != ei["description_raw"]:
        descriptor = ei["description_raw"]
        existing = _find_variant(conn, family_id, product_id, component_id, dimension_id, finish_id, descriptor)

    # verifica se já está correto (idempotência)
    if existing:
        current_price = conn.execute(
            """SELECT s.code as sku_code FROM prices pr
               LEFT JOIN skus s ON s.id = pr.sku_id
               WHERE pr.component_variant_id = ? AND pr.source_extracted_item_id = ?""",
            (int(existing["id"]), ei["id"]),
        ).fetchone()
        if current_price and current_price["sku_code"] == ei["sku_raw"]:
            print(f"  OK     ei={ei['id']:4d}  '{ei['description_raw']}'  sku={ei['sku_raw']}")
            skipped += 1
            continue

    amount = float(ei["price_raw"])
    sku_id = None
    if ei["sku_raw"]:
        if not DRY_RUN:
            sku_id = _get_or_create(conn, "skus", "code", ei["sku_raw"])
        else:
            r = conn.execute("SELECT id FROM skus WHERE code=?", (ei["sku_raw"],)).fetchone()
            sku_id = int(r["id"]) if r else "(novo)"

    if existing:
        variant_id = int(existing["id"])
        action = f"FIX-PRICE variant={variant_id}"
    else:
        if not DRY_RUN:
            variant_id = _create_variant(
                conn, family_id, product_id, component_id,
                dimension_id, finish_id, descriptor, ei["description_raw"],
            )
            action = f"NOVA-VARIANT id={variant_id} descriptor={descriptor!r}"
        else:
            action = f"NOVA-VARIANT descriptor={descriptor!r}"

    print(f"  {action}  ei={ei['id']:4d}  '{ei['description_raw']}'  sku={ei['sku_raw']}  R${amount}")

    if not DRY_RUN:
        _upsert_price(conn, variant_id, sku_id, amount, ei["currency"] or "BRL", ei["id"])

    fixed += 1

if not DRY_RUN and fixed > 0:
    conn.commit()
    print(f"\n✓ {fixed} item(s) corrigido(s), {skipped} já OK. Commit realizado.")
elif fixed == 0:
    print(f"\nNenhuma correção necessária ({skipped} itens já OK).")
else:
    print(f"\n[DRY-RUN] {fixed} item(s) seriam corrigidos, {skipped} já OK.")

conn.close()
