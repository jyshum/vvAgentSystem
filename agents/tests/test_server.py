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


def test_build_checkpointer_uses_default_pool_size(monkeypatch):
    import server as server_mod

    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")
    monkeypatch.delenv("DB_POOL_MIN_SIZE", raising=False)
    monkeypatch.delenv("DB_POOL_MAX_SIZE", raising=False)

    import psycopg_pool  # noqa: F401  (ensure real module loaded before patching)
    import langgraph.checkpoint.postgres  # noqa: F401

    captured = {}

    class FakePool:
        def __init__(self, *args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs

    class FakeSaver:
        setup_calls = 0

        def __init__(self, pool):
            captured["saver_pool"] = pool

        def setup(self):
            FakeSaver.setup_calls += 1

    monkeypatch.setattr("psycopg_pool.ConnectionPool", FakePool)
    monkeypatch.setattr("langgraph.checkpoint.postgres.PostgresSaver", FakeSaver)

    result = server_mod._build_checkpointer()

    assert captured["args"] == ("postgresql://user:pass@host:5432/db",)
    assert captured["kwargs"] == {
        "kwargs": {"autocommit": True, "prepare_threshold": 0},
        "open": True,
        "min_size": 4,
        "max_size": 4,
    }
    assert isinstance(result, FakeSaver)
    assert isinstance(captured["saver_pool"], FakePool)
    assert FakeSaver.setup_calls == 1


def test_build_checkpointer_pool_size_env_override(monkeypatch):
    import server as server_mod

    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")
    monkeypatch.setenv("DB_POOL_MIN_SIZE", "2")
    monkeypatch.setenv("DB_POOL_MAX_SIZE", "8")

    import psycopg_pool  # noqa: F401  (ensure real module loaded before patching)
    import langgraph.checkpoint.postgres  # noqa: F401

    captured = {}

    class FakePool:
        def __init__(self, *args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs

    class FakeSaver:
        setup_calls = 0

        def __init__(self, pool):
            captured["saver_pool"] = pool

        def setup(self):
            FakeSaver.setup_calls += 1

    monkeypatch.setattr("psycopg_pool.ConnectionPool", FakePool)
    monkeypatch.setattr("langgraph.checkpoint.postgres.PostgresSaver", FakeSaver)

    result = server_mod._build_checkpointer()

    assert captured["kwargs"]["min_size"] == 2
    assert captured["kwargs"]["max_size"] == 8
    assert isinstance(result, FakeSaver)
    assert FakeSaver.setup_calls == 1
