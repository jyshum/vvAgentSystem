import pytest

from src.technical_audit.workflow import (
    WorkflowError,
    actionable,
    approve_card,
    build_cards,
    mark_applied,
    persist_cards,
    reject_card,
    verify_card,
)


class FakeQuery:
    def __init__(self, table):
        self._table = table
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

    def update(self, payload):
        self._mode = "update"
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
        rows = self._table.rows
        if self._mode == "insert":
            payloads = self._payload if isinstance(self._payload, list) else [self._payload]
            inserted = []
            for payload in payloads:
                row = dict(payload)
                row.setdefault("id", f"{self._table.name}-{len(rows) + 1}")
                rows.append(row)
                inserted.append(row)
            return type("R", (), {"data": inserted})()
        if self._mode == "update":
            updated = []
            for row in rows:
                if self._matches(row):
                    row.update(self._payload)
                    updated.append(row)
            return type("R", (), {"data": updated})()
        matched = [row for row in rows if self._matches(row)]
        data = (matched[0] if matched else None) if self._single else matched
        return type("R", (), {"data": data})()


class FakeTable:
    def __init__(self, name):
        self.name = name
        self.rows = []


class FakeSupabase:
    def __init__(self):
        self.tables = {}

    def table(self, name):
        table = self.tables.setdefault(name, FakeTable(name))
        return FakeQuery(table)


FINGERPRINT = "f" * 64


def _result(status="fail", subject="https://example.com/", owner="admin"):
    return {
        "check_id": "meta_title.integrity",
        "check_version": 1,
        "subject": subject,
        "status": status,
        "summary": "Title is missing or empty",
        "observed": {"count": 0},
        "remediation_id": "meta_title.correct",
        "next_action": {"owner": owner, "instruction": "fix"},
    }


def _group(subjects, indices):
    return {
        "group_key": "g" * 64,
        "check_id": "meta_title.integrity",
        "remediation_id": "meta_title.correct",
        "summary": "Title is missing or empty",
        "status": "fail",
        "subjects": subjects,
        "result_indices": indices,
    }


def _seeded(status="draft_prepared"):
    sb = FakeSupabase()
    sb.table("clients").insert({
        "id": "client-1", "website_domain": "example.com", "site_platform": "squarespace",
    }).execute()
    results = [_result()]
    groups = [_group(["https://example.com/"], [0])]
    sb.table("technical_audit_results").insert({
        "id": "result-1", **{k: v for k, v in results[0].items()},
    }).execute()
    cards = build_cards(
        client_id="client-1", audit_run_id="run-1", platform="squarespace",
        implementation_mode="copy_paste", results=results, groups=groups,
        result_ids=["result-1"],
        observation_fingerprints={"https://example.com/": FINGERPRINT},
    )
    card_ids = persist_cards(sb, cards)
    if status != "draft_prepared":
        card = sb.tables["technical_audit_action_cards"].rows[0]
        card["status"] = status
    return sb, card_ids[0]


def test_actionable_rules():
    assert actionable(_result("fail"))
    assert actionable(_result("review"))
    assert actionable(_result("unknown", owner="integration"))
    assert not actionable(_result("unknown", owner="system"))
    assert not actionable(_result("pass"))
    assert not actionable(_result("not_applicable"))


def test_build_cards_composes_guidance_and_precondition():
    results = [_result()]
    cards = build_cards(
        client_id="client-1", audit_run_id="run-1", platform="squarespace",
        implementation_mode="copy_paste", results=results,
        groups=[_group(["https://example.com/"], [0])],
        result_ids=["result-1"],
        observation_fingerprints={"https://example.com/": FINGERPRINT},
    )
    (card,) = cards
    assert card["status"] == "draft_prepared"
    assert card["implementation_mode"] == "guided"
    assert any("SEO" in step for step in card["instructions"])
    assert card["precondition"]["fingerprints"] == {"https://example.com/": FINGERPRINT}
    assert card["result_ids"] == ["result-1"]


def test_unknown_remediation_yields_observed_card_not_hidden():
    result = {**_result(), "remediation_id": "nonexistent.fix"}
    (card,) = build_cards(
        client_id="c", audit_run_id="r", platform="other",
        implementation_mode="copy_paste", results=[result],
        groups=[_group(["https://example.com/"], [0])],
        result_ids=["result-1"], observation_fingerprints={},
    )
    assert card["status"] == "observed"
    assert card["implementation_mode"] == "unavailable"


def test_approval_requires_named_approver_and_valid_transition():
    sb, card_id = _seeded()
    with pytest.raises(WorkflowError, match="approver"):
        approve_card(sb, card_id, "  ")
    card = approve_card(sb, card_id, "Jared")
    assert card["status"] == "approved"
    assert card["approved_by"] == "Jared"
    with pytest.raises(WorkflowError, match="cannot move card"):
        approve_card(sb, card_id, "Jared")


def test_reject_and_illegal_transitions():
    sb, card_id = _seeded()
    card = reject_card(sb, card_id)
    assert card["status"] == "rejected"
    with pytest.raises(WorkflowError):
        approve_card(sb, card_id, "Jared")


def _page_fetch(body="<html><head><title>T</title></head></html>"):
    def fetcher(url):
        return {
            "status_code": 200,
            "content_type": "text/html",
            "body": body,
            "final_url": url,
            "redirect_chain": (url,),
            "error": None,
        }
    return fetcher


def test_mark_applied_refuses_stale_precondition():
    sb, card_id = _seeded(status="approved")
    with pytest.raises(WorkflowError, match="stale"):
        mark_applied(sb, card_id, fetcher=_page_fetch())
    card = sb.tables["technical_audit_action_cards"].rows[0]
    assert card["status"] == "stale"
    assert card["verification"]["stale_subjects"] == ["https://example.com/"]


def test_mark_applied_succeeds_when_precondition_matches():
    sb, card_id = _seeded(status="approved")
    from src.technical_audit.collector import _fetch
    from src.technical_audit.site import SiteIdentity

    identity = SiteIdentity.from_domain("example.com", "squarespace")
    live = _fetch(_page_fetch(), identity, "https://example.com/")
    card = sb.tables["technical_audit_action_cards"].rows[0]
    card["precondition"]["fingerprints"]["https://example.com/"] = live.fingerprint

    updated = mark_applied(sb, card_id, fetcher=_page_fetch())
    assert updated["status"] == "applied"
    assert updated["applied_at"]


def test_verify_card_passes_only_from_fresh_deterministic_evidence():
    sb, card_id = _seeded(status="applied")
    sb.table("technical_audit_card_results").insert(
        {"card_id": card_id, "result_id": "result-1"}
    ).execute()

    verified = verify_card(sb, card_id, fetcher=_page_fetch())
    assert verified["status"] == "verified"
    assert verified["verification"]["verified"] is True

    sb2, card_id2 = _seeded(status="applied")
    sb2.table("technical_audit_card_results").insert(
        {"card_id": card_id2, "result_id": "result-1"}
    ).execute()
    still_broken = _page_fetch(body="<html><head></head></html>")
    failing = verify_card(sb2, card_id2, fetcher=still_broken)
    assert failing["status"] == "still_failing"
    assert failing["verification"]["verified"] is False


def test_verify_requires_applied_state():
    sb, card_id = _seeded()
    with pytest.raises(WorkflowError, match="cannot verify"):
        verify_card(sb, card_id, fetcher=_page_fetch())
