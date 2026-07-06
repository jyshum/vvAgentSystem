"""Policy-based auto-approve for proven-safe action types.

Schema-only changes validated programmatically (JSON-LD parse + required
fields) carry near-zero risk. A client earns auto-approval for an action type
after `min_cycles` runs where every card of that type was approved or
implemented and none was ever rejected. Admins can also grant types explicitly
via clients.auto_approve_action_types.

Content-changing action types (intro rewrites, citations, freshness) are never
auto-approved from history — humans review anything that changes visible copy.
"""

from collections import defaultdict

# Only structurally-validatable, non-content action types can ever earn auto-approval.
HISTORY_ELIGIBLE_TYPES = {"add_faq_schema", "fix_schema", "generate_schema"}

RESOLVED_STATUSES = {"approved", "implemented"}


def compute_eligible_action_types(card_history: list[dict], min_cycles: int = 3) -> set[str]:
    """Earned eligibility from past automated cards for one client.

    A run counts as clean for an action type when every card of that type in
    the run resolved to approved/implemented. Any rejection ever disqualifies
    the type outright.
    """
    by_type_run: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    rejected_types: set[str] = set()

    for card in card_history:
        action_type = card.get("action_type", "")
        if action_type not in HISTORY_ELIGIBLE_TYPES:
            continue
        if card.get("track") != "automated":
            continue
        status = card.get("status", "")
        if status == "rejected":
            rejected_types.add(action_type)
        by_type_run[action_type][card.get("run_id", "")].append(status)

    eligible = set()
    for action_type, runs in by_type_run.items():
        if action_type in rejected_types:
            continue
        clean_runs = sum(
            1 for statuses in runs.values()
            if statuses and all(s in RESOLVED_STATUSES for s in statuses)
        )
        if clean_runs >= min_cycles:
            eligible.add(action_type)
    return eligible


def apply_auto_approve(cards: list[dict], eligible_types: set[str]) -> int:
    """Mark eligible cards approved in place. Returns count auto-approved."""
    count = 0
    for card in cards:
        if (
            card.get("track") == "automated"
            and card.get("action_type") in eligible_types
            and card.get("validation_passed")
            and card.get("status") == "pending"
        ):
            card["status"] = "approved"
            card["auto_approved"] = True
            count += 1
    return count
