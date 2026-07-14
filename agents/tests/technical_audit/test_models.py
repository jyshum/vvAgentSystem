from dataclasses import FrozenInstanceError

import pytest

from src.technical_audit.models import (
    Applicability,
    AuditStatus,
    CheckResult,
    Confidence,
    NextAction,
)


def test_check_result_serializes_the_complete_resolution_contract():
    result = CheckResult(
        check_id="meta_title.present",
        check_version=1,
        section="meta_title",
        subject="https://example.com/",
        status=AuditStatus.FAIL,
        severity="high",
        summary="Title is missing",
        expected="One nonempty title",
        observed={"count": 0},
        evidence_refs=("page:https://example.com/",),
        scope={"sampled": False, "urls_checked": 1},
        applicability=Applicability(True, "HTML page is indexable"),
        confidence=Confidence.HIGH,
        next_action=NextAction("admin", "Add a truthful SEO title"),
        remediation_id="meta_title.add",
    )

    payload = result.to_dict()

    assert payload["status"] == "fail"
    assert payload["confidence"] == "high"
    assert payload["applicability"] == {
        "applies": True,
        "reason": "HTML page is indexable",
    }
    assert payload["next_action"]["owner"] == "admin"
    assert payload["evidence_refs"] == ["page:https://example.com/"]


def test_check_result_is_immutable():
    result = CheckResult.not_applicable(
        check_id="llms_txt.present",
        check_version=1,
        section="llms_txt",
        subject="https://example.com/llms.txt",
        reason="Client has not opted in",
    )

    with pytest.raises(FrozenInstanceError):
        result.status = AuditStatus.FAIL


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"check_id": ""}, "check_id"),
        ({"check_version": 0}, "check_version"),
        (
            {
                "status": AuditStatus.NOT_APPLICABLE,
                "applicability": Applicability(True, "applies"),
            },
            "not_applicable",
        ),
    ],
)
def test_check_result_rejects_invalid_contracts(overrides, message):
    values = {
        "check_id": "meta_title.integrity",
        "check_version": 1,
        "section": "meta_title",
        "subject": "https://example.com/",
        "status": AuditStatus.PASS,
        "severity": "low",
        "summary": "Title is valid",
        "expected": "One nonempty title",
        "observed": {"count": 1},
        "evidence_refs": ("page:https://example.com/",),
        "scope": {"sampled": False, "urls_checked": 1},
        "applicability": Applicability(True, "HTML page is indexable"),
        "confidence": Confidence.HIGH,
        "next_action": NextAction("system", "No action required"),
        "remediation_id": None,
    }
    values.update(overrides)

    with pytest.raises(ValueError, match=message):
        CheckResult(**values)
