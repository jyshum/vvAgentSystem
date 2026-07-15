from src.improvement.community import select_community_opportunities


def _gap(**over):
    gap = {
        "query": "best daycare software",
        "query_id": "q-1",
        "bucket": "consideration",
        "client_mention_rate": 0.2,
        "competitor_data": [
            {"name": "KinderCare", "mention_rate": 0.6},
        ],
    }
    gap.update(over)
    return gap


def test_selects_direct_community_opportunity_from_competitor_gap():
    selection = select_community_opportunities([_gap()])

    assert selection.competitor_lead_count == 1
    assert len(selection.opportunities) == 1
    opportunity = selection.opportunities[0]
    assert opportunity.query == "best daycare software"
    assert opportunity.query_id == "q-1"
    assert opportunity.bucket == "consideration"
    assert opportunity.top_competitor == "KinderCare"
    assert opportunity.client_mention_rate == 0.2
    assert opportunity.competitor_mention_rate == 0.6
    assert opportunity.competitive_gap == 0.4


def test_ignores_rows_without_a_positive_competitor_lead():
    selection = select_community_opportunities([
        _gap(query_id="q-no-evidence", competitor_data=[]),
        _gap(
            query_id="q-client-leads",
            client_mention_rate=0.7,
            competitor_data=[{"name": "KinderCare", "mention_rate": 0.6}],
        ),
    ])

    assert selection.competitor_lead_count == 0
    assert selection.opportunities == ()
