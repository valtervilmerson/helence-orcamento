import pytest
from fastapi.testclient import TestClient

from app.db.connection import get_connection
from app.db.seed import seed
from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session", autouse=True)
def _seeded_catalog(client):
    with get_connection() as connection:
        seed(connection)
