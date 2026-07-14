from src.technical_audit.runner import _bounded_text, run_technical_audit


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


def test_runner_bounds_persisted_llms_txt_evidence():
    report = run_technical_audit(
        client_id="client-1",
        domain="example.com",
        inventory=[{
            "url": "https://example.com/",
            "raw_html": "<html><head><title>Home</title></head></html>",
        }],
        profile={"llms_txt_enabled": True, "priority_urls": []},
        fetcher=lambda url: {
            "status_code": 200,
            "content_type": "text/plain",
            "body": "x" * 10_000,
            "final_url": url,
            "error": None,
        },
    )

    llms = next(item for item in report["observations"] if item["kind"] == "llms_txt")
    assert "body" not in llms["data"]
    assert len(llms["data"]["body_excerpt"]) == 4_000
    assert llms["data"]["body_bytes"] == 10_000


def test_homepage_is_a_priority_page_when_profile_has_no_priority_urls():
    report = run_technical_audit(
        client_id="client-1",
        domain="example.com",
        inventory=[{
            "url": "https://example.com/",
            "raw_html": '<html><head><title>Home</title><link rel="canonical" href="https://example.com/"></head></html>',
        }],
        profile={"llms_txt_enabled": False},
        fetcher=lambda url: {
            "status_code": 404,
            "content_type": "text/plain",
            "body": "",
            "final_url": url,
            "error": None,
        },
    )

    description = next(
        result for result in report["results"]
        if result["check_id"] == "meta_description.integrity"
    )
    assert description["status"] == "review"


def test_unavailable_homepage_emits_unknown_page_results():
    def fetcher(url):
        if url == "https://example.com/":
            return {
                "status_code": 403,
                "content_type": "text/html",
                "body": "Forbidden",
                "final_url": url,
                "error": None,
            }
        return {
            "status_code": 404,
            "content_type": "text/plain",
            "body": "",
            "final_url": url,
            "error": None,
        }

    report = run_technical_audit(
        client_id="client-1",
        domain="example.com",
        inventory=[],
        profile={"llms_txt_enabled": False},
        fetcher=fetcher,
    )

    page_results = [result for result in report["results"] if result["section"] != "llms_txt"]
    assert len(page_results) == 3
    assert {result["status"] for result in page_results} == {"unknown"}
    assert report["summary"]["unknown"] == 3


def test_missing_configured_priority_page_is_fetched_and_reported_unknown():
    missing_priority = "https://example.com/important"

    def fetcher(url):
        if url == missing_priority:
            return {
                "status_code": 403,
                "content_type": "text/html",
                "body": "Forbidden",
                "final_url": url,
                "error": None,
            }
        if url == "https://example.com/":
            return {
                "status_code": 200,
                "content_type": "text/html",
                "body": "<html><head><title>Home</title></head></html>",
                "final_url": url,
                "error": None,
            }
        return {
            "status_code": 404,
            "content_type": "text/plain",
            "body": "",
            "final_url": url,
            "error": None,
        }

    report = run_technical_audit(
        client_id="client-1",
        domain="example.com",
        inventory=[],
        profile={"llms_txt_enabled": False, "priority_urls": [missing_priority]},
        fetcher=fetcher,
    )

    missing_results = [
        result for result in report["results"] if result["subject"] == missing_priority
    ]
    assert len(missing_results) == 3
    assert {result["status"] for result in missing_results} == {"unknown"}
    assert any(
        observation["subject"] == missing_priority
        and observation["data"]["status_code"] == 403
        for observation in report["observations"]
    )


def test_network_body_reader_stops_at_hard_byte_limit():
    body, truncated = _bounded_text([b"abc", b"def", b"ghi"], limit=5)

    assert body == "abcde"
    assert truncated is True


def test_unsafe_llms_txt_content_is_not_copied_into_persisted_excerpt():
    report = run_technical_audit(
        client_id="client-1",
        domain="example.com",
        inventory=[{"url": "https://example.com/", "raw_html": "<html></html>"}],
        profile={"llms_txt_enabled": True},
        fetcher=lambda url: {
            "status_code": 200,
            "content_type": "text/plain",
            "body": "password=client-secret-value",
            "final_url": url,
            "error": None,
        },
    )

    llms = next(item for item in report["observations"] if item["kind"] == "llms_txt")
    assert llms["data"]["body_excerpt"] == "[REDACTED: unsafe content detected]"
    assert llms["data"]["unsafe_content_detected"] is True
    assert "client-secret-value" not in str(llms)
