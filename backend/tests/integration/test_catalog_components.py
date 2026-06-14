"""Endpoints de busca e CRUD de variações vendáveis (docs/06, 14.8/14.9)."""

from app.db.connection import get_connection
from app.db.seed import SEED_CUSTOMER_NAME


def _customer_id() -> int:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id FROM customers WHERE name = ?", (SEED_CUSTOMER_NAME,)
        ).fetchone()
        return row["id"]


def test_search_returns_seeded_variants(client) -> None:
    response = client.get("/api/v1/components", params={"family": "Mesas de Reunião"})
    assert response.status_code == 200

    body = response.json()
    assert body["total"] == 9
    assert body["page"] == 1
    assert body["page_size"] == 50

    item = body["items"][0]
    assert item["family"] == "Mesas de Reunião"
    assert item["product"] == "Reunião 1200x900"
    assert item["component"] == "Tampo"
    assert item["dimension"] == {
        "width_mm": 1200,
        "depth_mm": 900,
        "diameter_mm": None,
        "height_mm": None,
        "raw_label": "1200x900",
    }
    assert item["price"]["currency"] == "BRL"
    assert item["source"] == "cadastro_manual"


def test_search_filters_by_finish_and_text(client) -> None:
    by_finish = client.get("/api/v1/components", params={"finish": "Carvalho"})
    assert by_finish.status_code == 200
    assert by_finish.json()["total"] == 1
    assert by_finish.json()["items"][0]["sku"] == "3981144789"

    by_text = client.get("/api/v1/components", params={"q": "3981142345"})
    assert by_text.status_code == 200
    assert by_text.json()["total"] == 1
    assert by_text.json()["items"][0]["finish"] == "Amêndoa"


def test_search_combines_filters_as_intersection(client) -> None:
    combined = client.get(
        "/api/v1/components",
        params={
            "family": "Mesas de Reunião",
            "product": "Reunião 1200x900",
            "component": "Tampo",
            "dimension": "1200x900",
            "finish": "Carvalho",
        },
    )
    assert combined.status_code == 200
    body = combined.json()
    assert body["total"] == 1
    assert body["items"][0]["finish"] == "Carvalho"


