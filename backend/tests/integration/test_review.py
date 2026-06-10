"""Testes de integração da revisão de itens extraídos (docs/06, 14.5/14.6;
docs/07, Fase 6).
"""

from app.db.connection import get_connection


def _create_import(file_marker: bytes) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO imported_files (file_path, file_hash, original_filename, status)
            VALUES (?, ?, ?, 'concluido')
            """,
            (f"data/uploads/{file_marker.hex()}.pdf", file_marker.hex(), "revisao.pdf"),
        )
        import_id = int(cursor.lastrowid)
        connection.commit()
    return import_id


def _create_page(import_id: int, page_number: int, page_profile: str = "tampo_padrao") -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO imported_pages (imported_file_id, page_number, page_profile, section)
            VALUES (?, ?, ?, 'Mesas de Reunião')
            """,
            (import_id, page_number, page_profile),
        )
        page_id = int(cursor.lastrowid)
        connection.commit()
    return page_id


def _insert_item(
    page_id: int,
    *,
    confidence: float = 0.95,
    confidence_level: str = "alta",
    review_status: str = "pendente",
    sku_raw: str | None = "3981130567",
    price_raw: str | None = "493,80",
    finish_raw: str | None = "Preto",
    component_type_raw: str | None = "Tampo",
    dimension_raw: str | None = "1200x900",
) -> int:
    with get_connection() as connection:
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
    return item_id


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
    import_id = _create_import(file_marker)
    page_id = _create_page(import_id, page_number)
    item_id = _insert_item(
        page_id,
        confidence=confidence,
        confidence_level=confidence_level,
        review_status=review_status,
        sku_raw=sku_raw,
        price_raw=price_raw,
        finish_raw=finish_raw,
        component_type_raw=component_type_raw,
        dimension_raw=dimension_raw,
    )
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


# ---------------------------------------------------------------------------
# Correção em lote (docs/04, seção 4 — fluxo de correção em lote)
# ---------------------------------------------------------------------------


