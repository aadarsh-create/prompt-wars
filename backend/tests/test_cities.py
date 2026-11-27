from fastapi.testclient import TestClient

from app.main import app
from app.schemas import SUPPORTED_CITIES


def test_cities_endpoint_returns_backend_allowlist():
    with TestClient(app) as client:
        response = client.get("/api/cities")

    assert response.status_code == 200
    assert response.json() == {"cities": list(SUPPORTED_CITIES)}
