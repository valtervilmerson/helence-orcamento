"""Testes de integração de upload/listagem de importações (docs/06, 14.1/14.2).

Fase 4 (docs/07): apenas recebe e guarda o arquivo — nada é processado.
"""

PDF_BYTES = b"%PDF-1.4\n%fake pdf content for tests\n%%EOF"


def test_upload_pdf_creates_import(client) -> None:
    response = client.post(
        "/api/v1/imports",
        files={"file": ("tabela-precos.pdf", PDF_BYTES, "application/pdf")},
        data={"notes": "upload de teste"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["original_filename"] == "tabela-precos.pdf"
    assert body["status"] == "recebido"
    assert body["page_count"] is None
    assert body["notes"] == "upload de teste"
    assert len(body["file_hash"]) == 64


def test_upload_duplicate_pdf_is_blocked(client) -> None:
    first = client.post(
        "/api/v1/imports",
        files={"file": ("duplicado.pdf", PDF_BYTES + b"unique-marker", "application/pdf")},
    )
    assert first.status_code == 201
    existing_id = first.json()["id"]

    second = client.post(
        "/api/v1/imports",
        files={"file": ("duplicado-de-novo.pdf", PDF_BYTES + b"unique-marker", "application/pdf")},
    )

    assert second.status_code == 409
    body = second.json()
    assert body["error"]["code"] == "ARQUIVO_DUPLICADO"
    assert body["error"]["details"]["existing_import_id"] == existing_id


def test_upload_invalid_file_is_rejected(client) -> None:
    response = client.post(
        "/api/v1/imports",
        files={"file": ("nao-e-pdf.pdf", b"isto nao eh um pdf", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "ARQUIVO_INVALIDO"


def test_list_imports_returns_uploaded_file(client) -> None:
    upload = client.post(
        "/api/v1/imports",
        files={"file": ("listagem.pdf", PDF_BYTES + b"listagem-marker", "application/pdf")},
    )
    assert upload.status_code == 201
    import_id = upload.json()["id"]

    response = client.get("/api/v1/imports")

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    ids = [item["id"] for item in body["items"]]
    assert import_id in ids

    item = next(item for item in body["items"] if item["id"] == import_id)
    assert item["status"] == "recebido"
    assert item["items_extracted"] == 0
    assert item["items_pending_review"] == 0
    assert item["linked_price_table"] is None


def test_list_imports_filters_by_status(client) -> None:
    response = client.get("/api/v1/imports", params={"status": "concluido"})

    assert response.status_code == 200
    body = response.json()
    assert all(item["status"] == "concluido" for item in body["items"])


def test_list_imports_invalid_status_is_rejected(client) -> None:
    response = client.get("/api/v1/imports", params={"status": "inexistente"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "PARAMETRO_INVALIDO"
