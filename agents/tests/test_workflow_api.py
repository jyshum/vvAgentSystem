from unittest.mock import patch

from fastapi.testclient import TestClient


def _auth():
    import server as server_mod

    return {"Authorization": f"Bearer {server_mod.API_KEY}"}


AUTH = _auth()


def _client():
    import server as server_mod

    return TestClient(server_mod.app)


def test_workflow_endpoints_require_auth():
    client = _client()
    assert client.get("/api/technical-audit/runs?client_id=c").status_code == 401
    assert client.get("/api/technical-audit/runs/run-1").status_code == 401
    assert client.get("/api/technical-audit/cards?client_id=c").status_code == 401
    assert client.post("/api/technical-audit/cards/x/approve", json={"approved_by": "j"}).status_code == 401
    assert client.post("/api/technical-audit/cards/x/reject").status_code == 401
    assert client.post("/api/technical-audit/cards/x/mark-applied").status_code == 401
    assert client.post("/api/technical-audit/cards/x/verify").status_code == 401


def test_trigger_audit_endpoint_requires_auth():
    client = _client()
    assert client.post("/api/technical-audit/runs", json={"client_id": "c"}).status_code == 401


def test_list_runs_returns_client_runs():
    class Query:
        def select(self, *a, **k):
            return self

        def eq(self, *a, **k):
            return self

        def order(self, *a, **k):
            return self

        def execute(self):
            return type("R", (), {"data": [{"id": "run-1", "status": "completed"}]})()

    class SB:
        def table(self, name):
            return Query()

    with patch("server._get_supabase", return_value=SB()):
        resp = _client().get("/api/technical-audit/runs?client_id=c", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json() == {"runs": [{"id": "run-1", "status": "completed"}]}


def test_approve_invalid_transition_returns_409():
    from src.technical_audit.workflow import WorkflowError

    def boom(*a, **k):
        raise WorkflowError("cannot move card from approved to approved")

    with patch("server._get_supabase", return_value=object()), patch(
        "src.technical_audit.workflow.approve_card", boom
    ):
        resp = _client().post(
            "/api/technical-audit/cards/card-1/approve",
            json={"approved_by": "Jared"},
            headers=AUTH,
        )
    assert resp.status_code == 409


def test_missing_card_returns_404():
    from src.technical_audit.workflow import WorkflowError

    def boom(*a, **k):
        raise WorkflowError("card not found")

    with patch("server._get_supabase", return_value=object()), patch(
        "src.technical_audit.workflow.reject_card", boom
    ):
        resp = _client().post("/api/technical-audit/cards/x/reject", headers=AUTH)
    assert resp.status_code == 404


def test_approve_success_returns_card():
    with patch("server._get_supabase", return_value=object()), patch(
        "src.technical_audit.workflow.approve_card",
        return_value={"id": "card-1", "status": "approved", "approved_by": "Jared"},
    ):
        resp = _client().post(
            "/api/technical-audit/cards/card-1/approve",
            json={"approved_by": "Jared"},
            headers=AUTH,
        )
    assert resp.status_code == 200
    assert resp.json()["card"]["status"] == "approved"


def test_verify_endpoint_invokes_workflow():
    with patch("server._get_supabase", return_value=object()), patch(
        "src.technical_audit.workflow.verify_card",
        return_value={"id": "card-1", "status": "verified"},
    ) as verify:
        resp = _client().post("/api/technical-audit/cards/card-1/verify", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["card"]["status"] == "verified"
    verify.assert_called_once()
