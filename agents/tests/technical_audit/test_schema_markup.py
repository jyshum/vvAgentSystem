import json

from src.technical_audit.checks.schema_markup import (
    evaluate_schema_coverage,
    evaluate_schema_integrity,
)
from src.technical_audit.evidence.structured_data import parse_jsonld
from src.technical_audit.models import AuditStatus

from helpers import make_context, page_observation


def test_parse_jsonld_flattens_arrays_and_graph():
    blocks = [
        json.dumps([{"@type": "Organization", "name": "A"}]),
        json.dumps({"@context": "https://schema.org", "@graph": [
            {"@type": "WebSite", "name": "B"},
            {"@type": "WebPage", "name": "C"},
        ]}),
    ]
    entities, errors = parse_jsonld(blocks)
    assert not errors
    assert {"Organization", "WebSite", "WebPage"} <= {
        t for e in entities for t in ([e.get("@type")] if isinstance(e.get("@type"), str) else e.get("@type") or [])
    }


def test_integrity_passes_clean_jsonld():
    page = page_observation(
        jsonld_blocks=[json.dumps({"@type": "Organization", "name": "Example Co"})]
    )
    (result,) = evaluate_schema_integrity(make_context(pages=(page,)))
    assert result.status is AuditStatus.PASS


def test_integrity_fails_malformed_placeholder_and_duplicates():
    malformed = page_observation(
        "https://example.com/bad", jsonld_blocks=['{"@type": "Organization",']
    )
    placeholder = page_observation(
        "https://example.com/ph",
        jsonld_blocks=[json.dumps({"@type": "Organization", "name": "Lorem ipsum"})],
    )
    duplicate = page_observation(
        "https://example.com/dup",
        jsonld_blocks=[
            json.dumps({"@type": "Organization", "name": "Example"}),
            json.dumps({"@type": "Organization", "name": "Example"}),
        ],
    )
    results = {
        r.subject: r
        for r in evaluate_schema_integrity(make_context(pages=(malformed, placeholder, duplicate)))
    }
    assert results["https://example.com/bad"].status is AuditStatus.FAIL
    assert results["https://example.com/ph"].status is AuditStatus.FAIL
    assert results["https://example.com/dup"].status is AuditStatus.FAIL


def test_integrity_fails_when_schema_references_collected_404():
    broken_target = page_observation(
        "https://example.com/gone", status_code=404, available=True
    )
    page = page_observation(
        jsonld_blocks=[json.dumps({"@type": "Organization", "url": "https://example.com/gone"})]
    )
    results = {
        r.subject: r
        for r in evaluate_schema_integrity(make_context(pages=(page, broken_target)))
    }
    assert results["https://example.com/"].status is AuditStatus.FAIL
    assert "https://example.com/gone" in results["https://example.com/"].observed["broken_same_site_urls"]


def test_integrity_microdata_only_is_review_and_none_is_not_applicable():
    microdata = page_observation("https://example.com/md", has_microdata=True)
    plain = page_observation("https://example.com/plain")
    results = {
        r.subject: r
        for r in evaluate_schema_integrity(make_context(pages=(microdata, plain)))
    }
    assert results["https://example.com/md"].status is AuditStatus.REVIEW
    assert results["https://example.com/plain"].status is AuditStatus.NOT_APPLICABLE


def test_integrity_unavailable_page_is_unknown():
    blocked = page_observation("https://example.com/x", available=False, status_code=403)
    (result,) = evaluate_schema_integrity(make_context(pages=(blocked,)))
    assert result.status is AuditStatus.UNKNOWN


def test_coverage_homepage_review_and_pass():
    bare = page_observation()
    (result,) = evaluate_schema_coverage(make_context(pages=(bare,)))
    assert result.status is AuditStatus.REVIEW

    covered = page_observation(
        jsonld_blocks=[json.dumps({"@type": "WebSite", "name": "Example"})]
    )
    (result,) = evaluate_schema_coverage(make_context(pages=(covered,)))
    assert result.status is AuditStatus.PASS
