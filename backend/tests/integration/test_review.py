"""Testes de integração da revisão de itens extraídos (docs/06, 14.5/14.6;
docs/07, Fase 6).
"""

from app.db.connection import get_connection


def _create_import_with_item(
    *,
    file_marker: bytes,
    page_number: int = 2,
    confidence: float = 0.95,
    confidence_level: str = "alta",
    review_status: str = "pendente",
    sku_raw: str | None = "3981130567",
    price_raw: str | None = "493,80",
    finish_raw: str | None = "Preto",
    component_type_raw: str | None = "Tampo",
    dimension_raw: str | None = "1200x900",
) -> tuple[int, int]:
    """Insere uma importação + página + item extraído diretamente no banco
    (a extração de fato é escopo da Fase 5; aqui simulamos seu resultado).
    """
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO imported_files (file_path, file_hash, original_filename, status)
            VALUES (?, ?, ?, 'concluido')
            """,
            (f"data/uploads/{file_marker.hex()}.pdf", file_marker.hex(), "revisao.pdf"),
        )
        import_id = int(cursor.lastrowid)

        cursor = connection.execute(
            """
            INSERT INTO imported_pages (imported_file_id, page_number, page_profile, section)
            VALUES (?, ?, 'tampo_padrao', 'Mesas de Reunião')
            """,
            (import_id, page_number),
        )
        page_id = int(cursor.lastrowid)

        cursor = connection.execute(
            """
            INSERT INTO extracted_items (
                imported_page_id, family_raw, product_context_raw, component_type_raw,
                description_raw, dimension_raw, finish_raw, sku_raw, price_raw, currency,
                confidence, confidence_level, source_text, extraction_notes, review_status
            )
            VALUES (?, 'Mesas de Reunião', 'Reunião 1200x900', ?, 'Tampo Inteiro Simples',
                    ?, ?, ?, ?, 'BRL', ?, ?, 'Tampo Inteiro Simples 493,80', '[]', ?)
            """,
            (
                page_id,
                component_type_raw,
                dimension_raw,
                finish_raw,
                sku_raw,
                price_raw,
                confidence,
                confidence_level,
                review_status,
            ),
        )
        item_id = int(cursor.lastrowid)
        connection.commit()

    return import_id, item_id


# ---------------------------------------------------------------------------
# 14.5 — GET /api/v1/imports/{id}/items
# ---------------------------------------------------------------------------


def test_list_items_unknown_import_returns_404(client) -> None:
    response = client.get("/api/v1/imports/999999/items")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "IMPORTACAO_NAO_ENCONTRADA"


def test_list_items_returns_extracted_item(client) -> None:
    import_id, item_id = _create_import_with_item(file_marker=b"list-items-marker")

    response = client.get(f"/api/v1/imports/{import_id}/items")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = next(i for i in body["items"] if i["id"] == item_id)
    assert item["page_number"] == 2
    assert item["sku_raw"] == "3981130567"
    assert item["confidence_level"] == "alta"
    assert item["review_status"] == "pendente"


def test_list_items_filters_by_review_status(client) -> None:
    import_id, _ = _create_import_with_item(file_marker=b"filter-status-marker")

    response = client.get(
        f"/api/v1/imports/{import_id}/items", params={"review_status": "aprovado"}
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_list_items_invalid_review_status_is_rejected(client) -> None:
    import_id, _ = _create_import_with_item(file_marker=b"invalid-status-marker")

    response = client.get(
        f"/api/v1/imports/{import_id}/items", params={"review_status": "inexistente"}
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "PARAMETRO_INVALIDO"


def test_list_items_filters_by_confidence_level(client) -> None:
    import_id, item_id = _create_import_with_item(
        file_marker=b"confidence-marker", confidence=0.2, confidence_level="baixa"
    )

    response = client.get(
        f"/api/v1/imports/{import_id}/items", params={"confidence_level": "baixa"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == item_id


def test_list_items_search_matches_sku(client) -> None:
    import_id, item_id = _create_import_with_item(
        file_marker=b"search-marker", sku_raw="3981199999"
    )

    response = client.get(f"/api/v1/imports/{import_id}/items", params={"search": "3981199999"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == item_id


# ---------------------------------------------------------------------------
# 14.6 — POST /api/v1/extracted-items/{id}/review
# ---------------------------------------------------------------------------


def test_review_unknown_item_returns_404(client) -> None:
    response = client.post(
        "/api/v1/extracted-items/999999/review",
        json={"decision": "aprovado"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ITEM_NAO_ENCONTRADO"


def test_approve_item(client) -> None:
    _, item_id = _create_import_with_item(file_marker=b"approve-marker")

    response = client.post(
        f"/api/v1/extracted-items/{item_id}/review",
        json={"decision": "aprovado", "notes": "Conferido contra o PDF."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == item_id
    assert body["review_status"] == "aprovado"
    assert body["decision"]["decision"] == "aprovado"
    assert body["decision"]["field_corrected"] is None


def test_approve_already_decided_item_is_rejected(client) -> None:
    _, item_id = _create_import_with_item(file_marker=b"already-decided-marker")

    first = client.post(
        f"/api/v1/extracted-items/{item_id}/review",
        json={"decision": "aprovado"},
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/v1/extracted-items/{item_id}/review",
        json={"decision": "aprovado"},
    )

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "STATUS_INVALIDO"


def test_reject_item_requires_notes(client) -> None:
    _, item_id = _create_import_with_item(file_marker=b"reject-no-notes-marker")

    response = client.post(
        f"/api/v1/extracted-items/{item_id}/review",
        json={"decision": "rejeitado"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CAMPO_OBRIGATORIO_AUSENTE"


def test_reject_item_with_notes(client) -> None:
    _, item_id = _create_import_with_item(file_marker=b"reject-with-notes-marker")

    response = client.post(
        f"/api/v1/extracted-items/{item_id}/review",
        json={"decision": "rejeitado", "notes": "Linha duplicada."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["review_status"] == "rejeitado"
    assert body["decision"]["decision"] == "rejeitado"


def test_correct_item_field(client) -> None:
    import_id, item_id = _create_import_with_item(file_marker=b"correct-marker", price_raw=None)

    response = client.post(
        f"/api/v1/extracted-items/{item_id}/review",
        json={
            "decision": "corrigido",
            "field": "price_raw",
            "previous_value": None,
            "corrected_value": "412.90",
            "notes": "Valor confirmado na página seguinte.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["review_status"] == "corrigido"
    assert body["decision"]["field_corrected"] == "price_raw"
    assert body["decision"]["corrected_value"] == "412.90"

    items = client.get(f"/api/v1/imports/{import_id}/items", params={"search": "412.90"}).json()
    assert any(i["id"] == item_id and i["price_raw"] == "412.90" for i in items["items"])


def test_correct_item_missing_field_is_rejected(client) -> None:
    _, item_id = _create_import_with_item(file_marker=b"correct-missing-field-marker")

    response = client.post(
        f"/api/v1/extracted-items/{item_id}/review",
        json={"decision": "corrigido", "corrected_value": "412.90"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CAMPO_OBRIGATORIO_AUSENTE"


def test_correct_item_non_correctable_field_is_rejected(client) -> None:
    _, item_id = _create_import_with_item(file_marker=b"correct-bad-field-marker")

    response = client.post(
        f"/api/v1/extracted-items/{item_id}/review",
        json={"decision": "corrigido", "field": "id", "corrected_value": "999"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CAMPO_NAO_CORRIGIVEL"


def test_correct_price_with_non_numeric_value_is_rejected(client) -> None:
    _, item_id = _create_import_with_item(file_marker=b"correct-bad-price-marker")

    response = client.post(
        f"/api/v1/extracted-items/{item_id}/review",
        json={"decision": "corrigido", "field": "price_raw", "corrected_value": "abc"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALOR_INCOMPATIVEL"
