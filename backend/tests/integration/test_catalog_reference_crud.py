"""CRUD das entidades de referência do catálogo manual (docs/07, Fase 2)."""


def test_families_crud_lifecycle(client) -> None:
    create = client.post(
        "/api/v1/catalog/families",
        json={"name": "Família CRUD Teste", "description": "Criada em teste"},
    )
    assert create.status_code == 201
    family = create.json()
    family_id = family["id"]
    assert family["name"] == "Família CRUD Teste"

    listing = client.get("/api/v1/catalog/families")
    assert listing.status_code == 200
    assert any(item["id"] == family_id for item in listing.json())

    detail = client.get(f"/api/v1/catalog/families/{family_id}")
    assert detail.status_code == 200
    assert detail.json()["name"] == "Família CRUD Teste"

    patched = client.patch(
        f"/api/v1/catalog/families/{family_id}", json={"description": "Atualizada"}
    )
    assert patched.status_code == 200
    assert patched.json()["description"] == "Atualizada"
    assert patched.json()["name"] == "Família CRUD Teste"

    deleted = client.delete(f"/api/v1/catalog/families/{family_id}")
    assert deleted.status_code == 204

    not_found = client.get(f"/api/v1/catalog/families/{family_id}")
    assert not_found.status_code == 404
    assert not_found.json()["error"]["code"] == "REGISTRO_NAO_ENCONTRADO"


def test_families_duplicate_name_returns_409(client) -> None:
    payload = {"name": "Família Duplicada Teste"}

    first = client.post("/api/v1/catalog/families", json=payload)
    assert first.status_code == 201

    second = client.post("/api/v1/catalog/families", json=payload)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "REGISTRO_DUPLICADO"


def test_dimensions_crud_lifecycle(client) -> None:
    create = client.post(
        "/api/v1/catalog/dimensions",
        json={"width_mm": 1500, "depth_mm": 700, "raw_label": "1500x700"},
    )
    assert create.status_code == 201
    dimension_id = create.json()["id"]

    detail = client.get(f"/api/v1/catalog/dimensions/{dimension_id}")
    assert detail.status_code == 200
    assert detail.json()["width_mm"] == 1500

    deleted = client.delete(f"/api/v1/catalog/dimensions/{dimension_id}")
    assert deleted.status_code == 204


def test_finishes_crud_lifecycle(client) -> None:
    create = client.post(
        "/api/v1/catalog/finishes",
        json={"name": "Acabamento CRUD Teste", "finish_group": "metalico"},
    )
    assert create.status_code == 201
    finish = create.json()
    assert finish["finish_group"] == "metalico"

    deleted = client.delete(f"/api/v1/catalog/finishes/{finish['id']}")
    assert deleted.status_code == 204


def test_component_types_crud_lifecycle(client) -> None:
    create = client.post("/api/v1/catalog/component-types", json={"name": "Componente CRUD Teste"})
    assert create.status_code == 201
    component = create.json()

    deleted = client.delete(f"/api/v1/catalog/component-types/{component['id']}")
    assert deleted.status_code == 204


def test_products_requires_valid_family(client) -> None:
    response = client.post(
        "/api/v1/catalog/products", json={"family_id": 999999, "name": "Produto Sem Família"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REFERENCIA_INVALIDA"


def test_products_crud_lifecycle(client) -> None:
    family = client.post(
        "/api/v1/catalog/families", json={"name": "Família Para Produto Teste"}
    ).json()

    create = client.post(
        "/api/v1/catalog/products",
        json={"family_id": family["id"], "name": "Produto CRUD Teste"},
    )
    assert create.status_code == 201
    product = create.json()
    assert product["family_id"] == family["id"]

    patched = client.patch(
        f"/api/v1/catalog/products/{product['id']}", json={"name": "Produto CRUD Atualizado"}
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Produto CRUD Atualizado"

    deleted = client.delete(f"/api/v1/catalog/products/{product['id']}")
    assert deleted.status_code == 204

    deleted_family = client.delete(f"/api/v1/catalog/families/{family['id']}")
    assert deleted_family.status_code == 204
