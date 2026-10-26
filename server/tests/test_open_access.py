"""The app has no accounts: every endpoint works with no sign-in, and the
old auth routes are gone."""

from fastapi.testclient import TestClient

from app.main import app


def test_endpoints_work_without_any_header() -> None:
    with TestClient(app) as c:
        assert c.get("/api/samples").status_code == 200
        assert c.get("/api/conversations").status_code == 200
        assert c.get("/api/health").status_code == 200


def test_auth_routes_are_gone() -> None:
    with TestClient(app) as c:
        for path in ("/api/auth/signup", "/api/auth/signin", "/api/auth/token", "/api/auth/me"):
            assert c.post(path, json={}).status_code in (404, 405)
