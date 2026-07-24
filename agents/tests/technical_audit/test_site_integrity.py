import json

from src.technical_audit.checks.freshness import evaluate_freshness
from src.technical_audit.checks.images import evaluate_alt_text, evaluate_image_integrity
from src.technical_audit.checks.links import (
    evaluate_external_links,
    evaluate_internal_links,
)
from src.technical_audit.checks.source_support import evaluate_source_support
from src.technical_audit.models import AuditStatus

from helpers import make_context, page_observation, site_observation


def _link(url, kind="internal", in_content=True, text="link"):
    return {"url": url, "text": text, "rel": None,
            "fragment": None, "kind": kind, "in_content": in_content}


def _probe(url, *, status=200, content_type="text/html", error=None):
    return site_observation(
        "external_probe", url, request_url=url, final_url=url,
        status_code=status, content_type=content_type, error=error,
    )


def _image_probe(url, *, status=200, content_type="image/jpeg", error=None):
    return site_observation(
        "image_probe", url, request_url=url, final_url=url,
        status_code=status, content_type=content_type, error=error,
    )


# --- internal links ---

def test_internal_link_to_collected_404_fails():
    home = page_observation(links=[_link("https://example.com/gone")])
    gone = page_observation("https://example.com/gone", status_code=404)
    results = {r.subject: r for r in evaluate_internal_links(make_context(pages=(home, gone)))}
    assert results["https://example.com/"].status is AuditStatus.FAIL


def test_internal_redirect_is_review_and_healthy_passes():
    home = page_observation(links=[
        _link("https://example.com/moved"), _link("https://example.com/fine"),
    ])
    moved = page_observation(
        "https://example.com/moved",
        redirect_chain=["https://example.com/moved", "https://example.com/new"],
    )
    fine = page_observation("https://example.com/fine")
    results = {r.subject: r for r in evaluate_internal_links(make_context(pages=(home, moved, fine)))}
    assert results["https://example.com/"].status is AuditStatus.REVIEW

    healthy_only = page_observation(links=[_link("https://example.com/fine")])
    results = evaluate_internal_links(make_context(pages=(healthy_only, fine)))
    assert results[0].status is AuditStatus.PASS


def test_link_to_canonical_url_reached_via_crawl_redirect_is_clean():
    # The homepage is crawled starting at the bare domain and 301s to www, so its
    # observation carries a 2-hop redirect_chain ending at the canonical www URL.
    # A link that already points to that canonical URL must NOT be flagged as an
    # unnecessary redirect — the redirect was the crawler's entry, not the link.
    homepage = page_observation(
        "https://www.example.com/",
        redirect_chain=["https://example.com/", "https://www.example.com/"],
    )
    about = page_observation(
        "https://www.example.com/about",
        links=[_link("https://www.example.com/")],
    )
    results = {
        r.subject: r
        for r in evaluate_internal_links(make_context(pages=(homepage, about)))
    }
    assert results["https://www.example.com/about"].status is AuditStatus.PASS


def test_internal_soft_404_title_is_review():
    home = page_observation(links=[_link("https://example.com/soft")])
    soft = page_observation("https://example.com/soft", titles=["404 — Page Not Found"])
    result = evaluate_internal_links(make_context(pages=(home, soft)))[0]
    assert result.status is AuditStatus.REVIEW
    assert "soft 404" in str(result.observed)


def test_internal_links_blocked_target_unknown_and_no_links_na():
    home = page_observation(links=[_link("https://example.com/blocked")])
    blocked = page_observation("https://example.com/blocked", status_code=429)
    assert evaluate_internal_links(make_context(pages=(home, blocked)))[0].status is AuditStatus.UNKNOWN

    bare = page_observation(links=[])
    results = evaluate_internal_links(make_context(pages=(bare,)))
    assert results[0].status is AuditStatus.NOT_APPLICABLE


# --- external links ---

