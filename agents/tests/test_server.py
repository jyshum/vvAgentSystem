from fastapi.testclient import TestClient


def test_health_endpoint():
    from server import app
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_run_endpoint_requires_auth():
    from server import app
    client = TestClient(app)
    resp = client.post("/api/run", json={"client_id": "test"})
    assert resp.status_code == 401
