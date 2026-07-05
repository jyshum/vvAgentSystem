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
    rows = {
        "clients": [{"id": "c1", "brand_name": "Brand", "cycle_frequency": "weekly", "cycle_day": 1}],
        "pipeline_runs": [{"client_id": "c1", "status": "completed", "started_at": "2026-07-01T00:00:00Z"}],
    }

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
            return type("R", (), {"data": rows.get(self.table, [])})()

    class FakeSB:
        def table(self, name):
            return FakeQuery(name)

    class FakeJob:
        id = "cycle-c1"
        next_run_time = None

    monkeypatch.setattr(server_mod, "_get_supabase", lambda: FakeSB())
    monkeypatch.setattr(server_mod.scheduler, "get_jobs", lambda: [FakeJob()])

    client = TestClient(server_mod.app)
    resp = client.get("/api/schedules", headers={"Authorization": f"Bearer {server_mod.API_KEY}"})

    assert resp.status_code == 200
    assert "started_at" in captured["pipeline_runs"]
    assert captured["pipeline_runs_order"] == "started_at"

    body = resp.json()
    assert body["schedules"][0]["last_run_at"] == "2026-07-01T00:00:00Z"
    assert body["schedules"][0]["last_run_status"] == "completed"


def test_build_checkpointer_returns_none_without_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    import server as server_mod
    assert server_mod._build_checkpointer() is None