def test_batch_preview_unknown_item_returns_404(client) -> None:
    response = client.get(
        "/api/v1/extracted-items/999999/batch-correction/preview",
        params={"field": "finish_raw", "scope": "page"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ITEM_NAO_ENCONTRADO"


def test_batch_preview_missing_params_returns_422(client) -> None:
    _, item_id = _create_import_with_item(file_marker=b"batch-missing-params-marker")

    response = client.get(f"/api/v1/extracted-items/{item_id}/batch-correction/preview")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CAMPO_OBRIGATORIO_AUSENTE"


def test_batch_preview_invalid_scope_returns_400(client) -> None:
    _, item_id = _create_import_with_item(file_marker=b"batch-invalid-scope-marker")

    response = client.get(
        f"/api/v1/extracted-items/{item_id}/batch-correction/preview",
        params={"field": "finish_raw", "scope": "galaxia"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "PARAMETRO_INVALIDO"


def test_batch_preview_non_correctable_field_returns_422(client) -> None:
    _, item_id = _create_import_with_item(file_marker=b"batch-bad-field-marker")

    response = client.get(
        f"/api/v1/extracted-items/{item_id}/batch-correction/preview",
        params={"field": "id", "scope": "page"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CAMPO_NAO_CORRIGIVEL"


def test_batch_preview_without_prior_correction_returns_422(client) -> None:
    _, item_id = _create_import_with_item(file_marker=b"batch-no-correction-marker")

    response = client.get(
        f"/api/v1/extracted-items/{item_id}/batch-correction/preview",
        params={"field": "finish_raw", "scope": "page"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CORRECAO_ORIGEM_NAO_ENCONTRADA"


def test_batch_preview_returns_eligible_and_already_decided_candidates(client) -> None:
    import_id = _create_import(b"batch-preview-marker")
    page_id = _create_page(import_id, page_number=4)
    item_a = _insert_item(page_id, finish_raw="Preto")
    item_b = _insert_item(page_id, finish_raw="Preto")
    item_c = _insert_item(page_id, finish_raw="Preto", review_status="aprovado")

    correct = client.post(
        f"/api/v1/extracted-items/{item_a}/review",
        json={"decision": "corrigido", "field": "finish_raw", "corrected_value": "Branco"},
    )
    assert correct.status_code == 200

    response = client.get(
        f"/api/v1/extracted-items/{item_a}/batch-correction/preview",
        params={"field": "finish_raw", "scope": "page"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["previous_value"] == "Preto"
    assert body["corrected_value"] == "Branco"
    assert body["scope"] == "page"
    assert body["eligible_count"] == 1
    assert [c["id"] for c in body["candidates"]] == [item_b]
    assert body["already_decided_count"] == 1
    assert body["already_decided_item_ids"] == [item_c]


def test_batch_apply_corrects_eligible_items_and_skips_already_decided(client) -> None:
    import_id = _create_import(b"batch-apply-marker")
    page_id = _create_page(import_id, page_number=5)
    item_a = _insert_item(page_id, finish_raw="Preto")
    item_b = _insert_item(page_id, finish_raw="Preto")
    item_c = _insert_item(page_id, finish_raw="Preto", review_status="aprovado")

    correct = client.post(
        f"/api/v1/extracted-items/{item_a}/review",
        json={"decision": "corrigido", "field": "finish_raw", "corrected_value": "Branco"},
    )
    assert correct.status_code == 200

    response = client.post(
        f"/api/v1/extracted-items/{item_a}/batch-correction/apply",
        json={"field": "finish_raw", "scope": "page", "notes": "Padronizando acabamento."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["previous_value"] == "Preto"
    assert body["corrected_value"] == "Branco"
    assert body["applied_count"] == 1
    assert body["applied_item_ids"] == [item_b]
    assert body["skipped_item_ids"] == [item_c]

    items = client.get(f"/api/v1/imports/{import_id}/items").json()["items"]
    item_b_out = next(i for i in items if i["id"] == item_b)
    assert item_b_out["finish_raw"] == "Branco"
    assert item_b_out["review_status"] == "corrigido"

    item_c_out = next(i for i in items if i["id"] == item_c)
    assert item_c_out["finish_raw"] == "Preto"
    assert item_c_out["review_status"] == "aprovado"


def test_batch_apply_scope_import_reaches_other_pages(client) -> None:
    import_id = _create_import(b"batch-apply-import-scope-marker")
    page_1 = _create_page(import_id, page_number=1, page_profile="tampo_padrao")
    page_2 = _create_page(import_id, page_number=2, page_profile="base_padrao")
    item_a = _insert_item(page_1, finish_raw="Preto")
    item_b = _insert_item(page_2, finish_raw="Preto")

    correct = client.post(
        f"/api/v1/extracted-items/{item_a}/review",
        json={"decision": "corrigido", "field": "finish_raw", "corrected_value": "Branco"},
    )
    assert correct.status_code == 200

    page_scope = client.get(
        f"/api/v1/extracted-items/{item_a}/batch-correction/preview",
        params={"field": "finish_raw", "scope": "page"},
    ).json()
    assert page_scope["eligible_count"] == 0

    import_scope = client.get(
        f"/api/v1/extracted-items/{item_a}/batch-correction/preview",
        params={"field": "finish_raw", "scope": "import"},
    ).json()
    assert import_scope["eligible_count"] == 1
    assert import_scope["candidates"][0]["id"] == item_b

    apply_response = client.post(
        f"/api/v1/extracted-items/{item_a}/batch-correction/apply",
        json={"field": "finish_raw", "scope": "import"},
    )
    assert apply_response.status_code == 200
    assert apply_response.json()["applied_item_ids"] == [item_b]


# ---------------------------------------------------------------------------
# Aprovação/rejeição em lote (docs/04, seção 3 — barra de ações em lote)
# ---------------------------------------------------------------------------


def test_batch_review_empty_selection_is_rejected(client) -> None:
    response = client.post(
        "/api/v1/extracted-items/batch-review",
        json={"item_ids": [], "decision": "aprovado"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "PARAMETRO_INVALIDO"


def test_batch_review_reject_without_notes_is_rejected(client) -> None:
    _, item_id = _create_import_with_item(file_marker=b"batch-review-no-notes-marker")

    response = client.post(
        "/api/v1/extracted-items/batch-review",
        json={"item_ids": [item_id], "decision": "rejeitado"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CAMPO_OBRIGATORIO_AUSENTE"


def test_batch_review_approve_multiple_items(client) -> None:
    import_id = _create_import(b"batch-review-approve-marker")
    page_id = _create_page(import_id, page_number=6)
    item_a = _insert_item(page_id, sku_raw="1111111111")
    item_b = _insert_item(page_id, sku_raw="2222222222")

    response = client.post(
        "/api/v1/extracted-items/batch-review",
        json={"item_ids": [item_a, item_b], "decision": "aprovado"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["requested_count"] == 2
    assert body["succeeded_count"] == 2
    assert body["failed_count"] == 0
    assert all(r["success"] for r in body["results"])

    items = client.get(f"/api/v1/imports/{import_id}/items").json()["items"]
    assert all(i["review_status"] == "aprovado" for i in items if i["id"] in (item_a, item_b))


def test_batch_review_reports_partial_failures(client) -> None:
    import_id = _create_import(b"batch-review-partial-marker")
    page_id = _create_page(import_id, page_number=7)
    item_a = _insert_item(page_id, sku_raw="3333333333")
    item_b = _insert_item(page_id, sku_raw="4444444444", review_status="aprovado")

    response = client.post(
        "/api/v1/extracted-items/batch-review",
        json={
            "item_ids": [item_a, item_b, 999999],
            "decision": "rejeitado",
            "notes": "Lote inválido.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["requested_count"] == 3
    assert body["succeeded_count"] == 1
    assert body["failed_count"] == 2

    by_id = {r["item_id"]: r for r in body["results"]}
    assert by_id[item_a]["success"] is True
    assert by_id[item_b]["success"] is False
    assert by_id[item_b]["error_code"] == "STATUS_INVALIDO"
    assert by_id[999999]["success"] is False
    assert by_id[999999]["error_code"] == "ITEM_NAO_ENCONTRADO"

    items = client.get(f"/api/v1/imports/{import_id}/items").json()["items"]
    item_a_out = next(i for i in items if i["id"] == item_a)
    assert item_a_out["review_status"] == "rejeitado"
