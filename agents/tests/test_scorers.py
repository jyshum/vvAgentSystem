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
