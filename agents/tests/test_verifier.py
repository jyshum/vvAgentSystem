from unittest.mock import patch, MagicMock
from src.improvement.verifier import verify_implementation


def _mock_response(status=200, html="<html><head><title>T</title></head><body><p>hello</p></body></html>"):
    resp = MagicMock()
    resp.status_code = status
    resp.text = html
    return resp


class TestVerifyImplementation:
    @patch("src.improvement.verifier.httpx.get")
    def test_schema_card_verified_when_type_present(self, mock_get):
        html = ('<html><head><title>T</title></head><body><p>x</p>'
                '<script type="application/ld+json">'
                '{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[]}'
                '</script></body></html>')
        mock_get.return_value = _mock_response(html=html)
        card = {"page_url": "https://x.com/p1", "action_type": "add_faq_schema",
                "code_block": '{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[]}',
                "after_text": ""}
        result = verify_implementation(card)
        assert result["verified"] is True
        assert result["checks"]["page_renders"] is True
        assert result["checks"]["change_present"] is True

    @patch("src.improvement.verifier.httpx.get")
    def test_schema_card_fails_when_type_absent(self, mock_get):
        mock_get.return_value = _mock_response()
        card = {"page_url": "https://x.com/p1", "action_type": "add_faq_schema",
                "code_block": '{"@type":"FAQPage"}', "after_text": ""}
        result = verify_implementation(card)
        assert result["verified"] is False
        assert result["checks"]["change_present"] is False

    @patch("src.improvement.verifier.httpx.get")
    def test_content_card_verified_by_after_text_substring(self, mock_get):
        mock_get.return_value = _mock_response(
            html="<html><head><title>T</title></head><body><p>Widgets cost $50 per month, including support.</p></body></html>")
        card = {"page_url": "https://x.com/p1", "action_type": "restructure_intro",
                "code_block": "", "after_text": "Widgets cost $50 per month"}
        result = verify_implementation(card)
        assert result["verified"] is True

    @patch("src.improvement.verifier.httpx.get")
    def test_http_error_reports_unverified_with_error(self, mock_get):
        mock_get.side_effect = Exception("connection refused")
        card = {"page_url": "https://x.com/p1", "action_type": "restructure_intro",
                "code_block": "", "after_text": "anything"}
        result = verify_implementation(card)
        assert result["verified"] is False
        assert "connection refused" in result["error"]

    @patch("src.improvement.verifier.httpx.get")
    def test_broken_page_fails_render_check(self, mock_get):
        mock_get.return_value = _mock_response(status=500, html="Internal Server Error")
        card = {"page_url": "https://x.com/p1", "action_type": "restructure_intro",
                "code_block": "", "after_text": "anything"}
        result = verify_implementation(card)
        assert result["verified"] is False
        assert result["checks"]["page_renders"] is False

    def test_card_without_page_url_is_skipped(self):
        card = {"page_url": None, "action_type": "content_brief", "code_block": "", "after_text": ""}
        result = verify_implementation(card)
        assert result["verified"] is False
        assert result["skipped"] is True
