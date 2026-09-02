from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_login_route_success(monkeypatch) -> None:
    class FakeSession:
        access_token = "access-token-123"
        refresh_token = "refresh-token-123"

    class FakeUser:
        id = "user-123"
        email = "user@example.com"

    class FakeAuth:
        @staticmethod
        def sign_in_with_password(payload):
            assert payload == {"email": "user@example.com", "password": "Password!123"}

            return type(
                "AuthResponse",
                (),
                {"user": FakeUser(), "session": FakeSession()},
            )()

    class FakeClient:
        auth = FakeAuth()

    monkeypatch.setattr("app.repositories.users.get_supabase_client", lambda: FakeClient())

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "Password!123"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "access-token-123"
    assert response.json()["refresh_token"] == "refresh-token-123"
    assert response.json()["token_type"] == "bearer"


def test_login_route_rejects_invalid_credentials(monkeypatch) -> None:
    class FakeAuth:
        @staticmethod
        def sign_in_with_password(payload):
            return type("AuthResponse", (), {"user": None, "session": None})()

    class FakeClient:
        auth = FakeAuth()

    monkeypatch.setattr("app.repositories.users.get_supabase_client", lambda: FakeClient())

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "Wrongpass!1"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_signup_password_requires_complexity() -> None:
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "new@example.com",
            "password": "short",
            "name": "Tester",
            "phone_number": "01012345678",
        },
    )

    assert response.status_code == 422
    assert "Password must be 8-16 characters long" in response.text


def test_login_route_translates_supabase_error_to_401(monkeypatch) -> None:
    class FakeAuth:
        @staticmethod
        def sign_in_with_password(payload):
            raise Exception("invalid_credentials")

    class FakeClient:
        auth = FakeAuth()

    monkeypatch.setattr("app.repositories.users.get_supabase_client", lambda: FakeClient())

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "Wrongpass!1"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_signup_route_translates_supabase_error_to_400(monkeypatch) -> None:
    class FakeAuth:
        @staticmethod
        def sign_up(payload):
            raise Exception("email_exists")

    class FakeClient:
        auth = FakeAuth()

    monkeypatch.setattr("app.repositories.users.get_supabase_client", lambda: FakeClient())

    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "exists@example.com",
            "password": "Password!123",
            "name": "Tester",
            "phone_number": "01012345678",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "User registration failed"
