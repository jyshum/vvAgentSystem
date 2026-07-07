from src.improvement.card_generator import build_community_check_card


def _gap(**over):
    gap = {
        "query": "best daycare software",
        "query_id": "q-1",
        "competitive_gap": 0.4,
        "top_competitor": "KinderCare",
        "client_mention_rate": 0.2,
        "competitor_mention_rate": 0.6,
    }
    gap.update(over)
    return gap


def test_card_shape():
    card = build_community_check_card(_gap())
    assert card["action_type"] == "community_check"
    assert card["track"] == "manual"
    assert card["priority"] == 2
    assert card["query_id"] == "q-1"
    assert card["status"] == "pending"
    assert card["cms_action"] == "none"
    assert card["page_url"] is None


def test_search_links_are_prebuilt():
    card = build_community_check_card(_gap())
    links = card["reddit_data"]["search_links"]
    assert links["reddit"] == "https://www.reddit.com/search/?q=best+daycare+software"
    assert "site%3Areddit.com+best+daycare+software" in links["google"]


def test_issue_names_competitor_and_gap():
    card = build_community_check_card(_gap())
    assert "KinderCare" in card["issue"]
    assert "40%" in card["issue"]


def test_issue_without_competitor():
    card = build_community_check_card(_gap(top_competitor=None, competitive_gap=0.0))
    assert "KinderCare" not in card["issue"]


def test_guidance_and_thread_url_field():
    card = build_community_check_card(_gap())
    assert card["reddit_data"]["thread_url"] is None
    assert "drip" in card["reddit_data"]["guidance"].lower() or "genuinely" in card["reddit_data"]["guidance"].lower()
