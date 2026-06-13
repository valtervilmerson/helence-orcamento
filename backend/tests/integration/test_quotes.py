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


def _seeded_variant_by_finish(client, finish: str) -> dict:
    search = client.get("/api/v1/components", params={"finish": finish}).json()
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


def _vigente_price_table_id() -> int:
    with get_connection() as connection:
        row = connection.execute("SELECT id FROM price_tables WHERE status = 'vigente'").fetchone()
        return row["id"]


def _create_variant_with_price(
    client, *, component_id: int, descriptor: str, sku: str, amount: float = 100
) -> dict:
    response = client.post(
        "/api/v1/components",
        json={
            "component_id": component_id,
            "descriptor": descriptor,
            "sku": {"code": sku},
            "price": {"amount": amount, "price_table_id": _vigente_price_table_id()},
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_variant_with_product(
    client, *, product_id: int, component_id: int, descriptor: str, sku: str, amount: float = 100
) -> dict:
    response = client.post(
        "/api/v1/components",
        json={
            "product_id": product_id,
            "component_id": component_id,
            "descriptor": descriptor,
            "sku": {"code": sku},
            "price": {"amount": amount, "price_table_id": _vigente_price_table_id()},
        },
    )
    assert response.status_code == 201
    return response.json()


def test_add_component_to_existing_item_without_rule_is_allowed(client) -> None:
    """RN-04: sem regra cadastrada para o par de tipos de componente, não há restrição."""
    tampo = _seeded_variant(client)

    accessory_type = client.post(
        "/api/v1/catalog/component-types", json={"name": "Acessório RN04 Teste A"}
    ).json()
    accessory = _create_variant_with_price(
        client,
        component_id=accessory_type["id"],
        descriptor="Acessório Avulso RN04 Teste A",
        sku="ACC-RN04-A",
    )

    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()
    item = client.post(
        f"/api/v1/quotes/{quote['id']}/items",
        json={
            "component_variant_id": tampo["component_variant_id"],
            "label": "Mesa Reunião 1200x900 — Carvalho",
            "quantity": 1,
        },
    ).json()

    response = client.post(
        f"/api/v1/quotes/{quote['id']}/items/{item['id']}/components",
        json={"component_variant_id": accessory["component_variant_id"]},
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body["components"]) == 2
    assert body["line_subtotal"] == round(tampo["price"]["amount"] + 100, 2)


def test_add_component_with_compatible_descriptor_is_allowed(client) -> None:
    """RN-04: par com regra cadastrada e descritores correspondentes é aceito."""
    component_types = client.get("/api/v1/catalog/component-types").json()
    tampo_id = next(c["id"] for c in component_types if c["name"] == "Tampo")

    estrutura_type = client.post(
        "/api/v1/catalog/component-types", json={"name": "Estrutura RN04 Teste B"}
    ).json()

    tampo_variant = _create_variant_with_price(
        client, component_id=tampo_id, descriptor="Tampo Inteiro RN04 Teste B", sku="TOP-RN04-B"
    )
    estrutura_variant = _create_variant_with_price(
        client,
        component_id=estrutura_type["id"],
        descriptor="Estrutura Reunião Tampo Inteiro RN04 Teste B",
        sku="EST-RN04-B",
    )

    rule = client.post(
        "/api/v1/catalog/compatibility-rules",
        json={
            "component_a_id": tampo_id,
            "descriptor_a": "Tampo Inteiro RN04 Teste B",
            "component_b_id": estrutura_type["id"],
            "descriptor_b": "Estrutura Reunião Tampo Inteiro RN04 Teste B",
        },
    )
    assert rule.status_code == 201

    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()
    item = client.post(
        f"/api/v1/quotes/{quote['id']}/items",
        json={
            "component_variant_id": tampo_variant["component_variant_id"],
            "label": "Mesa Reunião RN04 Teste B",
            "quantity": 1,
        },
    ).json()

    response = client.post(
        f"/api/v1/quotes/{quote['id']}/items/{item['id']}/components",
        json={"component_variant_id": estrutura_variant["component_variant_id"]},
    )
    assert response.status_code == 201
    assert len(response.json()["components"]) == 2


def test_add_component_with_incompatible_descriptor_is_blocked(client) -> None:
    """RN-04: par com regra cadastrada, mas descritores não correspondem, é bloqueado."""
    component_types = client.get("/api/v1/catalog/component-types").json()
    tampo_id = next(c["id"] for c in component_types if c["name"] == "Tampo")

    estrutura_type = client.post(
        "/api/v1/catalog/component-types", json={"name": "Estrutura RN04 Teste C"}
    ).json()

    tampo_variant = _create_variant_with_price(
        client, component_id=tampo_id, descriptor="Tampo Inteiro RN04 Teste C", sku="TOP-RN04-C"
    )
    estrutura_compativel = _create_variant_with_price(
        client,
        component_id=estrutura_type["id"],
        descriptor="Estrutura Reunião Tampo Inteiro RN04 Teste C",
        sku="EST-RN04-C1",
    )
    estrutura_incompativel = _create_variant_with_price(
        client,
        component_id=estrutura_type["id"],
        descriptor="Estrutura Reunião Tampo Tri-Partido RN04 Teste C",
        sku="EST-RN04-C2",
    )

    rule = client.post(
        "/api/v1/catalog/compatibility-rules",
        json={
            "component_a_id": tampo_id,
            "descriptor_a": "Tampo Inteiro RN04 Teste C",
            "component_b_id": estrutura_type["id"],
            "descriptor_b": "Estrutura Reunião Tampo Inteiro RN04 Teste C",
        },
    )
    assert rule.status_code == 201

    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()
    item = client.post(
        f"/api/v1/quotes/{quote['id']}/items",
        json={
            "component_variant_id": tampo_variant["component_variant_id"],
            "label": "Mesa Reunião RN04 Teste C",
            "quantity": 1,
        },
    ).json()

    response = client.post(
        f"/api/v1/quotes/{quote['id']}/items/{item['id']}/components",
        json={"component_variant_id": estrutura_incompativel["component_variant_id"]},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "DESCRITOR_INCOMPATIVEL"

    # A variação compatível, por outro lado, é aceita.
    response = client.post(
        f"/api/v1/quotes/{quote['id']}/items/{item['id']}/components",
        json={"component_variant_id": estrutura_compativel["component_variant_id"]},
    )
    assert response.status_code == 201


def test_add_component_to_unknown_item_is_not_found(client) -> None:
    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()
    variant = _seeded_variant(client)

    response = client.post(
        f"/api/v1/quotes/{quote['id']}/items/999999/components",
        json={"component_variant_id": variant["component_variant_id"]},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ITEM_NAO_ENCONTRADO"


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


# ---------------------------------------------------------------------------
# Composição completa na criação (components[], docs/06 §14.11)
# ---------------------------------------------------------------------------


def test_create_item_with_multiple_components(client) -> None:
    component_types = client.get("/api/v1/catalog/component-types").json()
    tampo_id = next(c["id"] for c in component_types if c["name"] == "Tampo")

    tampo_a = _create_variant_with_price(
        client, component_id=tampo_id, descriptor="Tampo Multi A", sku="TOP-MULTI-A", amount=100
    )
    tampo_b = _create_variant_with_price(
        client, component_id=tampo_id, descriptor="Tampo Multi B", sku="TOP-MULTI-B", amount=150
    )

    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()
    response = client.post(
        f"/api/v1/quotes/{quote['id']}/items",
        json={
            "label": "Mesa Reunião 1200x900 — composição",
            "quantity": 1,
            "components": [
                {"component_variant_id": tampo_a["component_variant_id"]},
                {"component_variant_id": tampo_b["component_variant_id"]},
            ],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body["components"]) == 2
    assert {c["component_variant_id"] for c in body["components"]} == {
        tampo_a["component_variant_id"],
        tampo_b["component_variant_id"],
    }
    expected_subtotal = tampo_a["price"]["amount"] + tampo_b["price"]["amount"]
    assert body["line_subtotal"] == round(expected_subtotal, 2)


def test_create_item_without_component_variant_id_or_components_is_blocked(client) -> None:
    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()

    response = client.post(
        f"/api/v1/quotes/{quote['id']}/items",
        json={"label": "Sem componentes", "quantity": 1},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CAMPO_OBRIGATORIO_AUSENTE"


def test_create_item_with_components_validates_rn04(client) -> None:
    component_types = client.get("/api/v1/catalog/component-types").json()
    tampo_id = next(c["id"] for c in component_types if c["name"] == "Tampo")

    estrutura_type = client.post(
        "/api/v1/catalog/component-types", json={"name": "Estrutura RN04 Teste D"}
    ).json()

    tampo_variant = _create_variant_with_price(
        client, component_id=tampo_id, descriptor="Tampo Inteiro RN04 Teste D", sku="TOP-RN04-D"
    )
    estrutura_incompativel = _create_variant_with_price(
        client,
        component_id=estrutura_type["id"],
        descriptor="Estrutura Reunião Tampo Tri-Partido RN04 Teste D",
        sku="EST-RN04-D",
    )

    client.post(
        "/api/v1/catalog/compatibility-rules",
        json={
            "component_a_id": tampo_id,
            "descriptor_a": "Tampo Inteiro RN04 Teste D",
            "component_b_id": estrutura_type["id"],
            "descriptor_b": "Estrutura Reunião Tampo Inteiro RN04 Teste D",
        },
    )

    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()
    response = client.post(
        f"/api/v1/quotes/{quote['id']}/items",
        json={
            "label": "Mesa Reunião RN04 Teste D",
            "quantity": 1,
            "components": [
                {"component_variant_id": tampo_variant["component_variant_id"]},
                {"component_variant_id": estrutura_incompativel["component_variant_id"]},
            ],
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "DESCRITOR_INCOMPATIVEL"


# ---------------------------------------------------------------------------
# Troca de variação com recongelamento (docs/06 §14.12)
# ---------------------------------------------------------------------------


def test_swap_component_variant_recongela_preco(client) -> None:
    component_types = client.get("/api/v1/catalog/component-types").json()
    tampo_id = next(c["id"] for c in component_types if c["name"] == "Tampo")

    tampo_a = _create_variant_with_price(
        client, component_id=tampo_id, descriptor="Tampo Swap A", sku="TOP-SWAP-A", amount=100
    )
    tampo_b = _create_variant_with_price(
        client, component_id=tampo_id, descriptor="Tampo Swap B", sku="TOP-SWAP-B", amount=150
    )

    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()
    item = client.post(
        f"/api/v1/quotes/{quote['id']}/items",
        json={
            "component_variant_id": tampo_a["component_variant_id"],
            "label": "Mesa Reunião — Tampo Swap A",
            "quantity": 1,
        },
    ).json()
    component_id = item["components"][0]["id"]
    previous_price = item["components"][0]["frozen_unit_price"]

    response = client.patch(
        f"/api/v1/quotes/{quote['id']}/items/{item['id']}/components/{component_id}",
        json={"component_variant_id": tampo_b["component_variant_id"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["component_variant_id"] == tampo_b["component_variant_id"]
    assert body["sku"] == tampo_b["sku"]
    assert body["previous_frozen_unit_price"] == previous_price
    assert body["frozen_unit_price"] == tampo_b["price"]["amount"]
    assert body["price_changed"] is True

    updated_item = client.get(f"/api/v1/quotes/{quote['id']}/items/{item['id']}").json()
    assert updated_item["components"][0]["frozen_unit_price"] == tampo_b["price"]["amount"]


def test_swap_component_variant_to_different_component_type_is_blocked(client) -> None:
    component_types = client.get("/api/v1/catalog/component-types").json()
    tampo_id = next(c["id"] for c in component_types if c["name"] == "Tampo")

    tampo = _create_variant_with_price(
        client, component_id=tampo_id, descriptor="Tampo SWAP Teste", sku="TOP-SWAP-TESTE"
    )

    estrutura_type = client.post(
        "/api/v1/catalog/component-types", json={"name": "Estrutura SWAP Teste"}
    ).json()
    estrutura_variant = _create_variant_with_price(
        client,
        component_id=estrutura_type["id"],
        descriptor="Estrutura SWAP Teste",
        sku="EST-SWAP-TESTE",
    )

    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()
    item = client.post(
        f"/api/v1/quotes/{quote['id']}/items",
        json={
            "component_variant_id": tampo["component_variant_id"],
            "label": "Mesa Reunião — Tampo SWAP Teste",
            "quantity": 1,
        },
    ).json()
    component_id = item["components"][0]["id"]

    response = client.patch(
        f"/api/v1/quotes/{quote['id']}/items/{item['id']}/components/{component_id}",
        json={"component_variant_id": estrutura_variant["component_variant_id"]},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VARIACAO_INCOMPATIVEL"


def test_swap_unknown_component_is_not_found(client) -> None:
    component_types = client.get("/api/v1/catalog/component-types").json()
    tampo_id = next(c["id"] for c in component_types if c["name"] == "Tampo")

    tampo_a = _create_variant_with_price(
        client, component_id=tampo_id, descriptor="Tampo Swap C", sku="TOP-SWAP-C"
    )
    tampo_b = _create_variant_with_price(
        client, component_id=tampo_id, descriptor="Tampo Swap D", sku="TOP-SWAP-D"
    )

    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()
    item = client.post(
        f"/api/v1/quotes/{quote['id']}/items",
        json={
            "component_variant_id": tampo_a["component_variant_id"],
            "label": "Mesa Reunião — Tampo Swap C",
            "quantity": 1,
        },
    ).json()

    response = client.patch(
        f"/api/v1/quotes/{quote['id']}/items/{item['id']}/components/999999",
        json={"component_variant_id": tampo_b["component_variant_id"]},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "COMPONENTE_NAO_ENCONTRADO"


# ---------------------------------------------------------------------------
# Remoção de itens e componentes (Telas 7/8, docs/04 §7/§8)
# ---------------------------------------------------------------------------


def test_remove_item_deletes_line(client) -> None:
    variant = _seeded_variant(client)

    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()
    item = client.post(
        f"/api/v1/quotes/{quote['id']}/items",
        json={
            "component_variant_id": variant["component_variant_id"],
            "label": "Mesa Reunião — remoção de linha",
            "quantity": 1,
        },
    ).json()

    response = client.delete(f"/api/v1/quotes/{quote['id']}/items/{item['id']}")
    assert response.status_code == 204

    items = client.get(f"/api/v1/quotes/{quote['id']}/items").json()
    assert items == []


def test_remove_unknown_item_is_not_found(client) -> None:
    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()

    response = client.delete(f"/api/v1/quotes/{quote['id']}/items/999999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ITEM_NAO_ENCONTRADO"


def test_remove_component_from_multi_component_item(client) -> None:
    component_types = client.get("/api/v1/catalog/component-types").json()
    tampo_id = next(c["id"] for c in component_types if c["name"] == "Tampo")

    tampo_a = _create_variant_with_price(
        client, component_id=tampo_id, descriptor="Tampo Remove A", sku="TOP-REMOVE-A", amount=100
    )
    tampo_b = _create_variant_with_price(
        client, component_id=tampo_id, descriptor="Tampo Remove B", sku="TOP-REMOVE-B", amount=150
    )

    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()
    item = client.post(
        f"/api/v1/quotes/{quote['id']}/items",
        json={
            "label": "Mesa Reunião — remoção de componente",
            "quantity": 1,
            "components": [
                {"component_variant_id": tampo_a["component_variant_id"]},
                {"component_variant_id": tampo_b["component_variant_id"]},
            ],
        },
    ).json()
    component_to_remove = item["components"][1]["id"]

    response = client.delete(
        f"/api/v1/quotes/{quote['id']}/items/{item['id']}/components/{component_to_remove}"
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["components"]) == 1
    assert body["components"][0]["component_variant_id"] == tampo_a["component_variant_id"]
    assert body["line_subtotal"] == round(tampo_a["price"]["amount"], 2)


def test_remove_last_component_is_blocked(client) -> None:
    variant = _seeded_variant(client)

    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()
    item = client.post(
        f"/api/v1/quotes/{quote['id']}/items",
        json={
            "component_variant_id": variant["component_variant_id"],
            "label": "Mesa Reunião — único componente",
            "quantity": 1,
        },
    ).json()
    component_id = item["components"][0]["id"]

    response = client.delete(
        f"/api/v1/quotes/{quote['id']}/items/{item['id']}/components/{component_id}"
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ULTIMO_COMPONENTE_DA_LINHA"


# ---------------------------------------------------------------------------
# Composição mínima por família (RN-07, Fase 9)
# ---------------------------------------------------------------------------


def test_incomplete_composition_blocks_enviado_until_justified(client) -> None:
    family = client.post("/api/v1/catalog/families", json={"name": "Família RN07 Teste"}).json()
    product = client.post(
        "/api/v1/catalog/products",
        json={"family_id": family["id"], "name": "Produto RN07 Teste"},
    ).json()
    tampo_type = client.post(
        "/api/v1/catalog/component-types", json={"name": "Tampo RN07 Teste"}
    ).json()
    estrutura_type = client.post(
        "/api/v1/catalog/component-types", json={"name": "Estrutura RN07 Teste"}
    ).json()

    for component_type in (tampo_type, estrutura_type):
        rule = client.post(
            "/api/v1/catalog/family-component-requirements",
            json={
                "family_id": family["id"],
                "component_id": component_type["id"],
                "requirement": "obrigatorio",
            },
        )
        assert rule.status_code == 201

    tampo_variant = _create_variant_with_product(
        client,
        product_id=product["id"],
        component_id=tampo_type["id"],
        descriptor="Tampo RN07 Teste",
        sku="TOP-RN07",
    )

    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()
    item = client.post(
        f"/api/v1/quotes/{quote['id']}/items",
        json={
            "label": "Item RN07 Teste",
            "product_id": product["id"],
            "components": [{"component_variant_id": tampo_variant["component_variant_id"]}],
        },
    ).json()
    assert item["missing_required_components"] == ["Estrutura RN07 Teste"]

    blocked = client.patch(f"/api/v1/quotes/{quote['id']}", json={"status": "enviado"})
    assert blocked.status_code == 422
    assert blocked.json()["error"]["code"] == "COMPOSICAO_INCOMPLETA"
    details = blocked.json()["error"]["details"]
    assert details["items"][0]["item_id"] == item["id"]
    assert details["items"][0]["missing"] == ["Estrutura RN07 Teste"]

    patched = client.patch(
        f"/api/v1/quotes/{quote['id']}/items/{item['id']}",
        json={"composition_justification": "Cliente fornecerá a estrutura — uso da própria mesa existente."},
    )
    assert patched.status_code == 200
    assert patched.json()["composition_justification"] is not None
    assert patched.json()["missing_required_components"] == ["Estrutura RN07 Teste"]

    sent = client.patch(f"/api/v1/quotes/{quote['id']}", json={"status": "enviado"})
    assert sent.status_code == 200


def test_missing_required_components_cleared_after_adding_component(client) -> None:
    family = client.post("/api/v1/catalog/families", json={"name": "Família RN07 Teste B"}).json()
    product = client.post(
        "/api/v1/catalog/products",
        json={"family_id": family["id"], "name": "Produto RN07 Teste B"},
    ).json()
    tampo_type = client.post(
        "/api/v1/catalog/component-types", json={"name": "Tampo RN07 Teste B"}
    ).json()
    estrutura_type = client.post(
        "/api/v1/catalog/component-types", json={"name": "Estrutura RN07 Teste B"}
    ).json()

    for component_type in (tampo_type, estrutura_type):
        rule = client.post(
            "/api/v1/catalog/family-component-requirements",
            json={
                "family_id": family["id"],
                "component_id": component_type["id"],
                "requirement": "obrigatorio",
            },
        )
        assert rule.status_code == 201

    tampo_variant = _create_variant_with_product(
        client,
        product_id=product["id"],
        component_id=tampo_type["id"],
        descriptor="Tampo RN07 Teste B",
        sku="TOP-RN07-B",
    )
    estrutura_variant = _create_variant_with_product(
        client,
        product_id=product["id"],
        component_id=estrutura_type["id"],
        descriptor="Estrutura RN07 Teste B",
        sku="EST-RN07-B",
    )

    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()
    item = client.post(
        f"/api/v1/quotes/{quote['id']}/items",
        json={
            "label": "Item RN07 Teste B",
            "product_id": product["id"],
            "components": [{"component_variant_id": tampo_variant["component_variant_id"]}],
        },
    ).json()
    assert item["missing_required_components"] == ["Estrutura RN07 Teste B"]

    added = client.post(
        f"/api/v1/quotes/{quote['id']}/items/{item['id']}/components",
        json={"component_variant_id": estrutura_variant["component_variant_id"]},
    )
    assert added.status_code == 201
    assert added.json()["missing_required_components"] == []

    sent = client.patch(f"/api/v1/quotes/{quote['id']}", json={"status": "enviado"})
    assert sent.status_code == 200


def test_item_without_known_family_requirements_never_blocks_enviado(client) -> None:
    """Itens cuja família não tem exigências cadastradas (caso comum, sem
    requisitos conhecidos) nunca têm pendências e nunca bloqueiam o envio."""
    variant = _seeded_variant(client)

    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()
    item = client.post(
        f"/api/v1/quotes/{quote['id']}/items",
        json={
            "component_variant_id": variant["component_variant_id"],
            "label": "Item RN07 sem exigências",
            "quantity": 1,
        },
    ).json()
    assert item["missing_required_components"] == []

    sent = client.patch(f"/api/v1/quotes/{quote['id']}", json={"status": "enviado"})
    assert sent.status_code == 200


# ---------------------------------------------------------------------------
# Duplicação de orçamento (RN-17, Fase 9)
# ---------------------------------------------------------------------------


def test_duplicate_quote_clean_copy(client) -> None:
    variant = _seeded_variant(client)

    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()
    client.post(
        f"/api/v1/quotes/{quote['id']}/items",
        json={
            "component_variant_id": variant["component_variant_id"],
            "label": "Mesa Reunião 1200x900 — Carvalho",
            "quantity": 2,
        },
    )

    response = client.post(f"/api/v1/quotes/{quote['id']}/duplicate")
    assert response.status_code == 201

    duplicated = response.json()
    assert duplicated["id"] != quote["id"]
    assert duplicated["quote_number"] != quote["quote_number"]
    assert duplicated["status"] == "rascunho"
    assert duplicated["source_quote_id"] == quote["id"]
    assert duplicated["customer"]["id"] == quote["customer"]["id"]

    items = client.get(f"/api/v1/quotes/{duplicated['id']}/items").json()
    assert len(items) == 1
    assert items[0]["label"] == "Mesa Reunião 1200x900 — Carvalho"
    assert items[0]["quantity"] == 2
    assert items[0]["pricing_pendencias"] == []
    assert len(items[0]["components"]) == 1
    assert items[0]["components"][0]["component_variant_id"] == variant["component_variant_id"]


def test_duplicate_quote_flags_pricing_pendencia_when_repricing_fails(client) -> None:
    variant = _seeded_variant(client)

    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()
    client.post(
        f"/api/v1/quotes/{quote['id']}/items",
        json={
            "component_variant_id": variant["component_variant_id"],
            "label": "Mesa Reunião 1200x900 — Carvalho",
            "quantity": 1,
        },
    )

    # Publica uma nova tabela vigente sem preço cadastrado para essa variação
    with get_connection() as connection:
        connection.execute(
            "UPDATE price_tables SET status = 'substituida' WHERE status = 'vigente'"
        )
        connection.execute(
            "INSERT INTO price_tables (code, name, status) "
            "VALUES ('NOVA-VIGENTE-RN17', 'Nova', 'vigente')"
        )
        connection.commit()

    response = client.post(f"/api/v1/quotes/{quote['id']}/duplicate")
    assert response.status_code == 201
    duplicated = response.json()

    items = client.get(f"/api/v1/quotes/{duplicated['id']}/items").json()
    assert len(items) == 1
    assert items[0]["components"] == []
    assert len(items[0]["pricing_pendencias"]) == 1
    assert variant["sku"] in items[0]["pricing_pendencias"][0]

    # Pendência persiste em consultas subsequentes (não só na resposta da duplicação)
    refetched = client.get(f"/api/v1/quotes/{duplicated['id']}/items/{items[0]['id']}").json()
    assert refetched["pricing_pendencias"] == items[0]["pricing_pendencias"]


def test_duplicate_unknown_quote_is_not_found(client) -> None:
    response = client.post("/api/v1/quotes/999999/duplicate")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ORCAMENTO_NAO_ENCONTRADO"
