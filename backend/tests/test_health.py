from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_health_check() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_current_user_requires_access_token() -> None:
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Bearer access token is required"
