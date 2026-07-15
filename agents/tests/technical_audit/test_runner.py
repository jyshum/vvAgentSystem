import pytest

from src.technical_audit.collector import CollectedSite, HttpEvidence
from src.technical_audit.runner import run_technical_audit
from src.technical_audit.site import SiteIdentity


RETRIEVED_AT = "2026-07-15T12:00:00+00:00"


def _evidence(
    url,
    *,
    status=200,
    content_type="text/html",
    body="",
    final_url=None,
    chain=None,
    error=None,
    fingerprint="a" * 64,
):
    return HttpEvidence(
        request_url=url,
        final_url=final_url or url,
        redirect_chain=chain or (url,),
        status_code=status,
        content_type=content_type,
        body=body,
        body_truncated=False,
        error=error,
        retrieved_at=RETRIEVED_AT,
        fingerprint=fingerprint,
    )


def _collected(*, page=None, llms=None, identity=None):
    identity = identity or SiteIdentity.from_domain("example.com", "squarespace")
    page = page or _evidence(
        "https://example.com/",
        body=(
            '<html><head><title>Example</title>'
            f'<meta name="description" content="{"A" * 80}">'
            '<link rel="canonical" href="https://example.com/">'
            "</head><body></body></html>"
        ),
    )
    llms = llms or _evidence(
        f"https://{identity.configured_domain}/llms.txt",
        status=404,
        content_type="text/plain",
        fingerprint="b" * 64,
    )
    return CollectedSite(
        identity=identity,
        homepage=page,
        pages=(page,),
        llms_txt=llms,
        scope={
            "max_pages": 20,
            "pages_collected": 1,
            "truncated": False,
            "body_byte_limit": 512_000,
            "redirect_limit": 5,
        },
    )


def test_runner_returns_counts_scope_and_never_a_score():
    identity = SiteIdentity.from_domain("example.com", "squarespace")
    collected = _collected(identity=identity)

    report = run_technical_audit("client-1", identity, collected)

    assert report["audit_version"] == 1
    assert report["summary"] == {
        "pass": 3,
        "fail": 0,
        "review": 0,
        "unknown": 0,
        "not_applicable": 1,
        "total": 4,
    }
    assert report["scope"] == collected.scope
    assert "score" not in report
    assert all("score" not in result for result in report["results"])


def test_runner_retains_unavailable_page_as_unknown_results():
    identity = SiteIdentity.from_domain("example.com", "squarespace")
    blocked = _evidence(
        "https://example.com/",
        status=403,
        body="Forbidden",
        error=None,
    )

    report = run_technical_audit(
        "client-1",
        identity,
        _collected(identity=identity, page=blocked),
    )

    page_results = [
        result for result in report["results"] if result["section"] != "llms_txt"
    ]
    assert len(page_results) == 3
    assert {result["status"] for result in page_results} == {"unknown"}
    page_observation = next(
        item for item in report["observations"] if item["kind"] == "page"
    )
    assert page_observation["data"]["available"] is False
    assert page_observation["data"]["status_code"] == 403


def test_runner_accepts_www_canonical_after_bare_homepage_redirect():
    configured = SiteIdentity.from_domain("budgetyourmd.ca", "squarespace")
    resolved = configured.with_final_homepage("https://www.budgetyourmd.ca/")
    page = _evidence(
        "https://budgetyourmd.ca/",
        final_url="https://www.budgetyourmd.ca/",
        chain=(
            "https://budgetyourmd.ca/",
            "https://www.budgetyourmd.ca/",
        ),
        body=(
            '<html><head><title>Budget Your MD</title>'
            f'<meta name="description" content="{"A" * 80}">'
            '<link rel="canonical" href="https://www.budgetyourmd.ca/">'
            "</head></html>"
        ),
    )
    llms = _evidence(
        "https://www.budgetyourmd.ca/llms.txt",
        status=404,
        content_type="text/plain",
    )
    collected = _collected(identity=resolved, page=page, llms=llms)

    report = run_technical_audit("client-1", configured, collected)

    canonical = next(
        result
        for result in report["results"]
        if result["check_id"] == "canonical.integrity"
    )
    assert canonical["status"] == "pass"
    assert canonical["subject"] == "https://www.budgetyourmd.ca/"
    llms_result = next(
        result
        for result in report["results"]
        if result["check_id"] == "llms_txt.integrity"
    )
    assert llms_result["subject"] == "https://www.budgetyourmd.ca/llms.txt"


def test_runner_persists_network_provenance_and_bounds_unsafe_llms_content():
    identity = SiteIdentity.from_domain("example.com", "squarespace")
    page = _collected(identity=identity).homepage
    llms = _evidence(
        "https://example.com/llms.txt",
        content_type="text/plain",
        body="password=client-secret-value",
        fingerprint="c" * 64,
    )

    report = run_technical_audit(
        "client-1",
        identity,
        _collected(identity=identity, page=page, llms=llms),
    )

    persisted_page = next(
        item for item in report["observations"] if item["kind"] == "page"
    )
    assert persisted_page["retrieved_at"] == RETRIEVED_AT
    assert persisted_page["fingerprint"] == "a" * 64
    assert persisted_page["data"]["request_url"] == "https://example.com/"
    assert persisted_page["data"]["redirect_chain"] == ["https://example.com/"]

    persisted_llms = next(
        item for item in report["observations"] if item["kind"] == "llms_txt"
    )
    assert persisted_llms["retrieved_at"] == RETRIEVED_AT
    assert persisted_llms["fingerprint"] == "c" * 64
    assert persisted_llms["data"]["body_excerpt"] == (
        "[REDACTED: unsafe content detected]"
    )
    assert persisted_llms["data"]["unsafe_content_detected"] is True
    assert "client-secret-value" not in str(persisted_llms)


@pytest.mark.parametrize("enabled_check_sets", [("unsupported",), ()])
def test_invalid_check_sets_fail_without_mutating_collected_evidence(enabled_check_sets):
    identity = SiteIdentity.from_domain("example.com", "squarespace")
    collected = _collected(identity=identity)

    with pytest.raises(ValueError, match="Unsupported technical audit check sets"):
        run_technical_audit(
            "client-1",
            identity,
            collected,
            enabled_check_sets=enabled_check_sets,
        )

    assert collected.pages == (collected.homepage,)
