import pytest
from fastapi.testclient import TestClient

from app.db.connection import get_connection
from app.db.seed import SEED_USER_PASSWORD, seed
from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session", autouse=True)
def _seeded_catalog(client):
    with get_connection() as connection:
        seed(connection)


@pytest.fixture(scope="session", autouse=True)
def _logged_in_admin(client, _seeded_catalog):
    """A maioria dos testes existentes assume acesso total — autentica o
    cliente de testes como admin por padrão (cookie de sessão fica no
    cookie jar compartilhado do TestClient)."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "aprovador@helence.local", "password": SEED_USER_PASSWORD},
    )
    assert response.status_code == 200


def login_as(client, email: str) -> None:
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": SEED_USER_PASSWORD}
    )
    assert response.status_code == 200


@pytest.fixture
def as_role(client):
    """Faz login temporário com outro papel e restaura o admin ao final.

    Uso: ``as_role("vendedor@helence.local")``.
    """

    def _switch(email: str) -> TestClient:
        login_as(client, email)
        return client

    yield _switch

    login_as(client, "aprovador@helence.local")
