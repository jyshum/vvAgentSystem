from unittest.mock import MagicMock, patch

import pytest

from src.technical_audit.collector import CollectedSite, HttpEvidence
from src.technical_audit.pipeline import run_technical_pipeline
from src.technical_audit.site import SiteIdentity


def _chainable_table(data=None):
    table = MagicMock()
    for method in (
        "select",
        "eq",
        "order",
        "limit",
        "maybe_single",
        "single",
        "insert",
        "update",
    ):
        getattr(table, method).return_value = table
    table.execute.return_value = MagicMock(data=[] if data is None else data)
    return table


def _audit_report():
    return {
        "audit_version": 1,
        "scope": {"pages_collected": 1, "truncated": False},
        "observations": [
            {
                "id": "page:https://x.com/",
                "kind": "page",
                "subject": "https://x.com/",
                "retrieved_at": "2026-07-14T10:00:00+00:00",
                "fingerprint": "a" * 64,
                "data": {"titles": []},
            }
        ],
        "results": [
            {
                "check_id": "meta_title.integrity",
                "check_version": 1,
                "section": "meta_title",
                "subject": "https://x.com/",
                "status": "fail",
                "severity": "high",
                "summary": "Title is missing",
                "expected": "One title",
                "observed": {"count": 0},
                "evidence_refs": ["page:https://x.com/"],
                "scope": {"sampled": False, "urls_checked": 1},
                "applicability": {"applies": True, "reason": "HTML page"},
                "confidence": "high",
                "next_action": {"owner": "admin", "instruction": "Add a title"},
                "remediation_id": "meta_title.correct",
            }
        ],
        "summary": {
            "pass": 0,
            "fail": 1,
            "review": 0,
            "unknown": 0,
            "not_applicable": 0,
            "total": 1,
        },
    }


def _tables():
    return {
        "improvement_runs": _chainable_table([{"id": "improvement-run-1"}]),
        "pipeline_runs": _chainable_table({"id": "pipeline-run-1"}),
        "technical_audit_runs": _chainable_table([{"id": "audit-run-1"}]),
        "technical_audit_observations": _chainable_table(),
        "technical_audit_results": _chainable_table(),
    }


def _state():
    return {
        "client_id": "client-1",
        "thread_id": "thread-1",
        "client_config": {
            "website_domain": "x.com",
            "site_platform": "squarespace",
            "implementation_mode": "copy_paste",
        },
    }


def _collected():
    identity = SiteIdentity.from_domain("x.com", "squarespace")
    page = HttpEvidence(
        request_url="https://x.com/",
        final_url="https://x.com/",
        redirect_chain=("https://x.com/",),
        status_code=200,
        content_type="text/html",
        body="<html></html>",
        body_truncated=False,
        error=None,
        retrieved_at="2026-07-15T12:00:00+00:00",
        fingerprint="a" * 64,
    )
    llms = HttpEvidence(
        request_url="https://x.com/llms.txt",
        final_url="https://x.com/llms.txt",
        redirect_chain=("https://x.com/llms.txt",),
        status_code=404,
        content_type="text/plain",
        body="",
        body_truncated=False,
        error=None,
        retrieved_at="2026-07-15T12:00:00+00:00",
        fingerprint="b" * 64,
    )
    return CollectedSite(
        identity=identity,
        homepage=page,
        pages=(page,),
        llms_txt=llms,
        scope={"pages_collected": 1, "truncated": False},
    )


