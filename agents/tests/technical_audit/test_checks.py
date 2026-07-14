from src.technical_audit.checks import build_v1_registry
from src.technical_audit.models import AuditContext, Observation


def _page_observation(
    *,
    title=None,
    description=None,
    canonical=None,
    is_html=True,
    robots=None,
):
    return Observation(
        id="page:https://example.com/page",
        kind="page",
        subject="https://example.com/page",
        retrieved_at="2026-07-14T10:00:00+00:00",
        fingerprint="a" * 64,
        data={
            "url": "https://example.com/page",
            "titles": title if title is not None else ["Accurate title"],
            "meta_descriptions": description if description is not None else ["A" * 80],
            "canonicals": canonical if canonical is not None else ["https://example.com/page"],
            "robots_directives": robots or [],
            "h1_texts": ["Page"],
            "is_html": is_html,
        },
    )


def _context(
    *,
    title=None,
    description=None,
    canonical=None,
    is_html=True,
    robots=None,
    priority=True,
    llms_enabled=False,
    llms_status=404,
    llms_body="",
    llms_content_type="text/plain",
    llms_error=None,
):
    page = _page_observation(
        title=title,
        description=description,
        canonical=canonical,
        is_html=is_html,
        robots=robots,
    )
    llms = Observation(
        id="site:https://example.com/llms.txt",
        kind="llms_txt",
        subject="https://example.com/llms.txt",
        retrieved_at="2026-07-14T10:00:00+00:00",
        fingerprint="b" * 64,
        data={
            "status_code": llms_status,
            "content_type": llms_content_type,
            "body": llms_body,
            "final_url": "https://example.com/llms.txt",
            "error": llms_error,
        },
    )
    return AuditContext(
        client_id="client-1",
        domain="example.com",
        profile={
            "llms_txt_enabled": llms_enabled,
            "priority_urls": ["https://example.com/page"] if priority else [],
        },
        pages=(page,),
        site_observations={"llms_txt": llms},
        run_timestamp="2026-07-14T10:00:00+00:00",
    )


def _status(context, check_id):
    return next(
        result.status.value
        for result in build_v1_registry().run(context)
        if result.check_id == check_id
    )


def test_title_statuses_are_structural_not_semantic_guesses():
    assert _status(_context(title=[]), "meta_title.integrity") == "fail"
    assert _status(_context(title=["Accurate title"]), "meta_title.integrity") == "pass"
    assert _status(_context(title=["A" * 101]), "meta_title.integrity") == "review"
    assert _status(_context(title=["One", "Two"]), "meta_title.integrity") == "fail"


def test_title_length_between_65_and_100_only_reviews_verbose_titles():
    concise = "A" * 80
    verbose = "one two three four five six seven eight nine ten eleven twelve thirteen"

    assert _status(_context(title=[concise]), "meta_title.integrity") == "pass"
    assert _status(_context(title=[verbose]), "meta_title.integrity") == "review"


def test_description_statuses_respect_priority_and_soft_length_guidance():
    assert _status(_context(description=[]), "meta_description.integrity") == "review"
    assert _status(_context(description=[], priority=False), "meta_description.integrity") == "not_applicable"
    assert _status(_context(description=["A useful description."]), "meta_description.integrity") == "review"
    assert _status(_context(description=["A" * 80]), "meta_description.integrity") == "pass"
    assert _status(_context(description=["A" * 201]), "meta_description.integrity") == "review"
    assert _status(_context(description=["A" * 80, "B" * 80]), "meta_description.integrity") == "fail"


def test_canonical_statuses_do_not_choose_between_conflicting_targets():
    assert _status(_context(canonical=[]), "canonical.integrity") == "review"
    assert _status(_context(canonical=["https://example.com/page"]), "canonical.integrity") == "pass"
    assert _status(_context(canonical=["http://example.com/page"]), "canonical.integrity") == "fail"
    assert _status(_context(canonical=["https://staging.example.com/page"]), "canonical.integrity") == "fail"
    assert _status(
        _context(canonical=["https://example.com/one", "https://example.com/two"]),
        "canonical.integrity",
    ) == "fail"


def test_cross_domain_canonical_requires_verified_allowlist():
    context = _context(canonical=["https://store.example.net/page"])
    assert _status(context, "canonical.integrity") == "fail"

    context.profile["allowed_canonical_hosts"] = ["store.example.net"]
    assert _status(context, "canonical.integrity") == "pass"


def test_non_html_and_noindex_pages_are_not_forced_to_have_metadata():
    assert _status(_context(is_html=False), "meta_title.integrity") == "not_applicable"
    assert _status(_context(robots=["noindex"]), "canonical.integrity") == "not_applicable"
    assert _status(_context(robots=["none"]), "meta_title.integrity") == "not_applicable"
    assert _status(_context(robots=["none"]), "canonical.integrity") == "not_applicable"


def test_llms_txt_is_optional_until_profile_enables_it():
    assert _status(_context(llms_enabled=False), "llms_txt.integrity") == "not_applicable"
    assert _status(
        _context(llms_enabled=False, llms_status=403, llms_error="forbidden"),
        "llms_txt.integrity",
    ) == "not_applicable"
    assert _status(_context(llms_enabled=True), "llms_txt.integrity") == "fail"


def test_llms_txt_distinguishes_integrity_review_and_access_unknown():
    assert _status(
        _context(llms_enabled=True, llms_status=200, llms_body="# Example\n\nA useful site."),
        "llms_txt.integrity",
    ) == "pass"
    assert _status(
        _context(llms_enabled=False, llms_status=200, llms_body="# Unexpected file"),
        "llms_txt.integrity",
    ) == "review"
    assert _status(
        _context(llms_enabled=True, llms_status=403, llms_error="forbidden"),
        "llms_txt.integrity",
    ) == "unknown"
    assert _status(
        _context(llms_enabled=True, llms_status=503, llms_body="Service unavailable"),
        "llms_txt.integrity",
    ) == "unknown"
    assert _status(
        _context(
            llms_enabled=True,
            llms_status=200,
            llms_body="<html>fallback</html>",
            llms_content_type="text/html",
        ),
        "llms_txt.integrity",
    ) == "fail"