def test_search_filter_combination_without_match_returns_empty(client) -> None:
    response = client.get(
        "/api/v1/components",
        params={"family": "Mesas de Reunião", "finish": "Inexistente"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_search_filters_by_finish_group(client) -> None:
    """RN-05 (camada 1): finish_group restringe os resultados pelo grupo do acabamento."""
    matching = client.get(
        "/api/v1/components",
        params={"family": "Mesas de Reunião", "finish": "Carvalho", "finish_group": "madeirado"},
    )
    assert matching.status_code == 200
    body = matching.json()
    assert body["total"] == 1
    assert body["items"][0]["finish_group"] == "madeirado"

    mismatched = client.get(
        "/api/v1/components",
        params={"family": "Mesas de Reunião", "finish": "Carvalho", "finish_group": "metalico"},
    )
    assert mismatched.status_code == 200
    assert mismatched.json()["total"] == 0


def test_get_component_includes_price(client) -> None:
    search = client.get("/api/v1/components", params={"finish": "Branco"})
    variant_id = search.json()["items"][0]["component_variant_id"]

    detail = client.get(f"/api/v1/components/{variant_id}")
    assert detail.status_code == 200

    body = detail.json()
    assert body["component_variant_id"] == variant_id
    assert body["price"]["amount"] == 374.45


def test_get_component_not_found(client) -> None:
    response = client.get("/api/v1/components/999999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "COMPONENTE_NAO_ENCONTRADO"


def test_create_component_with_sku_and_price(client) -> None:
    component_type = client.post(
        "/api/v1/catalog/component-types", json={"name": "Estrutura"}
    ).json()

    products = client.get("/api/v1/catalog/products").json()
    product_id = next(p["id"] for p in products if p["name"] == "Reunião 1200x900")

    dimensions = client.get("/api/v1/catalog/dimensions").json()
    dimension_id = next(d["id"] for d in dimensions if d["raw_label"] == "1200x900")

    finishes = client.get("/api/v1/catalog/finishes").json()
    finish_id = next(f["id"] for f in finishes if f["name"] == "Carvalho")

    payload = {
        "product_id": product_id,
        "component_id": component_type["id"],
        "dimension_id": dimension_id,
        "finish_id": finish_id,
        "descriptor": "Inteiro Simples",
        "description": "Cadastro manual — confirmação telefônica com o fabricante",
        "sku": {"code": "9999999999", "notes": "Novo código informado pelo fabricante"},
        "price": {"amount": 510.00, "currency": "BRL"},
    }

    create = client.post("/api/v1/components", json=payload)
    assert create.status_code == 201

    body = create.json()
    assert body["component"] == "Estrutura"
    assert body["sku"] == "9999999999"
    assert body["price"] == {"amount": 510.00, "currency": "BRL"}
    assert body["source"] == "cadastro_manual"

    # mesma combinação produto+componente+dimensão+acabamento+descritor -> duplicada
    duplicate = client.post("/api/v1/components", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "VARIACAO_DUPLICADA"


def test_create_component_invalid_reference(client) -> None:
    response = client.post("/api/v1/components", json={"component_id": 999999})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REFERENCIA_INVALIDA"


def test_patch_component_updates_descriptor(client) -> None:
    component_type = client.post(
        "/api/v1/catalog/component-types", json={"name": "Acessório PATCH Teste"}
    ).json()

    create = client.post(
        "/api/v1/components",
        json={"component_id": component_type["id"], "descriptor": "Original"},
    )
    variant_id = create.json()["component_variant_id"]

    patched = client.patch(f"/api/v1/components/{variant_id}", json={"descriptor": "Atualizado"})
    assert patched.status_code == 200
    assert patched.json()["descriptor"] == "Atualizado"


def test_delete_component_without_references(client) -> None:
    component_type = client.post(
        "/api/v1/catalog/component-types", json={"name": "Acessório DELETE Teste"}
    ).json()

    create = client.post(
        "/api/v1/components",
        json={"component_id": component_type["id"], "descriptor": "Para remover"},
    )
    variant_id = create.json()["component_variant_id"]

    deleted = client.delete(f"/api/v1/components/{variant_id}")
    assert deleted.status_code == 204

    not_found = client.get(f"/api/v1/components/{variant_id}")
    assert not_found.status_code == 404


def test_delete_component_blocked_when_in_use(client) -> None:
    search = client.get("/api/v1/components", params={"finish": "Preto"})
    item = search.json()["items"][0]
    variant_id = item["component_variant_id"]

    quote = client.post("/api/v1/quotes", json={"customer_id": _customer_id()}).json()
    client.post(
        f"/api/v1/quotes/{quote['id']}/items",
        json={
            "component_variant_id": variant_id,
            "label": "Item em uso",
            "quantity": 1,
        },
    )

    response = client.delete(f"/api/v1/components/{variant_id}")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "COMPONENTE_EM_USO"
    assert "quote_item_components" in response.json()["error"]["details"]["referenced_by"]


# ---------------------------------------------------------------------------
# Regras de compatibilidade entre componentes (RN-04, Fase 9)
# ---------------------------------------------------------------------------


def test_create_and_list_compatibility_rule(client) -> None:
    tampo = client.post(
        "/api/v1/catalog/component-types", json={"name": "Tampo RN04 CRUD Teste"}
    ).json()
    estrutura = client.post(
        "/api/v1/catalog/component-types", json={"name": "Estrutura RN04 CRUD Teste"}
    ).json()

    created = client.post(
        "/api/v1/catalog/compatibility-rules",
        json={
            "component_a_id": tampo["id"],
            "descriptor_a": "Inteiro",
            "component_b_id": estrutura["id"],
            "descriptor_b": "Reunião Tampo Inteiro",
            "notes": "RN-04 — inferido da nomenclatura da tabela 01-2026",
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["descriptor_a"] == "Inteiro"
    assert body["descriptor_b"] == "Reunião Tampo Inteiro"

    listed = client.get("/api/v1/catalog/compatibility-rules").json()
    assert any(rule["id"] == body["id"] for rule in listed)


def test_create_compatibility_rule_invalid_reference(client) -> None:
    response = client.post(
        "/api/v1/catalog/compatibility-rules",
        json={
            "component_a_id": 999999,
            "descriptor_a": "Inteiro",
            "component_b_id": 999999,
            "descriptor_b": "Reunião Tampo Inteiro",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REFERENCIA_INVALIDA"


# ---------------------------------------------------------------------------
# Composição mínima por família (RN-07, Fase 9)
# ---------------------------------------------------------------------------


def test_family_component_requirements_crud_lifecycle(client) -> None:
    family = client.post(
        "/api/v1/catalog/families", json={"name": "Família RN07 CRUD Teste"}
    ).json()
    component = client.post(
        "/api/v1/catalog/component-types", json={"name": "Componente RN07 CRUD Teste"}
    ).json()

    created = client.post(
        "/api/v1/catalog/family-component-requirements",
        json={
            "family_id": family["id"],
            "component_id": component["id"],
            "requirement": "obrigatorio",
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["requirement"] == "obrigatorio"

    listed = client.get("/api/v1/catalog/family-component-requirements").json()
    assert any(item["id"] == body["id"] for item in listed)

    patched = client.patch(
        f"/api/v1/catalog/family-component-requirements/{body['id']}",
        json={"requirement": "opcional"},
    )
    assert patched.status_code == 200
    assert patched.json()["requirement"] == "opcional"

    duplicate = client.post(
        "/api/v1/catalog/family-component-requirements",
        json={
            "family_id": family["id"],
            "component_id": component["id"],
            "requirement": "obrigatorio",
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "REGISTRO_DUPLICADO"

    deleted = client.delete(f"/api/v1/catalog/family-component-requirements/{body['id']}")
    assert deleted.status_code == 204


def test_family_component_requirements_invalid_reference(client) -> None:
    response = client.post(
        "/api/v1/catalog/family-component-requirements",
        json={"family_id": 999999, "component_id": 999999, "requirement": "obrigatorio"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REFERENCIA_INVALIDA"


# ---------------------------------------------------------------------------
# Composição de produtos
# ---------------------------------------------------------------------------


def test_composition_items_lifecycle(client) -> None:
    products = client.get("/api/v1/catalog/products").json()
    product_id = next(p["id"] for p in products if p["name"] == "Reunião 1200x900")

    search = client.get("/api/v1/components", params={"product": "Reunião 1200x900"})
    variants = search.json()["items"]
    tampo_id = next(v["component_variant_id"] for v in variants if v["component"] == "Tampo")
    estrutura_id = next(
        (v["component_variant_id"] for v in variants if v["component"] == "Estrutura"),
        None,
    )

    empty = client.get(f"/api/v1/catalog/products/{product_id}/composition-items")
    assert empty.status_code == 200
    assert empty.json() == []

    created = client.post(
        f"/api/v1/catalog/products/{product_id}/composition-items",
        json={"component_variant_id": tampo_id, "quantity": 1},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["product_id"] == product_id
    assert body["quantity"] == 1
    assert body["variant"]["component_variant_id"] == tampo_id
    assert body["variant"]["component"] == "Tampo"

    if estrutura_id is not None:
        client.post(
            f"/api/v1/catalog/products/{product_id}/composition-items",
            json={"component_variant_id": estrutura_id, "quantity": 1},
        )

    listed = client.get(f"/api/v1/catalog/products/{product_id}/composition-items")
    assert listed.status_code == 200
    listed_ids = {item["variant"]["component_variant_id"] for item in listed.json()}
    assert tampo_id in listed_ids

    duplicate = client.post(
        f"/api/v1/catalog/products/{product_id}/composition-items",
        json={"component_variant_id": tampo_id, "quantity": 1},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "REGISTRO_DUPLICADO"

    deleted = client.delete(f"/api/v1/catalog/products/{product_id}/composition-items/{tampo_id}")
    assert deleted.status_code == 204

    after_delete = client.get(f"/api/v1/catalog/products/{product_id}/composition-items")
    after_ids = {item["variant"]["component_variant_id"] for item in after_delete.json()}
    assert tampo_id not in after_ids


def test_composition_items_product_not_found(client) -> None:
    response = client.get("/api/v1/catalog/products/999999/composition-items")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "REGISTRO_NAO_ENCONTRADO"


def test_composition_items_invalid_variant(client) -> None:
    products = client.get("/api/v1/catalog/products").json()
    product_id = next(p["id"] for p in products if p["name"] == "Reunião 1200x900")

    response = client.post(
        f"/api/v1/catalog/products/{product_id}/composition-items",
        json={"component_variant_id": 999999, "quantity": 1},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "COMPONENTE_NAO_ENCONTRADO"


def test_composition_items_remove_not_found(client) -> None:
    products = client.get("/api/v1/catalog/products").json()
    product_id = next(p["id"] for p in products if p["name"] == "Reunião 1200x900")

    response = client.delete(f"/api/v1/catalog/products/{product_id}/composition-items/999999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "REGISTRO_NAO_ENCONTRADO"


def test_composition_expand_no_subcomposition(client) -> None:
    families = client.get("/api/v1/catalog/families").json()
    family_id = next(f["id"] for f in families if f["name"] == "Mesas de Reunião")

    product = client.post(
        "/api/v1/catalog/products",
        json={"family_id": family_id, "name": "Produto sem composição"},
    ).json()

    response = client.get(f"/api/v1/catalog/products/{product['id']}/composition")
    assert response.status_code == 200
    assert response.json() == []


def test_composition_expand_recursive(client) -> None:
    families = client.get("/api/v1/catalog/families").json()
    family_id = next(f["id"] for f in families if f["name"] == "Mesas de Reunião")

    components = client.get("/api/v1/catalog/component-types").json()
    component_id = components[0]["id"]

    product_b = client.post(
        "/api/v1/catalog/products",
        json={"family_id": family_id, "name": "Produto B (sub-composição)"},
    ).json()
    product_a = client.post(
        "/api/v1/catalog/products",
        json={"family_id": family_id, "name": "Produto A (composição recursiva)"},
    ).json()

    variant_b1 = client.post(
        "/api/v1/components",
        json={"product_id": product_b["id"], "component_id": component_id, "descriptor": "B1"},
    ).json()
    variant_b2 = client.post(
        "/api/v1/components",
        json={"product_id": product_b["id"], "component_id": component_id, "descriptor": "B2"},
    ).json()
    variant_b_representative = client.post(
        "/api/v1/components",
        json={
            "product_id": product_b["id"],
            "component_id": component_id,
            "descriptor": "B-representante",
        },
    ).json()

    # Produto B é composto por dois itens (B1 e B2).
    client.post(
        f"/api/v1/catalog/products/{product_b['id']}/composition-items",
        json={"component_variant_id": variant_b1["component_variant_id"], "quantity": 1},
    )
    client.post(
        f"/api/v1/catalog/products/{product_b['id']}/composition-items",
        json={"component_variant_id": variant_b2["component_variant_id"], "quantity": 2},
    )

    # Produto A é composto por uma variação que pertence ao Produto B.
    client.post(
        f"/api/v1/catalog/products/{product_a['id']}/composition-items",
        json={
            "component_variant_id": variant_b_representative["component_variant_id"],
            "quantity": 3,
        },
    )

    response = client.get(f"/api/v1/catalog/products/{product_a['id']}/composition")
    assert response.status_code == 200
    body = response.json()

    expanded = {
        item["variant"]["component_variant_id"]: item["quantity"] for item in body
    }
    assert expanded == {
        variant_b1["component_variant_id"]: 3,
        variant_b2["component_variant_id"]: 6,
    }
