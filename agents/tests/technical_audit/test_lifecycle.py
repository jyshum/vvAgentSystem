from src.technical_audit.lifecycle import (
    classify_lifecycle,
    finding_key,
    group_findings,
    material_hash,
)


def _result(check_id="meta_title.integrity", subject="https://example.com/",
            status="fail", observed=None, summary="Title is missing",
            remediation_id="meta_title.correct"):
    return {
        "check_id": check_id,
        "check_version": 1,
        "subject": subject,
        "status": status,
        "summary": summary,
        "observed": observed or {"count": 0},
        "remediation_id": remediation_id,
    }


def test_finding_key_normalizes_subject_and_is_stable():
    a = finding_key("c", "meta_title.integrity", 1, "https://example.com/Page/")
    b = finding_key("c", "meta_title.integrity", 1, "https://example.com/page")
    assert a == b
    assert len(a) == 64


def test_material_hash_ignores_volatile_evidence():
    base = _result(observed={"count": 0, "retrieved_at": "2026-07-15T10:00:00Z"})
    later = _result(observed={"count": 0, "retrieved_at": "2026-07-16T10:00:00Z"})
    changed = _result(observed={"count": 2})
    assert material_hash(base) == material_hash(later)
    assert material_hash(base) != material_hash(changed)


def test_lifecycle_new_continuing_changed_resolved_regressed():
    previous = [
        _result(subject="https://example.com/a", status="fail"),
        _result(subject="https://example.com/b", status="fail"),
        _result(subject="https://example.com/c", status="pass", observed={"count": 1}),
        _result(subject="https://example.com/d", status="fail", observed={"count": 0}),
    ]
    current = [
        _result(subject="https://example.com/a", status="fail"),                      # continuing
        _result(subject="https://example.com/b", status="pass", observed={"count": 1}),  # resolved
        _result(subject="https://example.com/c", status="fail"),                      # regressed
        _result(subject="https://example.com/d", status="fail", observed={"count": 3}),  # changed
        _result(subject="https://example.com/e", status="fail"),                      # new
    ]
    states = {
        item["subject"]: item["lifecycle_state"]
        for item in classify_lifecycle("client-1", current, previous)
    }
    assert states == {
        "https://example.com/a": "continuing",
        "https://example.com/b": "resolved",
        "https://example.com/c": "regressed",
        "https://example.com/d": "changed",
        "https://example.com/e": "new",
    }


def test_lifecycle_annotates_finding_key():
    annotated = classify_lifecycle("client-1", [_result()], [])
    assert annotated[0]["lifecycle_state"] == "new"
    assert annotated[0]["finding_key"] == finding_key(
        "client-1", "meta_title.integrity", 1, "https://example.com/"
    )


def test_grouping_shares_identical_cause_across_subjects():
    shared = {"failures": [{"url": "https://example.com/gone", "defect": "status 404"}]}
    results = [
        _result(check_id="links.internal_health", subject="https://example.com/a",
                observed=shared, remediation_id="links.repair_internal"),
        _result(check_id="links.internal_health", subject="https://example.com/b",
                observed=shared, remediation_id="links.repair_internal"),
        _result(check_id="links.internal_health", subject="https://example.com/c",
                observed={"failures": [{"url": "https://example.com/other", "defect": "status 404"}]},
                remediation_id="links.repair_internal"),
        _result(subject="https://example.com/a", status="pass"),
    ]
    groups = group_findings(results)
    assert len(groups) == 2
    shared_group = next(g for g in groups if len(g["subjects"]) == 2)
    assert shared_group["subjects"] == ["https://example.com/a", "https://example.com/b"]
    assert shared_group["result_indices"] == [0, 1]


def test_grouping_excludes_pass_and_not_applicable():
    results = [
        _result(status="pass"),
        _result(status="not_applicable", subject="https://example.com/x"),
    ]
    assert group_findings(results) == []


def test_mixed_content_different_url_sets_produce_two_groups():
    results = [
        _result(check_id="tls.mixed_content", subject="https://example.com/about",
                observed={"active_http_urls": ["http://example.com/a.js"], "evidence": "raw_html"},
                summary="Active content is referenced over plain HTTP",
                remediation_id="tls.fix_mixed_content"),
        _result(check_id="tls.mixed_content", subject="https://example.com/services",
                observed={"active_http_urls": ["http://example.com/b.js", "http://example.com/c.js"],
                          "evidence": "raw_html"},
                summary="Active content is referenced over plain HTTP",
                remediation_id="tls.fix_mixed_content"),
    ]
    groups = group_findings(results)
    assert len(groups) == 2
    subjects = {g["subjects"][0] for g in groups}
    assert subjects == {"https://example.com/about", "https://example.com/services"}


def test_mixed_content_same_url_set_produces_one_group():
    shared = {"active_http_urls": ["http://example.com/a.js"], "evidence": "raw_html"}
    results = [
        _result(check_id="tls.mixed_content", subject="https://example.com/about",
                observed=shared,
                summary="Active content is referenced over plain HTTP",
                remediation_id="tls.fix_mixed_content"),
        _result(check_id="tls.mixed_content", subject="https://example.com/contact",
                observed=shared,
                summary="Active content is referenced over plain HTTP",
                remediation_id="tls.fix_mixed_content"),
    ]
    groups = group_findings(results)
    assert len(groups) == 1
    assert groups[0]["subjects"] == ["https://example.com/about", "https://example.com/contact"]


def test_grouping_is_deterministic_across_orderings():
    results = [
        _result(subject="https://example.com/b"),
        _result(subject="https://example.com/a"),
    ]
    first = group_findings(results)
    second = group_findings(list(reversed(results)))
    assert [g["group_key"] for g in first] == [g["group_key"] for g in second]
    assert [g["subjects"] for g in first] == [g["subjects"] for g in second]
