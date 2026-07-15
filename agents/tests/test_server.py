from fastapi.testclient import TestClient


def test_health_endpoint():
    from server import app
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_manual_run_endpoint_still_requires_auth():
    from server import app
    client = TestClient(app)
    assert client.post("/api/run", json={"client_id": "client-1"}).status_code == 401


def test_schedule_routes_do_not_exist():
    from server import app
    client = TestClient(app)
    headers = {"Authorization": "Bearer dev-key"}
    assert client.get("/api/schedules", headers=headers).status_code == 404
    assert client.post("/api/reload-schedules", headers=headers).status_code == 404


def test_approve_marks_rejected_cards(monkeypatch):
    """Rejected cards must be marked status='rejected' in Supabase, and only approved
    ids should be sent to the graph resume."""
    import server as server_mod

    updates = []

    class FakeQuery:
        def __init__(self, table):
            self.table = table
            self._payload = None

        def update(self, payload):
            self._payload = payload
            return self

        def eq(self, col, val):
            updates.append((self.table, self._payload, col, val))
            return self

        def execute(self):
            return type("R", (), {"data": []})()

    class FakeSB:
        def table(self, name):
            return FakeQuery(name)

    resumed_with = {}

    class FakeGraph:
        def invoke(self, command, config=None):
            resumed_with["resume"] = command.resume
            return {"implementation_results": []}

    monkeypatch.setattr(server_mod, "_get_supabase", lambda: FakeSB())
    monkeypatch.setattr(server_mod, "graph", FakeGraph())

    client = TestClient(server_mod.app)
    resp = client.post(
        "/api/approve",
        json={
            "thread_id": "t",
            "approved_card_ids": ["a"],
            "rejected_card_ids": ["r1", "r2"],
        },
        headers={"Authorization": f"Bearer {server_mod.API_KEY}"},
    )

    assert resp.status_code == 200
    assert resumed_with["resume"] == ["a"]

    rejected_updates = [
        u for u in updates
        if u[0] == "action_cards" and u[1] == {"status": "rejected"}
    ]
    rejected_ids = {u[3] for u in rejected_updates if u[2] == "id"}
    assert rejected_ids == {"r1", "r2"}


def test_approve_rejected_ids_default_empty(monkeypatch):
    """rejected_card_ids should be optional for backward compatibility."""
    import server as server_mod

    class FakeQuery:
        def __init__(self, table):
            self.table = table

        def update(self, payload):
            return self

        def eq(self, col, val):
            return self

        def execute(self):
            return type("R", (), {"data": []})()

    class FakeSB:
        def table(self, name):
            return FakeQuery(name)

    resumed_with = {}

    class FakeGraph:
        def invoke(self, command, config=None):
            resumed_with["resume"] = command.resume
            return {"implementation_results": []}

    monkeypatch.setattr(server_mod, "_get_supabase", lambda: FakeSB())
    monkeypatch.setattr(server_mod, "graph", FakeGraph())

    client = TestClient(server_mod.app)
    resp = client.post(
        "/api/approve",
        json={"thread_id": "t", "approved_card_ids": ["a"]},
        headers={"Authorization": f"Bearer {server_mod.API_KEY}"},
    )

    assert resp.status_code == 200
    assert resumed_with["resume"] == ["a"]


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
