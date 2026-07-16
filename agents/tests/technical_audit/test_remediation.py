from src.technical_audit.checks import registered_check_sets
from src.technical_audit.remediation import CATALOGUE, build_guidance


def test_every_remediation_id_used_by_checks_has_a_catalogue_entry():
    # Collect every remediation_id emitted anywhere in the check modules by
    # scanning source for the string literals, then assert coverage.
    import pkgutil
    import re
    from pathlib import Path

    checks_dir = Path(__file__).parents[2] / "src/technical_audit/checks"
    used = set()
    for path in checks_dir.glob("*.py"):
        for match in re.finditer(r'remediation_id\s*=\s*"([a-z_.]+)"', path.read_text()):
            used.add(match.group(1))
    missing = used - set(CATALOGUE)
    assert not missing, f"remediation ids without catalogue entries: {missing}"


def test_squarespace_guidance_targets_native_settings():
    result = {
        "subject": "https://budgetyourmd.ca/about",
        "remediation_id": "meta_title.correct",
        "observed": {},
    }
    guidance = build_guidance(result, "squarespace")
    assert guidance["mode"] == "guided"
    assert guidance["remediation_id"] == "meta_title.correct"
    assert any("SEO Title" in step for step in guidance["instructions"])
    assert all("edit the html" not in step.lower() for step in guidance["instructions"])


def test_sitemap_guidance_never_edits_generated_xml():
    guidance = build_guidance(
        {"remediation_id": "sitemap.correct_source", "observed": {}}, "squarespace"
    )
    assert any("never edit the xml" in step.lower() for step in guidance["instructions"])


def test_mixed_content_guidance_carries_insecure_urls():
    guidance = build_guidance(
        {
            "remediation_id": "tls.fix_mixed_content",
            "observed": {"active_http_urls": ["http://cdn.example/app.js"]},
        },
        "squarespace",
    )
    assert guidance["copy_values"]["insecure_urls"] == ["http://cdn.example/app.js"]


def test_unknown_remediation_returns_none():
    assert build_guidance({"remediation_id": "does.not.exist"}, "other") is None
    assert build_guidance({}, "other") is None


def test_mixed_content_guidance_reports_true_total_beyond_cap():
    urls = [f"http://cdn.example/{i}.js" for i in range(60)]
    guidance = build_guidance(
        {
            "remediation_id": "tls.fix_mixed_content",
            "observed": {"active_http_urls": urls},
        },
        "squarespace",
    )
    assert len(guidance["copy_values"]["insecure_urls"]) == 10
    assert guidance["copy_values"]["insecure_urls"] == urls[:10]
    assert guidance["copy_values"]["insecure_urls_total"] == 60


def test_links_guidance_reports_true_total_beyond_cap():
    failures = [f"https://example.com/dead-{i}" for i in range(60)]
    guidance = build_guidance(
        {
            "remediation_id": "links.repair_internal",
            "observed": {"failures": failures},
        },
        "squarespace",
    )
    assert len(guidance["copy_values"]["broken"]) == 10
    assert guidance["copy_values"]["broken"] == failures[:10]
    assert guidance["copy_values"]["broken_total"] == 60


def test_sources_guidance_reports_true_total_beyond_cap():
    failures = [f"https://source.example/{i}" for i in range(60)]
    guidance = build_guidance(
        {
            "remediation_id": "sources.repair_citations",
            "observed": {"failures": failures},
        },
        "squarespace",
    )
    assert len(guidance["copy_values"]["dead_sources"]) == 10
    assert guidance["copy_values"]["dead_sources"] == failures[:10]
    assert guidance["copy_values"]["dead_sources_total"] == 60
