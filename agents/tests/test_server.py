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


def test_schedules_endpoint_requires_auth():
    from server import app
    client = TestClient(app)
    resp = client.get("/api/schedules")
    assert resp.status_code == 401


def test_schedules_uses_started_at(monkeypatch):
    """The schedules endpoint must query pipeline_runs by started_at (created_at doesn't exist)."""
    import server as server_mod

    captured = {}

    class FakeQuery:
        def __init__(self, table):
            self.table = table
        def select(self, cols):
            captured[self.table] = cols
            return self
        def order(self, col, desc=False):
            captured[self.table + "_order"] = col
            return self
        def execute(self):
            return type("R", (), {"data": []})()

    class FakeSB:
        def table(self, name):
            return FakeQuery(name)

    monkeypatch.setattr(server_mod, "_get_supabase", lambda: FakeSB())

    client = TestClient(server_mod.app)
    resp = client.get("/api/schedules", headers={"Authorization": f"Bearer {server_mod.API_KEY}"})

    assert resp.status_code == 200
    assert "started_at" in captured["pipeline_runs"]
    assert captured["pipeline_runs_order"] == "started_at"
