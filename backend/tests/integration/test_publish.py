"""Testes de integração da publicação de importação (docs/06, 14.7;
docs/07, Fase 7).
"""

from app.db.connection import get_connection


def _create_import(file_marker: bytes) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO imported_files (file_path, file_hash, original_filename, status)
            VALUES (?, ?, ?, 'concluido')
            """,
            (f"data/uploads/{file_marker.hex()}.pdf", file_marker.hex(), "publicacao.pdf"),
        )
        import_id = int(cursor.lastrowid)
        connection.commit()
    return import_id


def _create_page(import_id: int, page_number: int = 1) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO imported_pages (imported_file_id, page_number, page_profile, section)
            VALUES (?, ?, 'tampo_padrao', 'Mesas de Reunião')
            """,
            (import_id, page_number),
        )
        page_id = int(cursor.lastrowid)
        connection.commit()
    return page_id


def _insert_item(
    page_id: int,
    *,
    review_status: str = "aprovado",
    family_raw: str | None = "Mesas de Reunião",
    product_context_raw: str | None = "Reunião Bistrô 1200x500",
    component_type_raw: str | None = "Estrutura",
    description_raw: str | None = "Estrutura Reunião Bistrô Pé Painel 1200x500x1000mm",
    dimension_raw: str | None = "1200x500x1000",
    finish_raw: str | None = "Argila",
    sku_raw: str | None = "3982550799",
    price_raw: str | None = "528,29",
) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO extracted_items (
                imported_page_id, family_raw, product_context_raw, component_type_raw,
                description_raw, dimension_raw, finish_raw, sku_raw, price_raw, currency,
                confidence, confidence_level, source_text, extraction_notes, review_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'BRL', 0.97, 'alta', 'origem teste', '[]', ?)
            """,
            (
                page_id,
                family_raw,
                product_context_raw,
                component_type_raw,
                description_raw,
                dimension_raw,
                finish_raw,
                sku_raw,
                price_raw,
                review_status,
            ),
        )
        item_id = int(cursor.lastrowid)
        connection.commit()
    return item_id


def test_publish_unknown_import_returns_404(client) -> None:
    response = client.post("/api/v1/imports/999999/publish", json={"confirm": True})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "REGISTRO_NAO_ENCONTRADO"


def test_publish_without_confirm_returns_422(client) -> None:
    import_id = _create_import(b"pub-confirm-marker")

    response = client.post(f"/api/v1/imports/{import_id}/publish", json={})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CONFIRMACAO_AUSENTE"


def test_publish_blocks_on_pending_review_items(client) -> None:
    import_id = _create_import(b"pub-pending-marker")
    page_id = _create_page(import_id)
    _insert_item(page_id, review_status="pendente")

    response = client.post(f"/api/v1/imports/{import_id}/publish", json={"confirm": True})

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "ITENS_PENDENTES_DE_REVISAO"
    assert body["error"]["details"]["pending_count"] == 1
    assert "review_url" in body["error"]["details"]


def test_publish_unknown_finish_returns_422(client) -> None:
    import_id = _create_import(b"pub-finish-marker")
    page_id = _create_page(import_id)
    _insert_item(
        page_id,
        finish_raw="Cor Inexistente XYZ",
        sku_raw="9999999999",
        price_raw="100,00",
    )

    response = client.post(f"/api/v1/imports/{import_id}/publish", json={"confirm": True})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ACABAMENTO_NAO_CADASTRADO"


def test_publish_full_flow_creates_catalog_entries_with_traceability(client) -> None:
    import_id = _create_import(b"pub-full-flow-marker")
    page_id = _create_page(import_id)
    item_id = _insert_item(page_id)

    response = client.post(f"/api/v1/imports/{import_id}/publish", json={"confirm": True})

    assert response.status_code == 200
    body = response.json()
    assert body["imported_file_id"] == import_id
    assert body["items_published"] == 1

    search = client.get("/api/v1/components", params={"product": "Reunião Bistrô 1200x500"})
    assert search.status_code == 200
    search_body = search.json()
    assert search_body["total"] == 1
    item = search_body["items"][0]
    assert item["family"] == "Mesas de Reunião"
    assert item["component"] == "Estrutura"
    assert item["dimension"] == {
        "width_mm": 1200,
        "depth_mm": 500,
        "diameter_mm": None,
        "height_mm": 1000,
        "raw_label": "1200x500x1000",
    }
    assert item["finish"] == "Argila"
    assert item["sku"] == "3982550799"
    assert item["price"]["amount"] == 528.29

    with get_connection() as connection:
        traced = connection.execute(
            """
            SELECT pr.source_extracted_item_id
            FROM prices pr
            JOIN component_variants cv ON cv.id = pr.component_variant_id
            JOIN skus s ON s.id = pr.sku_id
            WHERE s.code = '3982550799'
            """,
        ).fetchone()
    assert traced["source_extracted_item_id"] == item_id

    # Republicar a mesma importação é idempotente (upsert do preço).
    repeat = client.post(f"/api/v1/imports/{import_id}/publish", json={"confirm": True})
    assert repeat.status_code == 200
    assert repeat.json()["items_published"] == 1
