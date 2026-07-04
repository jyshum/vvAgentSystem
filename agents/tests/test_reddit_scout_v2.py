from src.improvement.reddit_scout import (
    parse_google_results,
    detect_brand_mentions,
    build_scout_result,
)

SAMPLE_GOOGLE_HTML = """
<html><body>
<div class="g">
    <a href="https://www.reddit.com/r/personalfinance/comments/abc123/best_budgeting_tools/"><h3>Best budgeting tools for students - Reddit</h3></a>
    <div class="VwiC3b">Looking for recommendations on budgeting apps. CompetitorA seems popular but wondering about alternatives like BrandX.</div>
</div>
<div class="g">
    <a href="https://www.reddit.com/r/FinancialPlanning/comments/def456/mint_vs_ynab/"><h3>Mint vs YNAB for college students</h3></a>
    <div class="VwiC3b">Has anyone compared Mint and YNAB? I heard CompetitorA is better for students.</div>
</div>
<div class="g">
    <a href="https://www.reddit.com/r/budgeting/comments/ghi789/free_budget_apps/"><h3>Free budget apps recommendation thread</h3></a>
    <div class="VwiC3b">What free budgeting apps do you recommend? I tried BrandX and it was decent.</div>
</div>
</body></html>
"""


class TestParseGoogleResults:
    def test_extracts_reddit_threads(self):
        threads = parse_google_results(SAMPLE_GOOGLE_HTML)
        assert len(threads) >= 2
        assert all("url" in t for t in threads)
        assert all("title" in t for t in threads)
        assert all("reddit.com" in t["url"] for t in threads)

    def test_empty_html_returns_empty(self):
        threads = parse_google_results("<html><body></body></html>")
        assert threads == []

    def test_empty_string_returns_empty(self):
        threads = parse_google_results("")
        assert threads == []


class TestDetectBrandMentions:
    def test_detects_client_mention(self):
        threads = [
            {"title": "Best tools", "url": "https://reddit.com/r/test/1", "snippet": "BrandX is great"},
        ]
        result = detect_brand_mentions(threads, "BrandX", ["CompA", "CompB"])
        assert result["client_mentioned"] is True

    def test_detects_competitor_mentions(self):
        threads = [
            {"title": "Best tools - CompA review", "url": "https://reddit.com/r/test/1", "snippet": "CompA and CompB are popular"},
        ]
        result = detect_brand_mentions(threads, "BrandX", ["CompA", "CompB"])
        assert "CompA" in result["competitors_mentioned"]
        assert "CompB" in result["competitors_mentioned"]

    def test_no_mentions(self):
        threads = [
            {"title": "Random topic", "url": "https://reddit.com/r/test/1", "snippet": "Nothing relevant"},
        ]
        result = detect_brand_mentions(threads, "BrandX", ["CompA"])
        assert result["client_mentioned"] is False
        assert result["competitors_mentioned"] == []


class TestBuildScoutResult:
    def test_complete_result_structure(self):
        threads = [
            {"title": "Thread 1", "url": "https://reddit.com/1", "snippet": "text"},
            {"title": "Thread 2", "url": "https://reddit.com/2", "snippet": "text"},
        ]
        result = build_scout_result("best tools", threads, True, ["CompA"])
        assert result["query"] == "best tools"
        assert result["threads_found"] == 2
        assert result["client_mentioned"] is True
        assert "CompA" in result["competitors_mentioned"]
