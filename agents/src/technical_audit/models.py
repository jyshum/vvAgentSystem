from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class AuditStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    REVIEW = "review"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class Applicability:
    applies: bool
    reason: str


@dataclass(frozen=True)
class NextAction:
    owner: str
    instruction: str


@dataclass(frozen=True)
class Observation:
    id: str
    kind: str
    subject: str
    retrieved_at: str
    fingerprint: str
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class AuditContext:
    client_id: str
    domain: str
    profile: dict[str, Any]
    pages: tuple[Observation, ...]
    site_observations: dict[str, Observation]
    run_timestamp: str


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    check_version: int
    section: str
    subject: str
    status: AuditStatus
    severity: str
    summary: str
    expected: str
    observed: dict[str, Any]
    evidence_refs: tuple[str, ...]
    scope: dict[str, Any]
    applicability: Applicability
    confidence: Confidence
    next_action: NextAction
    remediation_id: str | None

    def __post_init__(self) -> None:
        if not self.check_id:
            raise ValueError("check_id must not be empty")
        if self.check_version <= 0:
            raise ValueError("check_version must be positive")
        if self.status is AuditStatus.NOT_APPLICABLE and self.applicability.applies:
            raise ValueError("not_applicable results cannot apply")

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))

    @classmethod
    def not_applicable(
        cls,
        *,
        check_id: str,
        check_version: int,
        section: str,
        subject: str,
        reason: str,
    ) -> CheckResult:
        return cls(
            check_id=check_id,
            check_version=check_version,
            section=section,
            subject=subject,
            status=AuditStatus.NOT_APPLICABLE,
            severity="low",
            summary="Check does not apply",
            expected="No requirement for this subject",
            observed={},
            evidence_refs=(),
            scope={"sampled": False, "urls_checked": 0},
            applicability=Applicability(False, reason),
            confidence=Confidence.HIGH,
            next_action=NextAction("system", "No action required"),
            remediation_id=None,
        )


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value
