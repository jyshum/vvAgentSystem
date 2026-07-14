from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CommunityOpportunity:
    query: str
    query_id: str | None
    bucket: str
    top_competitor: str
    client_mention_rate: float
    competitor_mention_rate: float
    competitive_gap: float

    def to_gap_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class CommunitySelection:
    opportunities: tuple[CommunityOpportunity, ...]
    competitor_lead_count: int


def select_community_opportunities(
    gap_rows: list[dict], *, limit: int = 5
) -> CommunitySelection:
    candidates: list[CommunityOpportunity] = []
    for row in gap_rows:
        competitors = row.get("competitor_data") or []
        if not competitors:
            continue
        top = max(competitors, key=lambda item: float(item.get("mention_rate") or 0.0))
        client_rate = float(row.get("client_mention_rate") or 0.0)
        competitor_rate = float(top.get("mention_rate") or 0.0)
        gap = round(competitor_rate - client_rate, 4)
        if gap <= 0:
            continue
        candidates.append(CommunityOpportunity(
            query=row["query"],
            query_id=row.get("query_id"),
            bucket=row.get("bucket") or "",
            top_competitor=top["name"],
            client_mention_rate=client_rate,
            competitor_mention_rate=competitor_rate,
            competitive_gap=gap,
        ))
    candidates.sort(key=lambda item: (
        -item.competitive_gap,
        item.query_id or item.query,
    ))
    return CommunitySelection(
        opportunities=tuple(candidates[:max(0, limit)]),
        competitor_lead_count=len(candidates),
    )
