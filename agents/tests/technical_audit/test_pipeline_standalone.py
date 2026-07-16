from unittest.mock import patch


class FakeQuery:
    """Minimal chainable query stub covering only what run_standalone_audit uses.

    Not the shared `tests/technical_audit/helpers.py` fake (that module has no
    FakeSupabase); this is local to this test file per the task instructions.
    """

    def __init__(self, table_name, rows, insert_log):
        self._table_name = table_name
        self._rows = rows
        self._insert_log = insert_log
        self._filters = []
        self._single = False
        self._mode = "select"
        self._payload = None

    def select(self, *_args, **_kwargs):
        self._mode = "select"
        return self

    def insert(self, payload):
        self._mode = "insert"
        self._payload = payload
        return self

    def eq(self, column, value):
        self._filters.append((column, value))
        return self

    def maybe_single(self):
        self._single = True
        return self

    def _matches(self, row):
        return all(row.get(column) == value for column, value in self._filters)

    def execute(self):
        if self._mode == "insert":
            self._insert_log.append(self._table_name)
            payloads = self._payload if isinstance(self._payload, list) else [self._payload]
            return type("R", (), {"data": [dict(p) for p in payloads]})()
        matched = [row for row in self._rows if self._matches(row)]
        data = (matched[0] if matched else None) if self._single else matched
        return type("R", (), {"data": data})()


class FakeSupabase:
    def __init__(self, seed: dict):
        self._seed = seed
        self._insert_log = []

    def table(self, name):
        return FakeQuery(name, self._seed.get(name, []), self._insert_log)

    def inserted_tables(self):
        return list(self._insert_log)


def _client_row():
    return {
        "id": "client-1",
        "brand_name": "Budget Your MD",
        "website_domain": "example.com",
        "site_platform": "squarespace",
        "implementation_mode": "copy_paste",
        "gsc_site_url": "",
    }


def test_run_standalone_audit_passes_null_improvement_run_id():
    """A standalone audit must not create an improvement_runs row."""
    from src.technical_audit import pipeline

    sb = FakeSupabase({"clients": [_client_row()]})
    captured = {}

    def fake_audit(sb_arg, state, improvement_run_id, enabled_check_sets):
        captured["improvement_run_id"] = improvement_run_id
        captured["state"] = state
        captured["check_sets"] = enabled_check_sets
        return {"run_id": "audit-1", "summary": {"total": 1}, "results": [], "error": None}

    with patch.object(pipeline, "_get_supabase", return_value=sb), \
         patch.object(pipeline, "_run_and_persist_technical_audit", fake_audit):
        result = pipeline.run_standalone_audit("client-1")

    assert captured["improvement_run_id"] is None
    assert captured["state"]["client_id"] == "client-1"
    assert captured["state"]["client_config"]["website_domain"] == "example.com"
    assert captured["state"]["client_config"]["site_platform"] == "squarespace"
    assert result["technical_audit_run_id"] == "audit-1"
    assert sb.inserted_tables().count("improvement_runs") == 0


def test_run_standalone_audit_raises_for_unknown_client():
    from src.technical_audit import pipeline

    sb = FakeSupabase({"clients": []})
    with patch.object(pipeline, "_get_supabase", return_value=sb):
        try:
            pipeline.run_standalone_audit("missing")
        except ValueError as exc:
            assert "client not found" in str(exc)
        else:
            raise AssertionError("expected ValueError")
