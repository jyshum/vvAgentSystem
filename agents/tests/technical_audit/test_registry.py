from dataclasses import replace

import pytest

from src.technical_audit.models import (
    Applicability,
    AuditStatus,
    CheckResult,
    Confidence,
    NextAction,
)
from src.technical_audit.registry import CheckDefinition, CheckRegistry


def test_registry_rejects_duplicate_check_versions():
    registry = CheckRegistry()
    definition = CheckDefinition(
        "meta_title.present", 1, "meta_title", "page", lambda context: []
    )
    registry.register(definition)

    with pytest.raises(ValueError, match="duplicate check version"):
        registry.register(definition)


def test_registry_runs_in_stable_id_version_order():
    calls = []
    registry = CheckRegistry()
    registry.register(
        CheckDefinition("z.check", 1, "z", "site", lambda context: calls.append("z") or [])
    )
    registry.register(
        CheckDefinition("a.check", 2, "a", "site", lambda context: calls.append("a2") or [])
    )
    registry.register(
        CheckDefinition("a.check", 1, "a", "site", lambda context: calls.append("a1") or [])
    )

    assert registry.run(object()) == []
    assert calls == ["a1", "a2", "z"]


def test_registry_rejects_result_provenance_that_differs_from_definition():
    valid = CheckResult(
        check_id="a.check",
        check_version=1,
        section="a",
        subject="https://example.com/",
        status=AuditStatus.PASS,
        severity="low",
        summary="Good",
        expected="Good",
        observed={},
        evidence_refs=(),
        scope={},
        applicability=Applicability(True, "Applicable"),
        confidence=Confidence.HIGH,
        next_action=NextAction("system", "No action required"),
        remediation_id=None,
    )
    registry = CheckRegistry()
    registry.register(
        CheckDefinition(
            "a.check",
            1,
            "a",
            "site",
            lambda context: [replace(valid, check_version=2)],
        )
    )

    with pytest.raises(ValueError, match="provenance"):
        registry.run(object())