def test_external_links_dead_fails_blocked_unknown_none_na():
    page = page_observation(links=[_link("https://dead.example/x", kind="external")])
    dead = make_context(
        pages=(page,),
        site_observations={"external_probes": (_probe("https://dead.example/x", status=404),)},
    )
    assert evaluate_external_links(dead)[0].status is AuditStatus.FAIL

    blocked = make_context(
        pages=(page,),
        site_observations={"external_probes": (_probe("https://dead.example/x", status=403),)},
    )
    assert evaluate_external_links(blocked)[0].status is AuditStatus.UNKNOWN

    none = make_context(pages=(page_observation(),))
    assert evaluate_external_links(none)[0].status is AuditStatus.NOT_APPLICABLE

    healthy = make_context(
        pages=(page,),
        site_observations={"external_probes": (_probe("https://dead.example/x"),)},
    )
    assert evaluate_external_links(healthy)[0].status is AuditStatus.PASS


def test_external_link_timeout_is_unknown_not_fail():
    page = page_observation(links=[_link("https://slow.example/x", kind="external")])
    timed_out = site_observation(
        "external_probe", "https://slow.example/x",
        request_url="https://slow.example/x", final_url="https://slow.example/x",
        status_code=0, content_type="", error="ConnectTimeout",
    )
    context = make_context(pages=(page,), site_observations={"external_probes": (timed_out,)})
    assert evaluate_external_links(context)[0].status is AuditStatus.UNKNOWN


def test_external_link_dns_failure_is_fail():
    page = page_observation(links=[_link("https://gone.example/x", kind="external")])
    dns_dead = site_observation(
        "external_probe", "https://gone.example/x",
        request_url="https://gone.example/x", final_url="https://gone.example/x",
        status_code=0, content_type="", error="DNS resolution failed for https://gone.example/x",
    )
    context = make_context(pages=(page,), site_observations={"external_probes": (dns_dead,)})
    assert evaluate_external_links(context)[0].status is AuditStatus.FAIL


def test_source_citation_timeout_is_unknown_not_fail():
    page = page_observation(links=[
        _link("https://slow.example/study", kind="external", text="study"),
    ])
    timed_out = site_observation(
        "external_probe", "https://slow.example/study",
        request_url="https://slow.example/study", final_url="https://slow.example/study",
        status_code=0, content_type="", error="ReadTimeout",
    )
    context = make_context(pages=(page,), site_observations={"external_probes": (timed_out,)})
    assert evaluate_source_support(context)[0].status is AuditStatus.UNKNOWN


# --- images ---

def test_image_integrity_statuses():
    page = page_observation(images=[
        {"src": "https://example.com/a.jpg", "alt": "A", "loading": None,
         "width": None, "height": None, "in_link": False},
    ])
    broken = make_context(
        pages=(page,),
        site_observations={"image_probes": (_image_probe("https://example.com/a.jpg", status=404),)},
    )
    assert evaluate_image_integrity(broken)[0].status is AuditStatus.FAIL

    html_fallback = make_context(
        pages=(page,),
        site_observations={"image_probes": (_image_probe("https://example.com/a.jpg", content_type="text/html"),)},
    )
    assert evaluate_image_integrity(html_fallback)[0].status is AuditStatus.FAIL

    healthy = make_context(
        pages=(page,),
        site_observations={"image_probes": (_image_probe("https://example.com/a.jpg"),)},
    )
    assert evaluate_image_integrity(healthy)[0].status is AuditStatus.PASS

    unprobed = make_context(pages=(page,))
    assert evaluate_image_integrity(unprobed)[0].status is AuditStatus.UNKNOWN

    no_images = make_context(pages=(page_observation(),))
    assert evaluate_image_integrity(no_images)[0].status is AuditStatus.NOT_APPLICABLE


