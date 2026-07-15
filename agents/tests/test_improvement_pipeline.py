from unittest.mock import MagicMock, patch

import pytest

from src.technical_audit.pipeline import run_technical_pipeline


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
        "client_site_profiles": _chainable_table(
            {
                "client_id": "client-1",
                "llms_txt_enabled": False,
                "priority_urls": ["https://x.com/"],
            }
        ),
        "pipeline_runs": _chainable_table({"id": "pipeline-run-1"}),
        "technical_audit_runs": _chainable_table([{"id": "audit-run-1"}]),
        "technical_audit_observations": _chainable_table(),
        "technical_audit_results": _chainable_table(),
    }


def _state():
    return {
        "client_id": "client-1",
        "thread_id": "thread-1",
        "client_config": {"website_domain": "x.com"},
    }


def test_run_technical_pipeline_persists_only_evidence_and_community_opportunities(
    monkeypatch,
):
    monkeypatch.setenv("TECHNICAL_AUDIT_CHECK_SETS", "foundation")
    tables = _tables()
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
    mock_audit.assert_called_once_with(
        client_id="client-1",
        domain="x.com",
        inventory=[],
        profile=tables["client_site_profiles"].execute.return_value.data,
        enabled_check_sets=("foundation",),
    )
    assert "action_cards" not in result
    assert "query_page_matches" not in [call.args[0] for call in sb.table.call_args_list]
    assert "page_citation_scores" not in [call.args[0] for call in sb.table.call_args_list]
    assert "action_cards" not in [call.args[0] for call in sb.table.call_args_list]
    tables["technical_audit_observations"].insert.assert_called_once()
    tables["technical_audit_results"].insert.assert_called_once()

    improvement_insert = tables["improvement_runs"].insert.call_args.args[0]
    assert improvement_insert == {
        "client_id": "client-1",
        "status": "running",
        "thread_id": "thread-1",
        "run_mode": "technical_v1",
        "effective_check_sets": ["foundation"],
    }
    assert tables["technical_audit_runs"].insert.call_args.args[0][
        "pipeline_run_id"
    ] == "pipeline-run-1"


def test_run_technical_pipeline_returns_audit_error_without_action_cards(monkeypatch):
    monkeypatch.setenv("TECHNICAL_AUDIT_CHECK_SETS", "foundation")
    tables = _tables()
    sb = MagicMock()
    sb.table.side_effect = lambda name: tables[name]

    with patch("src.technical_audit.pipeline._get_supabase", return_value=sb), patch(
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


@pytest.mark.parametrize(
    ("check_sets", "message"),
    [
        ("unsupported", "Unavailable technical audit check set"),
        ("", "At least one technical audit check set is required"),
    ],
)
def test_run_technical_pipeline_rejects_invalid_check_sets_before_persistence(
    monkeypatch, check_sets, message
):
    monkeypatch.setenv("TECHNICAL_AUDIT_CHECK_SETS", check_sets)

    with patch("src.technical_audit.pipeline._get_supabase") as mock_supabase:
        with pytest.raises(ValueError, match=message):
            run_technical_pipeline(_state(), [], [])

    mock_supabase.assert_not_called()