def test_run_technical_pipeline_persists_only_evidence_and_community_opportunities(
    monkeypatch,
):
    monkeypatch.setenv("TECHNICAL_AUDIT_CHECK_SETS", "unsupported")
    tables = _tables()
    collected = _collected()
    sb = MagicMock()
    sb.table.side_effect = lambda name: tables[name]
    tracker_gaps = [
        {
            "query": f"query-{number}",
            "query_id": f"query-{number}",
            "bucket": "awareness",
            "client_mention_rate": 0.1,
            "competitor_data": [{"name": "Competitor", "mention_rate": gap}],
        }
        for number, gap in [
            (4, 0.6),
            (1, 0.9),
            (7, 0.3),
            (2, 0.8),
            (6, 0.4),
            (3, 0.7),
            (5, 0.5),
        ]
    ]

    with patch("src.technical_audit.pipeline._get_supabase", return_value=sb), patch(
        "src.technical_audit.pipeline.collect_foundation",
        return_value=collected,
    ) as mock_collect, patch(
        "src.technical_audit.pipeline.run_technical_audit",
        return_value=_audit_report(),
    ) as mock_audit:
        result = run_technical_pipeline(_state(), [], tracker_gaps)

    assert result == {
        "improvement_run_id": "improvement-run-1",
        "technical_audit_run_id": "audit-run-1",
        "technical_audit_summary": _audit_report()["summary"],
        "technical_audit_results": _audit_report()["results"],
        "technical_audit_error": None,
        "community_opportunities": [
            {
                "query": f"query-{number}",
                "query_id": f"query-{number}",
                "bucket": "awareness",
                "top_competitor": "Competitor",
                "client_mention_rate": 0.1,
                "competitor_mention_rate": gap,
                "competitive_gap": round(gap - 0.1, 4),
            }
            for number, gap in [(1, 0.9), (2, 0.8), (3, 0.7), (4, 0.6), (5, 0.5)]
        ],
    }
    identity = SiteIdentity.from_domain("x.com", "squarespace")
    mock_collect.assert_called_once_with(identity)
    mock_audit.assert_called_once_with(
        "client-1", identity, collected, enabled_check_sets=("foundation",)
    )
    assert "action_cards" not in result
    assert "query_page_matches" not in [call.args[0] for call in sb.table.call_args_list]
    assert "page_citation_scores" not in [call.args[0] for call in sb.table.call_args_list]
    assert "action_cards" not in [call.args[0] for call in sb.table.call_args_list]
    assert "client_site_profiles" not in [
        call.args[0] for call in sb.table.call_args_list
    ]
    tables["technical_audit_observations"].insert.assert_called_once()
    tables["technical_audit_results"].insert.assert_called_once()

    improvement_insert = tables["improvement_runs"].insert.call_args.args[0]
    assert improvement_insert == {
        "client_id": "client-1",
        "status": "running",
        "thread_id": "thread-1",
    }
    completion = tables["improvement_runs"].update.call_args.args[0]
    assert "cards_generated" not in completion
    assert tables["technical_audit_runs"].insert.call_args.args[0][
        "pipeline_run_id"
    ] == "pipeline-run-1"


def test_run_technical_pipeline_returns_audit_error_without_action_cards(monkeypatch):
    tables = _tables()
    sb = MagicMock()
    sb.table.side_effect = lambda name: tables[name]

    with patch("src.technical_audit.pipeline._get_supabase", return_value=sb), patch(
        "src.technical_audit.pipeline.collect_foundation",
        return_value=_collected(),
    ), patch(
        "src.technical_audit.pipeline.run_technical_audit",
        side_effect=RuntimeError("audit unavailable"),
    ):
        result = run_technical_pipeline(_state(), [], [])

    assert result == {
        "improvement_run_id": "improvement-run-1",
        "technical_audit_run_id": "audit-run-1",
        "technical_audit_summary": {},
        "technical_audit_results": [],
        "technical_audit_error": "audit unavailable",
        "community_opportunities": [],
        "error": "audit unavailable",
    }
    assert "action_cards" not in result
    audit_update = tables["technical_audit_runs"].update.call_args.args[0]
    assert audit_update["status"] == "error"
    assert audit_update["error_message"] == "audit unavailable"


def test_run_technical_pipeline_has_no_rollout_or_profile_controls(monkeypatch):
    monkeypatch.setenv("TECHNICAL_AUDIT_V1_ENABLED", "false")
    monkeypatch.setenv("TECHNICAL_AUDIT_INTERNAL_CLIENT_IDS", "someone-else")
    monkeypatch.setenv("TECHNICAL_AUDIT_CHECK_SETS", "unsupported")
    tables = _tables()
    sb = MagicMock()
    sb.table.side_effect = lambda name: tables[name]

    with patch("src.technical_audit.pipeline._get_supabase", return_value=sb), patch(
        "src.technical_audit.pipeline.collect_foundation", return_value=_collected()
    ), patch(
        "src.technical_audit.pipeline.run_technical_audit",
        return_value=_audit_report(),
    ):
        result = run_technical_pipeline(_state(), [], [])

    assert result["technical_audit_error"] is None
    assert "client_site_profiles" not in [
        call.args[0] for call in sb.table.call_args_list
    ]
