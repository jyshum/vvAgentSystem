from src.improvement.card_generator import (
    classify_actions,
    build_content_brief,
    build_crawlability_card,
    prioritize_cards,
)


def _make_score_result(**overrides):
    base = {
        "structural_score": 60,
        "check_results": {
            "faq_schema": {"score": 10, "has_faq": True},
            "answer_first": {"score": 15, "has_declarative_opening": True},
            "source_citations": {"score": 8, "external_count": 5},
            "freshness": {"score": 10, "age_days": 30},
            "schema_validation": {"score": 15, "schema_status": "valid_complete"},
            "comparison_tables": {"score": 10, "table_count": 1},
            "lists": {"score": 10, "list_count": 3},
            "word_count": {"score": 10, "word_count": 2500},
            "author_attribution": {"score": 7, "has_author": True},
        },
        "schema_status": "valid_complete",
    }
    for k, v in overrides.items():
        if k in base["check_results"]:
            base["check_results"][k] = v
        else:
            base[k] = v
    return base


class TestClassifyActions:
    def test_missing_faq_schema(self):
        score = _make_score_result(faq_schema={"score": 0, "has_faq": False})
        actions = classify_actions(score, "https://example.com/page")
        action_types = [a["action_type"] for a in actions]
        assert "add_faq_schema" in action_types

    def test_not_answer_first(self):
        score = _make_score_result(answer_first={"score": 0, "has_declarative_opening": False})
        actions = classify_actions(score, "https://example.com/page")
        action_types = [a["action_type"] for a in actions]
        assert "restructure_intro" in action_types

    def test_no_citations(self):
        score = _make_score_result(source_citations={"score": 0, "external_count": 0})
        actions = classify_actions(score, "https://example.com/page")
        action_types = [a["action_type"] for a in actions]
        assert "add_citations" in action_types

    def test_stale_content(self):
        score = _make_score_result(freshness={"score": 1, "age_days": 400})
        actions = classify_actions(score, "https://example.com/page")
        action_types = [a["action_type"] for a in actions]
        assert "update_freshness" in action_types

    def test_missing_schema(self):
        score = _make_score_result(
            schema_validation={"score": 0, "schema_status": "missing"},
            schema_status="missing",
        )
        actions = classify_actions(score, "https://example.com/page")
        action_types = [a["action_type"] for a in actions]
        assert "generate_schema" in action_types

    def test_perfect_score_no_actions(self):
        score = _make_score_result()
        actions = classify_actions(score, "https://example.com/page")
        assert len(actions) == 0


class TestBuildContentBrief:
    def test_returns_brief_structure(self):
        brief = build_content_brief(
            query="best budgeting tools for med students",
            query_id="q1",
            competitive_gap=0.4,
            top_competitor="CompA",
        )
        assert brief["action_type"] == "content_brief"
        assert brief["track"] == "manual"
        assert brief["priority"] == 2
        assert brief["brief"]["target_query"] == "best budgeting tools for med students"
        assert brief["competitive_gap"] == 0.4

    def test_brief_has_required_fields(self):
        brief = build_content_brief(query="test query", query_id="q1", competitive_gap=0.2, top_competitor="CompB")
        required_keys = ["target_query", "recommended_title", "recommended_h1", "key_sections", "schema_type", "word_count_target"]
        for key in required_keys:
            assert key in brief["brief"], f"Missing key: {key}"


class TestPrioritizeCards:
    def test_competitive_gap_pages_first(self):
        cards = [
            {"action_type": "add_faq_schema", "priority": 3, "competitive_gap": None},
            {"action_type": "restructure_intro", "priority": 1, "competitive_gap": 0.4},
            {"action_type": "content_brief", "priority": 2, "competitive_gap": 0.6},
        ]
        sorted_cards = prioritize_cards(cards)
        assert sorted_cards[0]["priority"] == 1
        assert sorted_cards[-1]["priority"] == 3

    def test_within_same_priority_sort_by_gap(self):
        cards = [
            {"action_type": "a", "priority": 1, "competitive_gap": 0.2},
            {"action_type": "b", "priority": 1, "competitive_gap": 0.8},
        ]
        sorted_cards = prioritize_cards(cards)
        assert sorted_cards[0]["competitive_gap"] == 0.8


class TestBuildCrawlabilityCard:
    def test_lists_failing_critical_checks(self):
        report = {
            "robots_txt": {"status": "fail", "detail": "GPTBot disallowed in robots.txt"},
            "js_rendering": {"status": "pass"},
            "cdn_blocks": {"status": "fail", "detail": "403 for GPTBot user agent"},
            "has_critical_blocker": True,
        }
        card = build_crawlability_card(report, "example.com")
        assert card["action_type"] == "fix_crawlability"
        assert card["track"] == "manual"
        assert card["priority"] == 0
        assert card["status"] == "pending"
        assert card["page_url"] == "https://example.com"
        assert "GPTBot disallowed" in card["issue"]
        assert "403 for GPTBot" in card["issue"]

    def test_check_without_detail_falls_back_to_check_name(self):
        report = {
            "robots_txt": {"status": "fail"},
            "js_rendering": {"status": "pass"},
            "cdn_blocks": {"status": "pass"},
            "has_critical_blocker": True,
        }
        card = build_crawlability_card(report, "example.com")
        assert "robots_txt" in card["issue"]
