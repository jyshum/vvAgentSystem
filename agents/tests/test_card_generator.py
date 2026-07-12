import json
from unittest.mock import patch, MagicMock

import pytest

from src.improvement.card_generator import (
    CardGenerationError,
    DEFAULT_CARD_GEN_MODEL,
    _card_gen_model,
    classify_actions,
    build_content_brief,
    build_crawlability_card,
    generate_sonnet_quality,
    generate_sonnet_specifics,
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


def _mock_client_returning(text: str) -> MagicMock:
    client = MagicMock()
    client.messages.create.return_value = MagicMock(content=[MagicMock(type="text", text=text)])
    return client


class TestThinkingBlockHandling:
    @patch("src.improvement.card_generator._get_client")
    def test_text_extracted_when_thinking_block_precedes_it(self, mock_get_client):
        """Sonnet 5 runs adaptive thinking by default — content[0] may be a
        thinking block with no .text worth reading."""
        thinking = MagicMock(type="thinking")
        text = MagicMock(type="text", text=json.dumps({
            "specificity": 4, "completeness": 3, "answer_directness": 5, "summary": "ok",
        }))
        client = MagicMock()
        client.messages.create.return_value = MagicMock(content=[thinking, text])
        mock_get_client.return_value = client

        result = generate_sonnet_quality("page text", "query", {})
        assert result["specificity"] == 4

    @patch("src.improvement.card_generator._get_client")
    def test_thinking_disabled_on_card_calls(self, mock_get_client):
        client = _mock_client_returning("{}")
        mock_get_client.return_value = client
        generate_sonnet_quality("page text", "query", {})
        assert client.messages.create.call_args.kwargs["thinking"] == {"type": "disabled"}

    @patch("src.improvement.card_generator._get_client")
    def test_no_text_blocks_raises(self, mock_get_client):
        client = MagicMock()
        client.messages.create.return_value = MagicMock(content=[MagicMock(type="thinking")])
        mock_get_client.return_value = client
        with pytest.raises(CardGenerationError, match="no text"):
            generate_sonnet_quality("page text", "query", {})


class TestCardGenModel:
    def test_default_is_not_a_retired_snapshot(self):
        assert DEFAULT_CARD_GEN_MODEL != "claude-sonnet-4-20250514"
        assert _card_gen_model() == DEFAULT_CARD_GEN_MODEL

    def test_env_var_overrides_default(self, monkeypatch):
        monkeypatch.setenv("CARD_GEN_MODEL", "claude-test-model")
        assert _card_gen_model() == "claude-test-model"

    @patch("src.improvement.card_generator._get_client")
    def test_api_calls_use_configured_model(self, mock_get_client, monkeypatch):
        monkeypatch.setenv("CARD_GEN_MODEL", "claude-test-model")
        client = _mock_client_returning(json.dumps({
            "before_text": "old", "after_text": "new", "code_block": "",
        }))
        mock_get_client.return_value = client

        generate_sonnet_specifics("page text", "query", "add_citations", "issue", "gap")
        assert client.messages.create.call_args.kwargs["model"] == "claude-test-model"

        generate_sonnet_quality("page text", "query", {})
        assert client.messages.create.call_args.kwargs["model"] == "claude-test-model"


class TestApiFailuresAreLoud:
    @patch("src.improvement.card_generator._get_client")
    def test_specifics_raises_on_api_error(self, mock_get_client):
        client = MagicMock()
        client.messages.create.side_effect = RuntimeError("404 model not found")
        mock_get_client.return_value = client

        with pytest.raises(CardGenerationError, match="404 model not found"):
            generate_sonnet_specifics("page text", "query", "add_citations", "issue", "gap")

    @patch("src.improvement.card_generator._get_client")
    def test_quality_raises_on_api_error(self, mock_get_client):
        client = MagicMock()
        client.messages.create.side_effect = RuntimeError("404 model not found")
        mock_get_client.return_value = client

        with pytest.raises(CardGenerationError, match="404 model not found"):
            generate_sonnet_quality("page text", "query", {})

    @patch("src.improvement.card_generator._get_client")
    def test_specifics_unparseable_response_still_falls_back(self, mock_get_client):
        mock_get_client.return_value = _mock_client_returning("not json at all")
        result = generate_sonnet_specifics("page text", "query", "add_citations", "issue", "gap")
        assert result == {"before_text": "", "after_text": "", "code_block": ""}

    @patch("src.improvement.card_generator._get_client")
    def test_quality_unparseable_response_still_falls_back(self, mock_get_client):
        mock_get_client.return_value = _mock_client_returning("not json at all")
        result = generate_sonnet_quality("page text", "query", {})
        assert result["specificity"] == 0
        assert result["completeness"] == 0
        assert result["answer_directness"] == 0


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
