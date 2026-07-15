"""Evidence-backed, deterministic technical website audits."""

from .models import (
    Applicability,
    AuditContext,
    AuditStatus,
    CheckResult,
    Confidence,
    NextAction,
    Observation,
)
from .collector import CollectedSite, HttpEvidence, collect_foundation
from .site import SiteIdentity

__all__ = [
    "Applicability",
    "AuditContext",
    "AuditStatus",
    "CheckResult",
    "Confidence",
    "NextAction",
    "Observation",
    "CollectedSite",
    "HttpEvidence",
    "SiteIdentity",
    "collect_foundation",
]
