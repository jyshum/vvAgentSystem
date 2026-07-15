from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

# Evidence keys that vary between runs without changing what the finding is.
_VOLATILE_KEYS = {
    "retrieved_at",
    "fetch_times",
    "collection_period",
    "days_to_expiry",
    "fingerprint",
    "last_submitted",
    "last_downloaded",
}


def _strip_volatile(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_volatile(item)
            for key, item in sorted(value.items())
            if key not in _VOLATILE_KEYS
        }
    if isinstance(value, list):
        return [_strip_volatile(item) for item in value]
    return value


def _normalize_subject(subject: str) -> str:
    return subject.strip().rstrip("/").lower()


def finding_key(client_id: str, check_id: str, check_version: int, subject: str) -> str:
    payload = f"{client_id}|{check_id}|{check_version}|{_normalize_subject(subject)}"
    return sha256(payload.encode("utf-8")).hexdigest()


def material_hash(result: dict[str, Any]) -> str:
    payload = {
        "status": result.get("status"),
        "observed": _strip_volatile(result.get("observed") or {}),
    }
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def classify_lifecycle(
    client_id: str,
    current: list[dict[str, Any]],
    previous: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Annotate each current result with finding_key and lifecycle_state by
    comparing against the previous completed run's results. Pure and
    deterministic."""
    previous_by_key = {
        finding_key(client_id, item["check_id"], item["check_version"], item["subject"]): (
            item.get("status"),
            material_hash(item),
        )
        for item in previous
    }
    annotated = []
    for result in current:
        key = finding_key(
            client_id, result["check_id"], result["check_version"], result["subject"]
        )
        current_material = material_hash(result)
        prior = previous_by_key.get(key)
        if prior is None:
            state = "new"
        else:
            prior_status, prior_material = prior
            status = result.get("status")
            if prior_status != "pass" and status == "pass":
                state = "resolved"
            elif prior_status == "pass" and status == "fail":
                state = "regressed"
            elif prior_status == status and prior_material == current_material:
                state = "continuing"
            else:
                state = "changed"
        annotated.append({**result, "finding_key": key, "lifecycle_state": state})
    return annotated


_ACTIONABLE = {"fail", "review", "unknown"}


def _cause_signature(result: dict[str, Any]) -> Any:
    observed = result.get("observed") or {}
    for key in ("failures", "defects", "missing", "reviews", "blocked"):
        items = observed.get(key)
        if isinstance(items, list) and items:
            values = []
            for item in items:
                if isinstance(item, dict):
                    values.append(
                        item.get("url")
                        or item.get("src")
                        or item.get("loc")
                        or item.get("defect")
                        or json.dumps(item, sort_keys=True, default=str)
                    )
                else:
                    values.append(str(item))
            return tuple(sorted(set(values)))
    return result.get("summary", "")


def group_findings(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group actionable results that share one identical cause: same check,
    same remediation, same material defect signature. No similarity logic."""
    groups: dict[str, dict[str, Any]] = {}
    for index, result in enumerate(results):
        if result.get("status") not in _ACTIONABLE:
            continue
        cause = _cause_signature(result)
        raw_key = json.dumps(
            [result.get("check_id"), result.get("remediation_id"), cause],
            sort_keys=True,
            default=str,
        )
        group_key = sha256(raw_key.encode("utf-8")).hexdigest()
        group = groups.setdefault(
            group_key,
            {
                "group_key": group_key,
                "check_id": result.get("check_id"),
                "remediation_id": result.get("remediation_id"),
                "summary": result.get("summary", ""),
                "status": result.get("status"),
                "subjects": [],
                "result_indices": [],
            },
        )
        group["subjects"].append(result.get("subject"))
        group["result_indices"].append(index)
    ordered = sorted(groups.values(), key=lambda item: item["group_key"])
    for group in ordered:
        group["subjects"] = sorted(set(group["subjects"]))
    return ordered
