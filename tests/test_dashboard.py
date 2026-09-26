import os
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-at-least-32-bytes-long")
os.environ.setdefault("DEMO_PASSWORD_HASH", "$2b$12$LQv3c1yqBWxkQ5u7GQ0xqOe0bXn6H2KQj9yV4jG6Qk0kQxV7s6h9e")

from fastapi.testclient import TestClient
from dashboard.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_auth_rejects_unknown_user():
    with TestClient(app) as client:
        response = client.post("/api/auth/token", json={"username": "wrong", "password": "wrong"})
        assert response.status_code == 401
