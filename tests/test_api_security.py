from fastapi.testclient import TestClient

from app import auth
from app.config import settings
from app.main import app


def test_listing_api_requires_admin():
    with TestClient(app) as client:
        response = client.get("/api/listings")
    assert response.status_code == 401


def test_admin_login_rejects_default_password_and_rate_limits(monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "changeme")
    auth._failed_logins.clear()
    with TestClient(app) as client:
        for _ in range(settings.admin_login_rate_limit):
            assert client.post("/api/admin/login", json={"password": "changeme"}).status_code == 401
        assert client.post("/api/admin/login", json={"password": "changeme"}).status_code == 429


def test_secure_cookie_when_forwarded_https(monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "a-long-test-password")
    auth._failed_logins.clear()
    with TestClient(app) as client:
        response = client.post(
            "/api/admin/login",
            json={"password": "a-long-test-password"},
            headers={"x-forwarded-proto": "https"},
        )
    assert response.status_code == 200
    assert "Secure" in response.headers["set-cookie"]


def test_authenticated_filters_endpoint(monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "another-long-test-password")
    auth._failed_logins.clear()
    with TestClient(app) as client:
        login = client.post("/api/admin/login", json={"password": "another-long-test-password"})
        assert login.status_code == 200
        response = client.get("/api/filters")
    assert response.status_code == 200
    assert "currencies" in response.json()
