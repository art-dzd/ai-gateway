from fastapi.testclient import TestClient

from ai_gateway.main import app


def test_healthz_ok() -> None:
    client = TestClient(app)
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

