from src.improvement.community import select_community_opportunities


def _gap(query_id, query, client, competitors, bucket="consideration"):
    return {
        "query_id": query_id,
        "query": query,
        "bucket": bucket,
        "client_mention_rate": client,
        "competitor_data": competitors,
    }


def test_selects_only_positive_competitor_leads_in_descending_order():
    rows = [
        _gap("q2", "second", 0.20, [{"name": "B", "mention_rate": 0.60}]),
        _gap("q1", "first", 0.10, [{"name": "A", "mention_rate": 0.50}]),
        _gap("q3", "winning", 0.70, [{"name": "C", "mention_rate": 0.20}]),
        _gap("q4", "no evidence", 0.10, []),
    ]

    selection = select_community_opportunities(rows)

    assert selection.competitor_lead_count == 2
    assert [item.query_id for item in selection.opportunities] == ["q1", "q2"]
    assert selection.opportunities[0].top_competitor == "A"
    assert selection.opportunities[0].competitive_gap == 0.4


def test_uses_query_id_as_stable_tie_break_and_caps_at_five():
    rows = [
        _gap(f"q{i}", f"query {i}", 0.0, [{"name": "A", "mention_rate": 0.5}])
        for i in range(7, 0, -1)
    ]

    selection = select_community_opportunities(rows, limit=5)

    assert selection.competitor_lead_count == 7
    assert [item.query_id for item in selection.opportunities] == [
        "q1", "q2", "q3", "q4", "q5"
    ]


def test_card_payload_contains_measured_values_but_no_thread_claim():
    selection = select_community_opportunities([
        _gap("q1", "medical student budgeting", 0.1, [
            {"name": "Competitor", "mention_rate": 0.55}
        ])
    ])

    payload = selection.opportunities[0].to_gap_dict()

    assert payload == {
        "query": "medical student budgeting",
        "query_id": "q1",
        "bucket": "consideration",
        "top_competitor": "Competitor",
        "client_mention_rate": 0.1,
        "competitor_mention_rate": 0.55,
        "competitive_gap": 0.45,
    }
    assert "thread_url" not in payload
