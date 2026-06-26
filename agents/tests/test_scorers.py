from src.parsers import ParsedPage
from src.scorers import score_source_citations, score_schema_markup, score_freshness


def _make_page(**kwargs) -> ParsedPage:
    defaults = dict(
        url="https://childspot.ca/page",
        title="Test Page",
        headings=[],
        paragraphs=[],
        word_count=400,
        external_links=[],
        schema_blocks=[],
        raw_text="Some content here",
        modified_date=None,
        last_modified_header=None,
        status_code=200,
    )
    defaults.update(kwargs)
    return ParsedPage(**defaults)


def test_source_citations_zero_external_links():
    page = _make_page(external_links=[])
    result = score_source_citations(page, "childspot.ca")
    assert result["score"] == 0
    assert len(result["issues"]) > 0


def test_source_citations_three_links_good_score():
    page = _make_page(external_links=[
        "https://ontario.ca/childcare",
        "https://statcan.gc.ca/report",
        "https://example.com/article",
    ])
    result = score_source_citations(page, "childspot.ca")
    assert result["score"] >= 55


def test_source_citations_gov_link_gets_bonus():
    page_no_gov = _make_page(external_links=["https://example.com", "https://blog.com", "https://site.com"])
    page_with_gov = _make_page(external_links=["https://ontario.ca", "https://canada.ca", "https://statcan.gc.ca"])
    score_no_gov = score_source_citations(page_no_gov, "childspot.ca")["score"]
    score_with_gov = score_source_citations(page_with_gov, "childspot.ca")["score"]
    assert score_with_gov > score_no_gov


def test_schema_no_blocks_scores_zero():
    page = _make_page(schema_blocks=[])
    result = score_schema_markup(page)
    assert result["score"] == 0


def test_schema_faqpage_scores_high():
    page = _make_page(schema_blocks=[{"@type": "FAQPage", "mainEntity": []}])
    result = score_schema_markup(page)
    assert result["score"] >= 80


def test_schema_malformed_block_flagged():
    page = _make_page(schema_blocks=[{"_malformed": True}])
    result = score_schema_markup(page)
    assert any("malformed" in i.lower() for i in result["issues"])


def test_freshness_no_date_scores_low():
    page = _make_page(modified_date=None, last_modified_header=None)
    result = score_freshness(page)
    assert result["score"] <= 20


def test_freshness_recent_date_scores_high():
    page = _make_page(modified_date="2026-06-01T00:00:00Z")
    result = score_freshness(page)
    assert result["score"] == 100


def test_freshness_old_date_scores_low():
    page = _make_page(modified_date="2025-01-01T00:00:00Z")
    result = score_freshness(page)
    assert result["score"] <= 35


def test_source_citations_returns_strengths_key():
    page = _make_page(external_links=[
        "https://ontario.ca/childcare",
        "https://statcan.gc.ca/report",
        "https://example.com/article",
    ])
    result = score_source_citations(page, "childspot.ca")
    assert "strengths" in result


def test_source_citations_strengths_when_authoritative():
    page = _make_page(external_links=[
        "https://ontario.ca/childcare",
        "https://statcan.gc.ca/report",
        "https://canada.ca/data",
    ])
    result = score_source_citations(page, "childspot.ca")
    assert len(result["strengths"]) > 0
    assert any("authoritative" in s.lower() for s in result["strengths"])


def test_source_citations_no_strengths_when_zero():
    page = _make_page(external_links=[])
    result = score_source_citations(page, "childspot.ca")
    assert result["strengths"] == []


def test_schema_markup_strengths_when_perfect():
    page = _make_page(schema_blocks=[
        {"@type": "FAQPage", "mainEntity": []},
        {"@type": "Organization", "name": "Test"},
    ])
    result = score_schema_markup(page)
    assert len(result["strengths"]) > 0


def test_schema_markup_no_strengths_when_zero():
    page = _make_page(schema_blocks=[])
    result = score_schema_markup(page)
    assert result["strengths"] == []


def test_freshness_strengths_when_recent():
    page = _make_page(modified_date="2026-06-01T00:00:00Z")
    result = score_freshness(page)
    assert len(result["strengths"]) > 0


def test_freshness_no_strengths_when_no_date():
    page = _make_page(modified_date=None, last_modified_header=None)
    result = score_freshness(page)
    assert result["strengths"] == []


from unittest.mock import patch
from src.scorers import score_with_haiku_batch


def test_haiku_batch_returns_three_pillar_scores():
    fake_response = """{
      "content_structure": {"score": 45, "issues": ["Opening paragraph is marketing copy"], "recommendations": ["Lead with a direct answer"]},
      "fact_density": {"score": 20, "issues": ["Only 0.2 facts per 200 words"], "recommendations": ["Add specific statistics"]},
      "authority_signals": {"score": 10, "issues": ["No press mentions found"], "recommendations": ["Add a Featured In section"]}
    }"""

    with patch("src.scorers._call_haiku", return_value=fake_response):
        result = score_with_haiku_batch("Some page content here.", ["p1 text"], [{"level": 2, "text": "About us"}])

    assert "content_structure" in result
    assert "fact_density" in result
    assert "authority_signals" in result
    assert result["content_structure"]["score"] == 45
