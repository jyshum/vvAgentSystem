from __future__ import annotations

from dataclasses import dataclass
import os


AVAILABLE_CHECK_SETS = frozenset({"foundation"})


def _csv(value: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(part.strip() for part in value.split(",") if part.strip())
    )


@dataclass(frozen=True)
class AuditRolloutPolicy:
    enabled: bool
    client_ids: frozenset[str]
    check_sets: tuple[str, ...]

    @classmethod
    def from_environment(cls) -> "AuditRolloutPolicy":
        enabled = (
            os.environ.get("TECHNICAL_AUDIT_V1_ENABLED", "false").lower() == "true"
        )
        client_ids = frozenset(
            _csv(os.environ.get("TECHNICAL_AUDIT_INTERNAL_CLIENT_IDS", ""))
        )
        check_sets = _csv(
            os.environ.get("TECHNICAL_AUDIT_CHECK_SETS", "foundation")
        )
        unavailable = set(check_sets) - AVAILABLE_CHECK_SETS
        if unavailable:
            names = ", ".join(sorted(unavailable))
            raise ValueError(f"Unavailable technical audit check set(s): {names}")
        if not check_sets:
            raise ValueError("At least one technical audit check set is required")
        return cls(enabled=enabled, client_ids=client_ids, check_sets=check_sets)

    def active_for(self, client_id: str) -> bool:
        return self.enabled and (
            "*" in self.client_ids or client_id in self.client_ids
        )
