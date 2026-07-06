from unittest.mock import patch, MagicMock
from src.improvement.card_qa import check_grounding, haiku_review, qa_card


class TestCheckGrounding:
    def test_before_text_present_on_page_passes(self):
        page_text = "Our widget service costs $50 per month and includes support."
        result = check_grounding("costs $50 per month", page_text)
        assert result["passed"] is True

    def test_before_text_absent_fails(self):
        result = check_grounding("this sentence is not on the page", "totally different page content here")
        assert result["passed"] is False
        assert "not found" in result["reason"].lower()

    def test_whitespace_and_case_normalized(self):
        page_text = "Our   Widget\nService costs $50."
        result = check_grounding("our widget service", page_text)
        assert result["passed"] is True

    def test_empty_or_none_before_text_skips_check(self):
        assert check_grounding("", "anything")["passed"] is True
        assert check_grounding("none", "anything")["passed"] is True

    def test_ascii_quote_matches_unicode_punctuation_on_page(self):
        # Sonnet quotes in ASCII; the page uses curly quotes, an em-dash, and a non-breaking space.
        page_text = "We’re the “best choice” for teams—fast setup and 24/7 support."
        result = check_grounding(
            'We\'re the "best choice" for teams-fast setup and 24/7 support.',
            page_text,
        )
        assert result["passed"] is True

    def test_unicode_quote_matches_ascii_punctuation_on_page(self):
        # Reverse direction: before_text carries unicode punctuation, page is ASCII.
        page_text = 'We\'re the "best choice" for teams - fast setup.'
        result = check_grounding(
            "We’re the “best choice” for teams – fast setup.",
            page_text,
        )
        assert result["passed"] is True


class TestQaCard:
    @patch("src.improvement.card_qa.haiku_review")
    def test_passes_when_grounded_and_haiku_approves(self, mock_haiku):
        mock_haiku.return_value = {"verdict": "pass", "reason": "specific"}
        card = {"action_type": "restructure_intro", "before_text": "old intro text",
                "after_text": "New specific intro answering the query.", "code_block": ""}
        result = qa_card(card, "page containing the old intro text somewhere")
        assert result["passed"] is True

    @patch("src.improvement.card_qa.haiku_review")
    def test_fails_on_ungrounded_before_text_without_calling_haiku(self, mock_haiku):
        card = {"action_type": "restructure_intro", "before_text": "hallucinated quote",
                "after_text": "whatever", "code_block": ""}
        result = qa_card(card, "page text that does not contain that quote")
        assert result["passed"] is False
        mock_haiku.assert_not_called()

    @patch("src.improvement.card_qa.haiku_review")
    def test_fails_when_haiku_rejects(self, mock_haiku):
        mock_haiku.return_value = {"verdict": "fail", "reason": "generic boilerplate"}
        card = {"action_type": "add_faq_schema", "before_text": "",
                "after_text": "", "code_block": '{"@type":"FAQPage"}'}
        result = qa_card(card, "any page text")
        assert result["passed"] is False
        assert "generic boilerplate" in result["reason"]

    @patch("src.improvement.card_qa.haiku_review")
    def test_fails_when_card_has_no_content_at_all(self, mock_haiku):
        card = {"action_type": "restructure_intro", "before_text": "",
                "after_text": "", "code_block": ""}
        result = qa_card(card, "page text")
        assert result["passed"] is False
        mock_haiku.assert_not_called()

    @patch("src.improvement.card_qa.haiku_review")
    def test_haiku_error_passes_open(self, mock_haiku):
        """QA is a filter, not a gate — if Haiku errors, let the card through to human review."""
        mock_haiku.return_value = {"verdict": "error", "reason": "api down"}
        card = {"action_type": "restructure_intro", "before_text": "",
                "after_text": "Some replacement text.", "code_block": ""}
        result = qa_card(card, "page text")
        assert result["passed"] is True


def _mock_client_returning(text: str) -> MagicMock:
    client = MagicMock()
    client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=text)]
    )
    return client


CARD = {"action_type": "restructure_intro", "before_text": "",
        "after_text": "Some replacement text.", "code_block": ""}


class TestHaikuReview:
    @patch("src.improvement.card_qa._get_client")
    def test_clean_json_verdict_passed_through(self, mock_get_client):
        mock_get_client.return_value = _mock_client_returning(
            '{"verdict": "fail", "reason": "generic filler"}'
        )
        result = haiku_review(CARD)
        assert result == {"verdict": "fail", "reason": "generic filler"}

    @patch("src.improvement.card_qa._get_client")
    def test_unknown_verdict_coerced_to_error(self, mock_get_client):
        mock_get_client.return_value = _mock_client_returning(
            '{"verdict": "maybe", "reason": "unsure"}'
        )
        result = haiku_review(CARD)
        assert result["verdict"] == "error"

    @patch("src.improvement.card_qa._get_client")
    def test_json_wrapped_in_prose_uses_regex_fallback(self, mock_get_client):
        mock_get_client.return_value = _mock_client_returning(
            'Here is my assessment:\n{"verdict": "pass", "reason": "specific to page"}\nHope that helps!'
        )
        result = haiku_review(CARD)
        assert result == {"verdict": "pass", "reason": "specific to page"}

    @patch("src.improvement.card_qa._get_client")
    def test_garbage_response_returns_error(self, mock_get_client):
        mock_get_client.return_value = _mock_client_returning("I cannot evaluate this.")
        result = haiku_review(CARD)
        assert result["verdict"] == "error"
        assert "unparseable" in result["reason"].lower()

    @patch("src.improvement.card_qa._get_client")
    def test_client_exception_returns_error(self, mock_get_client):
        client = MagicMock()
        client.messages.create.side_effect = RuntimeError("api down")
        mock_get_client.return_value = client
        result = haiku_review(CARD)
        assert result["verdict"] == "error"
        assert "api down" in result["reason"]
