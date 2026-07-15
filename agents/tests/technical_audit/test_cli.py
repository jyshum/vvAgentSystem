import json

from src.technical_audit.collector import HttpEvidence


def _not_found(url: str) -> HttpEvidence:
    return HttpEvidence(
        request_url=url,
        final_url=url,
        redirect_chain=(url,),
        status_code=404,
        content_type="text/plain",
        body="",
        body_truncated=False,
        error=None,
    )


def test_smoke_writes_bounded_report_without_requesting_database(monkeypatch, tmp_path):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    output = tmp_path / "smoke.json"

    from src.technical_audit.cli import main

    result = main(
        [
            "smoke",
            "--domain",
            "example.com",
            "--platform",
            "other",
            "--output",
            str(output),
        ],
        fetcher=_not_found,
    )

    assert result == 0
    report = json.loads(output.read_text())
    assert report["summary"]["total"] >= 4
    assert report["scope"]["pages_collected"] == 1
    assert output.stat().st_size < 2_000_000


def test_smoke_returns_nonzero_for_run_error(tmp_path):
    from src.technical_audit.cli import main

    output = tmp_path / "smoke.json"
    result = main(
        [
            "smoke",
            "--domain",
            "127.0.0.1",
            "--platform",
            "other",
            "--output",
            str(output),
        ],
        fetcher=_not_found,
    )

    assert result == 1
    assert not output.exists()


def test_persisted_run_uses_loaded_client_context(monkeypatch):
    from src.technical_audit import cli

    context = (
        {
            "client_id": "client-1",
            "thread_id": None,
            "client_config": {
                "brand_name": "Example",
                "website_domain": "example.com",
                "site_platform": "other",
                "implementation_mode": "copy_paste",
                "competitors": [],
                "gsc_site_url": "",
                "target_queries": [],
            },
        },
        [{"id": "query-1"}],
        [],
    )
    monkeypatch.setattr(cli, "_load_persisted_context", lambda client_id: context)
    calls = []

    def run_pipeline(state, queries, gaps, check_sets=None):
        calls.append((state, queries, gaps, check_sets))
        return {"technical_audit_error": None, "technical_audit_summary": {"total": 4}}

    monkeypatch.setattr(cli, "run_technical_pipeline", run_pipeline)

    assert cli.main(["run", "--client-id", "client-1"]) == 0
    assert calls == [
        (*context, ("foundation", "protocol", "site_integrity", "performance"))
    ]


def test_persisted_run_returns_nonzero_when_pipeline_errors(monkeypatch):
    from src.technical_audit import cli

    context = ({"client_id": "client-1", "client_config": {}}, [], [])
    monkeypatch.setattr(cli, "_load_persisted_context", lambda client_id: context)
    monkeypatch.setattr(
        cli,
        "run_technical_pipeline",
        lambda state, queries, gaps, check_sets=None: {
            "technical_audit_error": "collection failed",
            "error": "collection failed",
        },
    )

    assert cli.main(["run", "--client-id", "client-1"]) == 1
