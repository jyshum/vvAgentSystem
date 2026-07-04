from src.improvement.validators import (
    validate_json_ld,
    validate_html_fragment,
    check_link_alive,
)


class TestValidateJsonLd:
    def test_valid_faq_schema(self):
        json_ld = '{"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": "What is GEO?", "acceptedAnswer": {"@type": "Answer", "text": "GEO stands for Generative Engine Optimization."}}]}'
        result = validate_json_ld(json_ld)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_invalid_json(self):
        result = validate_json_ld("{not valid json}")
        assert result["valid"] is False
        assert any("parse" in e.lower() or "json" in e.lower() for e in result["errors"])

    def test_missing_context(self):
        result = validate_json_ld('{"@type": "FAQPage", "mainEntity": []}')
        assert result["valid"] is False
        assert any("@context" in e for e in result["errors"])

    def test_missing_type(self):
        result = validate_json_ld('{"@context": "https://schema.org", "name": "Test"}')
        assert result["valid"] is False
        assert any("@type" in e for e in result["errors"])

    def test_empty_string(self):
        result = validate_json_ld("")
        assert result["valid"] is False

    def test_valid_organization(self):
        result = validate_json_ld('{"@context": "https://schema.org", "@type": "Organization", "name": "TestCo", "url": "https://testco.com"}')
        assert result["valid"] is True

    def test_missing_required_field(self):
        result = validate_json_ld('{"@context": "https://schema.org", "@type": "Organization"}')
        assert result["valid"] is False
        assert any("name" in e for e in result["errors"])


class TestValidateHtmlFragment:
    def test_valid_html(self):
        result = validate_html_fragment("<p>Hello <strong>world</strong></p>")
        assert result["valid"] is True

    def test_empty_string(self):
        result = validate_html_fragment("")
        assert result["valid"] is False

    def test_script_injection(self):
        result = validate_html_fragment('<p>Hello</p><script>alert("xss")</script>')
        assert result["valid"] is False
        assert any("script" in e.lower() for e in result["errors"])

    def test_event_handler_injection(self):
        result = validate_html_fragment('<img onerror="alert(1)" src="x">')
        assert result["valid"] is False
        assert any("event handler" in e.lower() for e in result["errors"])


class TestCheckLinkAlive:
    def test_returns_dict_structure(self):
        result = check_link_alive("https://httpbin.org/status/200")
        assert "alive" in result
        assert "status_code" in result
        assert "url" in result
