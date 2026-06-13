"""Testes de integração da ingestão via contrato JSON (docs/10; docs/07,
Fase 13).
"""

from app.db.connection import get_connection


def _payload(code: str, items: list[dict]) -> dict:
    return {
        "contract_version": "1.0",
        "price_table": {"code": code, "name": f"Tabela {code}"},
        "source": {"description": "teste", "generated_by": "pytest"},
        "items": items,
    }


def _item(**overrides) -> dict:
    base = {
        "ref": "TESTE!L1",
        "family": "Mesas de Reunião",
        "product_context": "Reunião 1200x900",
        "component_type": "Tampo",
        "description": "Tampo de teste",
        "dimension": "1200x900",
        "finish": "Argila",
        "sku": "JSONTEST0001",
        "price": 100.0,
        "currency": "BRL",
        "confidence": 0.97,
        "notes": None,
    }
    base.update(overrides)
    return base


def test_import_json_fast_path_publishes_to_catalog(client) -> None:
    payload = _payload("JSON-FASTPATH-01", [_item(sku="JSONTEST0001", price=111.50)])

    response = client.post("/api/v1/imports/json", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["items_total"] == 1
    assert body["items_published"] == 1
    assert body["items_pending_review"] == 0
    assert body["price_table"]["code"] == "JSON-FASTPATH-01"
    assert body["price_table"]["status"] == "rascunho"
    assert body["items"][0]["review_status"] == "aprovado"
    assert body["items"][0]["reasons"] is None

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT pr.amount, pr.source_extracted_item_id, s.code AS sku_code
            FROM prices pr
            JOIN skus s ON s.id = pr.sku_id
            JOIN price_tables pt ON pt.id = pr.price_table_id
            WHERE pt.code = 'JSON-FASTPATH-01'
            """,
        ).fetchone()
    assert row["sku_code"] == "JSONTEST0001"
    assert row["amount"] == 111.50
    assert row["source_extracted_item_id"] == body["items"][0]["extracted_item_id"]


def test_import_json_pending_for_new_entities(client) -> None:
    payload = _payload(
        "JSON-PENDING-COMP",
        [
            _item(
                sku="JSONTEST0002",
                component_type="Estrutura Apoio Credenza",
                finish="Prata",
                finish_group="metalico",
                confidence=0.85,
                notes="Tipo de componente e acabamento novos.",
            )
        ],
    )

    response = client.post("/api/v1/imports/json", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["items_published"] == 0
    assert body["items_pending_review"] == 1
    assert body["warnings_count"] >= 1
    item = body["items"][0]
    assert item["review_status"] == "pendente"
    assert any("Estrutura Apoio Credenza" in r for r in item["reasons"])
    assert any("Prata" in r for r in item["reasons"])


def test_import_json_pending_for_missing_confidence(client) -> None:
    payload = _payload("JSON-PENDING-CONF", [_item(sku="JSONTEST0003", confidence=None)])

    response = client.post("/api/v1/imports/json", json=payload)

    assert response.status_code == 201
    body = response.json()
    item = body["items"][0]
    assert item["review_status"] == "pendente"
    assert any("Confiança baixa" in r for r in item["reasons"])


def test_import_json_pending_for_notes(client) -> None:
    payload = _payload(
        "JSON-PENDING-NOTES",
        [_item(sku="JSONTEST0004", notes="Descrição remontada a partir de 3 linhas.")],
    )

    response = client.post("/api/v1/imports/json", json=payload)

    assert response.status_code == 201
    body = response.json()
    item = body["items"][0]
    assert item["review_status"] == "pendente"
    assert "Descrição remontada a partir de 3 linhas." in item["reasons"]


def test_import_json_duplicate_payload_returns_409(client) -> None:
    payload = _payload("JSON-DUP", [_item(sku="JSONTEST0005")])

    first = client.post("/api/v1/imports/json", json=payload)
    assert first.status_code == 201

    second = client.post("/api/v1/imports/json", json=payload)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "ARQUIVO_DUPLICADO"


def test_import_json_reuses_price_table_and_upserts_price(client) -> None:
    first_payload = _payload("JSON-REUSE", [_item(ref="TESTE!L1", sku="JSONTEST0006", price=100.0)])
    second_payload = _payload(
        "JSON-REUSE", [_item(ref="TESTE!L2", sku="JSONTEST0006", price=150.0)]
    )

    first = client.post("/api/v1/imports/json", json=first_payload)
    second = client.post("/api/v1/imports/json", json=second_payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["price_table"]["id"] == second.json()["price_table"]["id"]

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT pr.amount
            FROM prices pr
            JOIN skus s ON s.id = pr.sku_id
            JOIN price_tables pt ON pt.id = pr.price_table_id
            WHERE pt.code = 'JSON-REUSE' AND s.code = 'JSONTEST0006'
            """,
        ).fetchall()

    assert len(rows) == 1
    assert rows[0]["amount"] == 150.0
