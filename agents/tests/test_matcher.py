from src.improvement.matcher import (
    build_page_text,
    classify_match,
    match_queries_to_pages,
)


class TestBuildPageText:
    def test_concatenates_fields(self):
        page = {"title": "Best Tools", "h1": "Top 10 Tools", "first_paragraph": "Here are the tools."}
        result = build_page_text(page)
        assert "Best Tools" in result
        assert "Top 10 Tools" in result
        assert "Here are the tools" in result

    def test_handles_empty_h1(self):
        page = {"title": "Best Tools", "h1": "", "first_paragraph": "Content here."}
        result = build_page_text(page)
        assert "Best Tools" in result
        assert "Content here" in result


class TestClassifyMatch:
    def test_high_score_matched(self):
        assert classify_match(0.7) == "matched"

    def test_medium_score_weak(self):
        assert classify_match(0.4) == "weak"

    def test_low_score_content_gap(self):
        assert classify_match(0.2) == "content_gap"

    def test_boundary_matched(self):
        assert classify_match(0.51) == "matched"

    def test_boundary_weak(self):
        assert classify_match(0.5) == "weak"

    def test_boundary_gap_below(self):
        assert classify_match(0.29) == "content_gap"


class TestMatchQueriesToPages:
    def test_returns_match_per_query(self):
        pages = [
            {"url": "https://example.com/budgeting", "title": "Budgeting Guide", "h1": "How to Budget", "first_paragraph": "Learn budgeting strategies for saving money and managing expenses."},
            {"url": "https://example.com/investing", "title": "Investing 101", "h1": "Start Investing", "first_paragraph": "Learn how to invest in stocks, bonds, and mutual funds."},
        ]
        queries = [
            {"query": "best budgeting tips for students", "query_id": "q1", "bucket": "awareness"},
            {"query": "how to start investing in stocks", "query_id": "q2", "bucket": "consideration"},
        ]
        results = match_queries_to_pages(pages, queries)
        assert len(results) == 2
        assert all("match_type" in r for r in results)
        assert all("similarity_score" in r for r in results)
        assert all("query_id" in r for r in results)

    def test_content_gap_when_no_relevant_page(self):
        pages = [
            {"url": "https://example.com/about", "title": "About Us", "h1": "Our Company", "first_paragraph": "We are a company that does things."},
        ]
        queries = [
            {"query": "quantum computing applications in healthcare", "query_id": "q1", "bucket": "awareness"},
        ]
        results = match_queries_to_pages(pages, queries)
        assert len(results) == 1
        assert results[0]["similarity_score"] < 0.5

    def test_empty_pages_all_content_gaps(self):
        queries = [
            {"query": "test query", "query_id": "q1", "bucket": "awareness"},
        ]
        results = match_queries_to_pages([], queries)
        assert len(results) == 1
        assert results[0]["match_type"] == "content_gap"
        assert results[0]["matched_page_url"] is None

    def test_empty_queries_returns_empty(self):
        pages = [{"url": "https://example.com/", "title": "Home", "h1": "Welcome", "first_paragraph": "Hello world."}]
        results = match_queries_to_pages(pages, [])
        assert results == []
