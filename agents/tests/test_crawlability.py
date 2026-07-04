from src.improvement.crawlability import (
    check_robots_txt,
    check_js_rendering,
    check_cdn_blocks,
    check_sitemap,
    check_meta_tags,
    check_llms_txt,
    run_crawlability_gate,
    AI_USER_AGENTS,
)


class TestCheckRobotsTxt:
    def test_all_allowed(self):
        result = check_robots_txt("User-agent: *\nAllow: /\n")
        assert result["status"] == "pass"
        assert result["blocked_agents"] == []

    def test_gptbot_blocked(self):
        result = check_robots_txt("User-agent: GPTBot\nDisallow: /\n")
        assert result["status"] == "fail"
        assert "GPTBot" in result["blocked_agents"]

    def test_wildcard_disallow_all(self):
        result = check_robots_txt("User-agent: *\nDisallow: /\n")
        assert result["status"] == "fail"
        assert len(result["blocked_agents"]) == len(AI_USER_AGENTS)

    def test_partial_disallow(self):
        robots = (
            "User-agent: GPTBot\nDisallow: /\n\n"
            "User-agent: ClaudeBot\nDisallow: /\n\n"
            "User-agent: *\nAllow: /\n"
        )
        result = check_robots_txt(robots)
        assert result["status"] == "fail"
        assert "GPTBot" in result["blocked_agents"]
        assert "ClaudeBot" in result["blocked_agents"]
        assert "PerplexityBot" not in result["blocked_agents"]

    def test_empty_robots(self):
        result = check_robots_txt("")
        assert result["status"] == "pass"

    def test_disallow_specific_path_not_root(self):
        result = check_robots_txt("User-agent: GPTBot\nDisallow: /private/\n")
        assert result["status"] == "warning"
        assert "GPTBot" in result["partial_blocks"][0]


class TestCheckJsRendering:
    def test_sufficient_content(self):
        html = "<html><head><title>Test</title></head><body>" + " ".join(["word"] * 300) + "</body></html>"
        result = check_js_rendering(html, "https://example.com")
        assert result["status"] == "pass"

    def test_js_dependent_page(self):
        html = '<html><head><title>My App</title></head><body><div id="root"></div><script src="app.js"></script></body></html>'
        result = check_js_rendering(html, "https://example.com")
        assert result["status"] == "fail"

    def test_minimal_but_enough_content(self):
        html = "<html><head><title>Test</title></head><body>" + " ".join(["word"] * 201) + "</body></html>"
        result = check_js_rendering(html, "https://example.com")
        assert result["status"] == "pass"

    def test_no_body_tag(self):
        result = check_js_rendering("<html><head></head></html>", "https://example.com")
        assert result["status"] == "fail"


class TestCheckCdnBlocks:
    def test_200_ok(self):
        result = check_cdn_blocks(200, "OK")
        assert result["status"] == "pass"

    def test_403_blocked(self):
        result = check_cdn_blocks(403, "Forbidden")
        assert result["status"] == "fail"
        assert "403" in result["detail"]

    def test_503_blocked(self):
        result = check_cdn_blocks(503, "Service Unavailable")
        assert result["status"] == "fail"

    def test_404_warning(self):
        result = check_cdn_blocks(404, "Not Found")
        assert result["status"] == "warning"


class TestCheckSitemap:
    def test_valid_sitemap(self):
        xml = '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/</loc></url></urlset>'
        result = check_sitemap(200, xml, robots_references_sitemap=True)
        assert result["status"] == "pass"
        assert result["url_count"] == 1

    def test_missing_sitemap(self):
        result = check_sitemap(404, "", robots_references_sitemap=False)
        assert result["status"] == "warning"

    def test_sitemap_not_in_robots(self):
        xml = '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/</loc></url></urlset>'
        result = check_sitemap(200, xml, robots_references_sitemap=False)
        assert result["status"] == "warning"
        assert "robots.txt" in result["detail"]


class TestCheckMetaTags:
    def test_no_blocking_tags(self):
        html = '<html><head><meta name="description" content="Hello"></head><body>Content</body></html>'
        result = check_meta_tags(html)
        assert result["status"] == "pass"

    def test_noindex_found(self):
        html = '<html><head><meta name="robots" content="noindex"></head><body>Content</body></html>'
        result = check_meta_tags(html)
        assert result["status"] == "fail"
        assert "noindex" in result["detail"]

    def test_nosnippet_found(self):
        html = '<html><head><meta name="robots" content="nosnippet"></head><body>Content</body></html>'
        result = check_meta_tags(html)
        assert result["status"] == "warning"
        assert "nosnippet" in result["detail"]


class TestCheckLlmsTxt:
    def test_exists(self):
        result = check_llms_txt(200, "# LLMs.txt\nSome content")
        assert result["status"] == "pass"

    def test_missing(self):
        result = check_llms_txt(404, "")
        assert result["status"] == "info"


class TestRunCrawlabilityGate:
    def test_returns_report_structure(self):
        report = run_crawlability_gate.__wrapped__(
            domain="example.com",
            robots_content="User-agent: *\nAllow: /\n",
            homepage_html="<html><body>" + " ".join(["word"] * 300) + "</body></html>",
            homepage_status=200,
            sitemap_status=200,
            sitemap_content='<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/</loc></url></urlset>',
            llms_txt_status=404,
            llms_txt_content="",
        )
        assert "robots_txt" in report
        assert "js_rendering" in report
        assert "cdn_blocks" in report
        assert "sitemap" in report
        assert "meta_tags" in report
        assert "llms_txt" in report
        assert "has_critical_blocker" in report
        assert report["has_critical_blocker"] is False

    def test_critical_blocker_detected(self):
        report = run_crawlability_gate.__wrapped__(
            domain="example.com",
            robots_content="User-agent: GPTBot\nDisallow: /\n",
            homepage_html="<html><body>" + " ".join(["word"] * 300) + "</body></html>",
            homepage_status=200,
            sitemap_status=200,
            sitemap_content='<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/</loc></url></urlset>',
            llms_txt_status=404,
            llms_txt_content="",
        )
        assert report["has_critical_blocker"] is True
