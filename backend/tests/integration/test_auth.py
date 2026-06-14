from fastapi.testclient import TestClient

from app.db.seed import SEED_USER_PASSWORD
from app.main import app


def test_login_with_valid_credentials_returns_user() -> None:
    with TestClient(app) as fresh_client:
        response = fresh_client.post(
            "/api/v1/auth/login",
            json={"email": "aprovador@helence.local", "password": SEED_USER_PASSWORD},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "aprovador@helence.local"
    assert body["role"] == "admin"
    assert "password_hash" not in body


def test_login_with_invalid_password_returns_401() -> None:
    with TestClient(app) as fresh_client:
        response = fresh_client.post(
            "/api/v1/auth/login",
            json={"email": "aprovador@helence.local", "password": "senha-errada"},
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "CREDENCIAIS_INVALIDAS"


def test_me_requires_authentication() -> None:
    with TestClient(app) as fresh_client:
        response = fresh_client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NAO_AUTENTICADO"


def test_me_returns_logged_in_user(client) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "aprovador@helence.local"


def test_logout_clears_session() -> None:
    with TestClient(app) as fresh_client:
        login = fresh_client.post(
            "/api/v1/auth/login",
            json={"email": "aprovador@helence.local", "password": SEED_USER_PASSWORD},
        )
        assert login.status_code == 200

        logout = fresh_client.post("/api/v1/auth/logout")
        assert logout.status_code == 204

        me = fresh_client.get("/api/v1/auth/me")
        assert me.status_code == 401


def test_vendedor_cannot_create_catalog_family(client, as_role) -> None:
    as_role("vendedor@helence.local")

    response = client.post("/api/v1/catalog/families", json={"name": "Família de Teste"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSAO_NEGADA"


def test_importador_cannot_create_quote(client, as_role) -> None:
    as_role("importador@helence.local")

    response = client.post("/api/v1/quotes", json={"customer_id": 1})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSAO_NEGADA"


def test_vendedor_cannot_upload_import(client, as_role) -> None:
    as_role("vendedor@helence.local")

    response = client.post(
        "/api/v1/imports",
        files={"file": ("teste.xlsx", b"conteudo", "application/vnd.ms-excel")},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSAO_NEGADA"


def test_anonymous_cannot_list_quotes() -> None:
    with TestClient(app) as fresh_client:
        response = fresh_client.get("/api/v1/quotes")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NAO_AUTENTICADO"