def test_alt_text_missing_fails_and_filename_alt_reviews():
    def image(src, alt, in_link=False):
        return {"src": src, "alt": alt, "loading": None, "width": None,
                "height": None, "in_link": in_link}

    missing = page_observation(images=[image("https://example.com/x.jpg", None)])
    assert evaluate_alt_text(make_context(pages=(missing,)))[0].status is AuditStatus.FAIL

    filename = page_observation(images=[image("https://example.com/x.jpg", "x.jpg")])
    assert evaluate_alt_text(make_context(pages=(filename,)))[0].status is AuditStatus.REVIEW

    stuffed = page_observation(
        images=[image("https://example.com/x.jpg", "seo, budget, doctor, money, finance")]
    )
    assert evaluate_alt_text(make_context(pages=(stuffed,)))[0].status is AuditStatus.REVIEW

    linked_empty = page_observation(images=[image("https://example.com/x.jpg", "", in_link=True)])
    assert evaluate_alt_text(make_context(pages=(linked_empty,)))[0].status is AuditStatus.REVIEW

    decorative = page_observation(images=[image("https://example.com/x.jpg", "")])
    assert evaluate_alt_text(make_context(pages=(decorative,)))[0].status is AuditStatus.PASS


# --- freshness ---

def test_freshness_classification_and_date_rules():
    timeless = page_observation()
    assert evaluate_freshness(make_context(pages=(timeless,)))[0].status is AuditStatus.NOT_APPLICABLE

    ordered = page_observation(jsonld_blocks=[json.dumps({
        "@type": "BlogPosting",
        "datePublished": "2026-01-01T00:00:00Z",
        "dateModified": "2026-02-01T00:00:00Z",
    })])
    assert evaluate_freshness(make_context(pages=(ordered,)))[0].status is AuditStatus.PASS

    misordered = page_observation(jsonld_blocks=[json.dumps({
        "@type": "BlogPosting",
        "datePublished": "2026-03-01T00:00:00Z",
        "dateModified": "2026-02-01T00:00:00Z",
    })])
    assert evaluate_freshness(make_context(pages=(misordered,)))[0].status is AuditStatus.FAIL

    future = page_observation(meta_dates={"published": "2030-01-01T00:00:00Z", "modified": None})
    assert evaluate_freshness(make_context(pages=(future,)))[0].status is AuditStatus.FAIL

    expired_event = page_observation(jsonld_blocks=[json.dumps({
        "@type": "Event", "endDate": "2025-01-01T00:00:00Z",
    })], visible_dates=["2025-01-01"])
    result = evaluate_freshness(make_context(pages=(expired_event,)))[0]
    assert result.status is AuditStatus.REVIEW
    assert result.observed["change_verification"] == "unknown_baseline"


# --- source support ---

def test_source_support_statuses():
    citing = page_observation(links=[
        _link("https://source.example/study", kind="external", text="the study"),
    ])
    dead = make_context(
        pages=(citing,),
        site_observations={"external_probes": (_probe("https://source.example/study", status=410),)},
    )
    assert evaluate_source_support(dead)[0].status is AuditStatus.FAIL

    healthy = make_context(
        pages=(citing,),
        site_observations={"external_probes": (_probe("https://source.example/study"),)},
    )
    result = evaluate_source_support(healthy)[0]
    assert result.status is AuditStatus.PASS
    assert result.scope["semantic_claim_comparison"] == "out_of_scope_v1"
    assert result.observed["healthy_sources"][0]["publisher_host"] == "source.example"

    nav_only = page_observation(links=[
        _link("https://social.example/profile", kind="external", in_content=False),
    ])
    assert evaluate_source_support(make_context(pages=(nav_only,)))[0].status is AuditStatus.NOT_APPLICABLE

    blocked = make_context(
        pages=(citing,),
        site_observations={"external_probes": (_probe("https://source.example/study", status=403),)},
    )
    assert evaluate_source_support(blocked)[0].status is AuditStatus.UNKNOWN
