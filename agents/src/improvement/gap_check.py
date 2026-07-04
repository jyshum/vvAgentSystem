"""Competitive gap check — Step 5 of the improvement pipeline.

Computes the competitive gap between the client and top competitor for each
query that matched in the content audit. Positive gap = competitor winning
(higher mention rate). Negative gap = client winning.

Gap data originates from the tracker (Phase 2) and feeds into action card
prioritization — pages with competitive gaps receive priority 1.
"""

from __future__ import annotations


def compute_gap_for_query(gap_data: dict) -> dict:
    """Compute the competitive gap for a single query.

    Parameters
    ----------
    gap_data:
        {
            "query": str,
            "client_mention_rate": float,
            "competitor_data": [{"name": str, "mention_rate": float}, ...]
        }

    Returns
    -------
    {
        "query": str,
        "competitive_gap": float,          # rounded to 4 decimal places
        "top_competitor": str | None,
        "client_mention_rate": float,
        "competitor_mention_rate": float,  # max competitor rate (0.0 if none)
    }

    Convention: positive gap means a competitor has a higher mention rate than
    the client; negative gap means the client is winning.
    """
    query: str = gap_data["query"]
    client_rate: float = gap_data["client_mention_rate"]
    competitors: list[dict] = gap_data.get("competitor_data", [])

    if not competitors:
        return {
            "query": query,
            "competitive_gap": 0.0,
            "top_competitor": None,
            "client_mention_rate": client_rate,
            "competitor_mention_rate": 0.0,
        }

    top = max(competitors, key=lambda c: c["mention_rate"])
    top_rate: float = top["mention_rate"]
    gap = round(top_rate - client_rate, 4)

    return {
        "query": query,
        "competitive_gap": gap,
        "top_competitor": top["name"],
        "client_mention_rate": client_rate,
        "competitor_mention_rate": top_rate,
    }


def check_competitive_gaps(
    matches: list[dict],
    gap_data_list: list[dict],
) -> list[dict]:
    """For each query in *matches*, look up its competitive gap.

    Parameters
    ----------
    matches:
        List of audit matches, each containing at minimum:
        {"query": str, "query_id": str, "match_type": str, "matched_page_url": str | None}
    gap_data_list:
        List of gap data dicts as returned/stored by the tracker, each with
        {"query": str, "client_mention_rate": float, "competitor_data": [...]}

    Returns
    -------
    List of gap result dicts (one per entry in *matches*), each containing the
    fields from :func:`compute_gap_for_query` plus ``"query_id"``.
    """
    # Build lookup by query name for O(1) access.
    gap_lookup: dict[str, dict] = {gd["query"]: gd for gd in gap_data_list}

    results: list[dict] = []
    for match in matches:
        query: str = match["query"]
        query_id: str = match["query_id"]

        gap_data = gap_lookup.get(query)
        if gap_data is None:
            # No tracker data for this query — return a zero-gap placeholder.
            gap_data = {
                "query": query,
                "client_mention_rate": 0.0,
                "competitor_data": [],
            }

        result = compute_gap_for_query(gap_data)
        result["query_id"] = query_id
        results.append(result)

    return results
