from src.technical_audit.runner import run_technical_audit


def test_runner_returns_counts_and_never_a_score():
    inventory = [
        {
            "url": "https://example.com/",
            "raw_html": (
                '<html><head><title>Example</title><meta name="description" content="'
                + ("A" * 80)
                + '"><link rel="canonical" href="https://example.com/"></head><body></body></html>'
            ),
        }
    ]

    report = run_technical_audit(
        client_id="client-1",
        domain="example.com",
        inventory=inventory,
        profile={
            "llms_txt_enabled": False,
            "priority_urls": ["https://example.com/"],
        },
        fetcher=lambda url: {
            "status_code": 404,
            "content_type": "text/plain",
            "body": "",
            "final_url": url,
            "error": None,
        },
    )

    assert report["audit_version"] == 1
    assert report["summary"] == {
        "pass": 3,
        "fail": 0,
        "review": 0,
        "unknown": 0,
        "not_applicable": 1,
        "total": 4,
    }
    assert "score" not in report
    assert all("score" not in result for result in report["results"])


def test_runner_fetches_a_missing_homepage_once_and_records_fetch_errors():
    calls = []

    def fetcher(url):
        calls.append(url)
        if url == "https://example.com/":
            return {
                "status_code": 200,
                "content_type": "text/html",
                "body": "<html><head><title>Home</title></head></html>",
                "final_url": url,
                "error": None,
            }
        return {
            "status_code": 0,
            "content_type": "",
            "body": "",
            "final_url": url,
            "error": "timeout",
        }

    report = run_technical_audit(
        client_id="client-1",
        domain="example.com",
        inventory=[],
        profile={"llms_txt_enabled": True, "priority_urls": []},
        fetcher=fetcher,
    )

    assert calls == ["https://example.com/", "https://example.com/llms.txt"]
    assert report["summary"]["unknown"] == 1
    assert len(report["observations"]) == 2
