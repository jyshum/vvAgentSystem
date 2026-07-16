from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .collector import Fetcher, _fetch
from .remediation import build_guidance
from .site import SiteIdentity

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "observed": {"draft_prepared", "rejected"},
    "draft_prepared": {"approved", "rejected"},
    "approved": {"applied", "rejected", "stale"},
    "applied": {"verified", "still_failing"},
    "stale": {"draft_prepared", "rejected"},
    "rejected": set(),
    "verified": set(),
    "still_failing": {"draft_prepared", "rejected"},
}

_CARD_STATUSES = {"fail", "review"}
_CARD_UNKNOWN_OWNERS = {"admin", "client", "integration"}


class WorkflowError(ValueError):
    """Invalid transition or stale precondition; carries the reason."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def actionable(result: dict[str, Any]) -> bool:
    status = result.get("status")
    if status in _CARD_STATUSES:
        return True
    if status == "unknown":
        owner = ((result.get("next_action") or {}).get("owner") or "").lower()
        return owner in _CARD_UNKNOWN_OWNERS
    return False


def build_cards(
    *,
    client_id: str,
    audit_run_id: str,
    platform: str,
    implementation_mode: str,
    results: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    result_ids: list[str],
    observation_fingerprints: dict[str, str],
) -> list[dict[str, Any]]:
    """Compose one card per actionable finding group. Immutable results stay
    untouched; the card is the editable workflow object."""
    cards = []
    for group in groups:
        member_indices = [
            index for index in group["result_indices"] if actionable(results[index])
        ]
        if not member_indices:
            continue
        representative = results[member_indices[0]]
        guidance = build_guidance(representative, platform)
        precondition = {
            subject: observation_fingerprints[subject]
            for subject in group["subjects"]
            if subject in observation_fingerprints
        }
        card = {
            "client_id": client_id,
            "audit_run_id": audit_run_id,
            "group_key": group["group_key"],
            "source": "technical",
            "status": "draft_prepared" if guidance else "observed",
            "title": group["summary"] or representative.get("summary", ""),
            "platform": platform,
            "implementation_mode": (
                guidance["mode"] if guidance else "unavailable"
            ),
            "instructions": guidance["instructions"] if guidance else [],
            "copy_values": guidance.get("copy_values", {}) if guidance else {},
            "precondition": {
                "fingerprints": precondition,
                "audited_at": _now(),
            },
            "result_ids": [result_ids[index] for index in member_indices],
        }
        cards.append(card)
    return cards


def persist_cards(sb, cards: list[dict[str, Any]]) -> list[str]:
    card_ids = []
    for card in cards:
        row = {key: value for key, value in card.items() if key != "result_ids"}
        response = sb.table("technical_audit_action_cards").insert(row).execute()
        card_id = response.data[0]["id"]
        card_ids.append(card_id)
        links = [
            {"card_id": card_id, "result_id": result_id}
            for result_id in card["result_ids"]
        ]
        if links:
            sb.table("technical_audit_card_results").insert(links).execute()
    return card_ids


def _load_card(sb, card_id: str) -> dict[str, Any]:
    response = (
        sb.table("technical_audit_action_cards")
        .select("*")
        .eq("id", card_id)
        .maybe_single()
        .execute()
    )
    if not response.data:
        raise WorkflowError("card not found")
    return response.data


def _transition(sb, card: dict[str, Any], new_status: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    current = card["status"]
    if new_status not in ALLOWED_TRANSITIONS.get(current, set()):
        raise WorkflowError(f"cannot move card from {current} to {new_status}")
    payload = {"status": new_status, "updated_at": _now(), **(extra or {})}
    sb.table("technical_audit_action_cards").update(payload).eq("id", card["id"]).execute()
    return {**card, **payload}


def approve_card(sb, card_id: str, approver: str) -> dict[str, Any]:
    if not approver or not approver.strip():
        raise WorkflowError("approval requires a named approver")
    card = _load_card(sb, card_id)
    return _transition(
        sb, card, "approved",
        {"approved_by": approver.strip(), "approved_at": _now()},
    )


def reject_card(sb, card_id: str) -> dict[str, Any]:
    card = _load_card(sb, card_id)
    return _transition(sb, card, "rejected")


def _client_identity(sb, client_id: str) -> SiteIdentity:
    response = (
        sb.table("clients")
        .select("website_domain,site_platform")
        .eq("id", client_id)
        .maybe_single()
        .execute()
    )
    if not response.data:
        raise WorkflowError("client not found")
    return SiteIdentity.from_domain(
        response.data["website_domain"],
        response.data.get("site_platform") or "other",
    )


def _live_fetcher(identity: SiteIdentity) -> Fetcher:
    from .collector import _HttpxFetcher

    return _HttpxFetcher(identity)


def mark_applied(sb, card_id: str, *, fetcher: Fetcher | None = None) -> dict[str, Any]:
    """Record the operator's applied claim, refusing when the audited
    precondition no longer matches production (the draft is stale)."""
    card = _load_card(sb, card_id)
    if card["status"] != "approved":
        raise WorkflowError(f"cannot move card from {card['status']} to applied")
    identity = _client_identity(sb, card["client_id"])
    effective_fetcher = fetcher or _live_fetcher(identity)
    fingerprints = (card.get("precondition") or {}).get("fingerprints") or {}
    changed = []
    try:
        for subject, audited_fingerprint in fingerprints.items():
            evidence = _fetch(effective_fetcher, identity, subject)
            if evidence.fingerprint != audited_fingerprint:
                changed.append(subject)
    finally:
        close = getattr(effective_fetcher, "close", None)
        if fetcher is None and callable(close):
            close()
    if changed:
        stale = _transition(
            sb, card, "stale",
            {"verification": {"stale_subjects": changed, "checked_at": _now()}},
        )
        raise WorkflowError(
            "precondition changed since the audit; card marked stale: "
            + ", ".join(changed)
        ) from None
    return _transition(sb, card, "applied", {"applied_at": _now()})


def _linked_results(sb, card_id: str) -> list[dict[str, Any]]:
    links = (
        sb.table("technical_audit_card_results")
        .select("result_id")
        .eq("card_id", card_id)
        .execute()
    )
    result_ids = [row["result_id"] for row in (links.data or [])]
    results = []
    for result_id in result_ids:
        response = (
            sb.table("technical_audit_results")
            .select("check_id,check_version,subject")
            .eq("id", result_id)
            .maybe_single()
            .execute()
        )
        if response.data:
            results.append(response.data)
    return results


def verify_card(
    sb,
    card_id: str,
    *,
    fetcher: Fetcher | None = None,
) -> dict[str, Any]:
    """Deterministic re-audit: re-collect the site the same way the audit did,
    re-run the exact originating checks, and mark verified only when every
    linked (check_id, subject) pair passes on fresh evidence.

    Re-collecting the whole site (not just the linked pages) is what lets
    site-level findings — robots, sitemap, TLS, schema — actually verify; a
    page-only re-fetch leaves their evidence empty and they can never pass.
    """
    from .checks import build_v1_registry, registered_check_sets
    from .collector import collect_site
    from .runner import run_technical_audit

    card = _load_card(sb, card_id)
    if card["status"] != "applied":
        raise WorkflowError(f"cannot verify card in status {card['status']}")
    linked = _linked_results(sb, card_id)
    if not linked:
        raise WorkflowError("card has no linked results to verify")
    identity = _client_identity(sb, card["client_id"])

    linked_pairs = {(item["check_id"], item["subject"].rstrip("/").lower()) for item in linked}
    check_ids = {item["check_id"] for item in linked}
    # Verification never depends on live performance integrations; those checks
    # are excluded so an unconfigured key cannot leave a card unverifiable.
    verify_sets = tuple(
        name for name in registered_check_sets() if name != "performance"
    )

    collected = collect_site(identity, fetcher=fetcher)
    report = run_technical_audit(
        card["client_id"], collected.identity, collected,
        enabled_check_sets=verify_sets,
    )

    relevant = [
        result
        for result in report["results"]
        if result["check_id"] in check_ids
        and (result["check_id"], result["subject"].rstrip("/").lower()) in linked_pairs
    ]
    verified = bool(relevant) and all(item["status"] == "pass" for item in relevant)
    verification = {
        "checked_at": _now(),
        "verified": verified,
        "results": [
            {"check_id": item["check_id"], "subject": item["subject"], "status": item["status"]}
            for item in relevant
        ],
    }
    return _transition(
        sb, card, "verified" if verified else "still_failing",
        {"verification": verification},
    )
