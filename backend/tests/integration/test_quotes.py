"""Ciclo de vida básico de orçamentos (docs/06, 14.10-14.13; docs/07, Fase 3)."""

from app.db.connection import get_connection
from app.db.seed import SEED_CUSTOMER_NAME


def _customer_id() -> int:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id FROM customers WHERE name = ?", (SEED_CUSTOMER_NAME,)
        ).fetchone()
        return row["id"]


def _seeded_variant(client) -> dict:
    search = client.get("/api/v1/components", params={"finish": "Carvalho"}).json()
    return search["items"][0]


def test_create_quote_anchors_to_vigente_price_table(client) -> None:
    response = client.post(
        "/api/v1/quotes",
        json={"customer_id": _customer_id(), "valid_until": "2026-07-08", "notes": "Teste Fase 3"},
    )
    assert response.status_code == 201

    body = response.json()
    assert body["status"] == "rascunho"
    assert body["customer"]["name"] == SEED_CUSTOMER_NAME
    assert body["price_table"]["status"] == "vigente"
    assert body["quote_number"].startswith("ORC-")


def test_create_quote_unknown_customer(client) -> None:
    response = client.post("/api/v1/quotes", json={"customer_id": 999999})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CLIENTE_NAO_ENCONTRADO"


def test_get_quote_not_found(client) -> None:
    response = client.get("/api/v1/quotes/999999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ORCAMENTO_NAO_ENCONTRADO"


def test_full_quote_lifecycle(client) -> None:
    variant = _seeded_variant(client)
    unit_price = variant["price"]["amount"]

    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()
    quote_id = quote["id"]

    # Adiciona item (RN-15/RN-16: preço congelado no momento da adição)
    item_response = client.post(
        f"/api/v1/quotes/{quote_id}/items",
        json={
            "component_variant_id": variant["component_variant_id"],
            "label": "Mesa Reunião 1200x900 — Carvalho",
            "quantity": 2,
        },
    )
    assert item_response.status_code == 201
    item = item_response.json()
    assert item["components"][0]["frozen_unit_price"] == unit_price
    assert item["components"][0]["sku"] == variant["sku"]
    assert item["line_subtotal"] == round(unit_price * 2, 2)

    # Atualiza quantidade e desconto (RN-08/RN-09)
    patched = client.patch(
        f"/api/v1/quotes/{quote_id}/items/{item['id']}",
        json={"quantity": 3, "discount_percent": 10, "discount_reason": "Negociação comercial"},
    )
    assert patched.status_code == 200
    patched_body = patched.json()
    expected_subtotal = round(unit_price * 3 * 0.9, 2)
    assert patched_body["line_subtotal"] == expected_subtotal

    # Calcula total ao vivo
    totals = client.get(f"/api/v1/quotes/{quote_id}/totals")
    assert totals.status_code == 200
    totals_body = totals.json()
    assert totals_body["is_snapshot"] is False
    assert totals_body["subtotal"] == round(unit_price * 3, 2)
    assert totals_body["total"] == expected_subtotal

    # Congela o total
    frozen = client.post(f"/api/v1/quotes/{quote_id}/totals/freeze")
    assert frozen.status_code == 200
    assert frozen.json()["is_snapshot"] is True
    assert frozen.json()["total"] == expected_subtotal

    # Muda status: rascunho -> enviado -> aprovado
    sent = client.patch(f"/api/v1/quotes/{quote_id}", json={"status": "enviado"})
    assert sent.status_code == 200
    assert sent.json()["status"] == "enviado"

    approved = client.patch(f"/api/v1/quotes/{quote_id}", json={"status": "aprovado"})
    assert approved.status_code == 200
    assert approved.json()["status"] == "aprovado"


def test_price_freeze_survives_price_table_change(client) -> None:
    variant = _seeded_variant(client)
    unit_price = variant["price"]["amount"]

    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()
    quote_id = quote["id"]

    item = client.post(
        f"/api/v1/quotes/{quote_id}/items",
        json={
            "component_variant_id": variant["component_variant_id"],
            "label": "Mesa Reunião 1200x900 — Carvalho",
            "quantity": 1,
        },
    ).json()
    assert item["components"][0]["frozen_unit_price"] == unit_price

    # Publica uma nova versão de tabela vigente, com preço diferente para a mesma variação
    with get_connection() as connection:
        connection.execute(
            "UPDATE price_tables SET status = 'substituida' WHERE status = 'vigente'"
        )
        connection.execute(
            "INSERT INTO price_tables (code, name, status) "
            "VALUES ('NOVA-VIGENTE', 'Nova', 'vigente')"
        )
        new_table_id = connection.execute(
            "SELECT id FROM price_tables WHERE code = 'NOVA-VIGENTE'"
        ).fetchone()["id"]
        sku_id = connection.execute(
            "SELECT id FROM skus WHERE code = ?", (variant["sku"],)
        ).fetchone()["id"]
        connection.execute(
            """
            INSERT INTO prices (component_variant_id, sku_id, price_table_id, amount)
            VALUES (?, ?, ?, ?)
            """,
            (variant["component_variant_id"], sku_id, new_table_id, unit_price + 100),
        )
        connection.commit()

    # Item já incluído mantém o preço congelado (RN-16)
    unchanged = client.get(f"/api/v1/quotes/{quote_id}/items/{item['id']}")
    assert unchanged.json()["components"][0]["frozen_unit_price"] == unit_price

    # Novo orçamento é ancorado à nova tabela vigente (RN-15)
    new_quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()
    assert new_quote["price_table"]["code"] == "NOVA-VIGENTE"

    new_item = client.post(
        f"/api/v1/quotes/{new_quote['id']}/items",
        json={
            "component_variant_id": variant["component_variant_id"],
            "label": "Mesa Reunião 1200x900 — Carvalho",
            "quantity": 1,
        },
    ).json()
    assert new_item["components"][0]["frozen_unit_price"] == unit_price + 100


def test_add_item_without_price_is_blocked(client) -> None:
    component_type = client.post(
        "/api/v1/catalog/component-types", json={"name": "Sem Preço Teste"}
    ).json()
    variant = client.post(
        "/api/v1/components", json={"component_id": component_type["id"], "descriptor": "Sem preço"}
    ).json()

    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()

    response = client.post(
        f"/api/v1/quotes/{quote['id']}/items",
        json={
            "component_variant_id": variant["component_variant_id"],
            "label": "Item sem preço",
            "quantity": 1,
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ITEM_SEM_PRECO"


def test_cannot_add_item_to_non_draft_quote(client) -> None:
    variant = _seeded_variant(client)
    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()

    rejected = client.patch(f"/api/v1/quotes/{quote['id']}", json={"status": "rejeitado"})
    assert rejected.status_code == 200

    response = client.post(
        f"/api/v1/quotes/{quote['id']}/items",
        json={
            "component_variant_id": variant["component_variant_id"],
            "label": "Não deveria entrar",
            "quantity": 1,
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "STATUS_INVALIDO"


def test_invalid_status_transition(client) -> None:
    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()

    response = client.patch(f"/api/v1/quotes/{quote['id']}", json={"status": "aprovado"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TRANSICAO_INVALIDA"


def test_freeze_empty_quote_is_blocked(client) -> None:
    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()

    response = client.post(f"/api/v1/quotes/{quote['id']}/totals/freeze")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ORCAMENTO_VAZIO"


def test_discount_without_reason_is_blocked(client) -> None:
    variant = _seeded_variant(client)
    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()
    item = client.post(
        f"/api/v1/quotes/{quote['id']}/items",
        json={
            "component_variant_id": variant["component_variant_id"],
            "label": "Mesa Reunião 1200x900 — Carvalho",
            "quantity": 1,
        },
    ).json()

    response = client.patch(
        f"/api/v1/quotes/{quote['id']}/items/{item['id']}", json={"discount_percent": 5}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "DESCONTO_SEM_JUSTIFICATIVA"


def test_invalid_quantity_is_blocked(client) -> None:
    variant = _seeded_variant(client)
    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()
    item = client.post(
        f"/api/v1/quotes/{quote['id']}/items",
        json={
            "component_variant_id": variant["component_variant_id"],
            "label": "Mesa Reunião 1200x900 — Carvalho",
            "quantity": 1,
        },
    ).json()

    response = client.patch(
        f"/api/v1/quotes/{quote['id']}/items/{item['id']}", json={"quantity": 0}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "QUANTIDADE_INVALIDA"
