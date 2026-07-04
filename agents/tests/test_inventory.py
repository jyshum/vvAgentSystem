from src.improvement.inventory import extract_page_data, discover_pages_from_sitemap


SAMPLE_HTML = """
<html>
<head>
    <title>Best Budgeting Tools for Students</title>
    <meta property="article:modified_time" content="2026-06-15T00:00:00Z">
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": []}
    </script>
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "Organization", "name": "TestCo"}
    </script>
</head>
<body>
    <h1>Top 10 Budgeting Tools for College Students</h1>
    <p>Managing your finances in college can be challenging. Here are the best tools to help you budget effectively and save money while studying. These tools have been tested and reviewed by financial experts.</p>
    <h2>1. Mint</h2>
    <p>Mint is a free budgeting app that automatically tracks your spending.</p>
    <table>
        <thead><tr><th>Feature</th><th>Tool A</th><th>Tool B</th></tr></thead>
        <tbody><tr><td>Price</td><td>Free</td><td>$5/mo</td></tr></tbody>
    </table>
    <a href="https://external.com/source1">Source 1</a>
    <a href="https://external.com/source2">Source 2</a>
    <a href="https://testco.com/about">About Us</a>
</body>
</html>
"""


class TestExtractPageData:
    def test_extracts_title(self):
        data = extract_page_data("https://testco.com/blog/budgeting", SAMPLE_HTML, "testco.com")
        assert data["title"] == "Best Budgeting Tools for Students"

    def test_extracts_h1(self):
        data = extract_page_data("https://testco.com/blog/budgeting", SAMPLE_HTML, "testco.com")
        assert data["h1"] == "Top 10 Budgeting Tools for College Students"

    def test_extracts_first_paragraph(self):
        data = extract_page_data("https://testco.com/blog/budgeting", SAMPLE_HTML, "testco.com")
        assert "Managing your finances" in data["first_paragraph"]
        assert len(data["first_paragraph"]) <= 500

    def test_extracts_schema_types(self):
        data = extract_page_data("https://testco.com/blog/budgeting", SAMPLE_HTML, "testco.com")
        assert "FAQPage" in data["schema_types"]
        assert "Organization" in data["schema_types"]

    def test_counts_words(self):
        data = extract_page_data("https://testco.com/blog/budgeting", SAMPLE_HTML, "testco.com")
        assert data["word_count"] > 0

    def test_detects_last_modified(self):
        data = extract_page_data("https://testco.com/blog/budgeting", SAMPLE_HTML, "testco.com")
        assert data["last_modified"] is not None
        assert "2026-06-15" in data["last_modified"]

    def test_counts_outbound_links(self):
        data = extract_page_data("https://testco.com/blog/budgeting", SAMPLE_HTML, "testco.com")
        assert data["outbound_link_count"] == 2

    def test_detects_faq_schema(self):
        data = extract_page_data("https://testco.com/blog/budgeting", SAMPLE_HTML, "testco.com")
        assert data["has_faq_schema"] is True

    def test_detects_comparison_table(self):
        data = extract_page_data("https://testco.com/blog/budgeting", SAMPLE_HTML, "testco.com")
        assert data["has_comparison_table"] is True

    def test_stores_raw_html(self):
        data = extract_page_data("https://testco.com/blog/budgeting", SAMPLE_HTML, "testco.com")
        assert data["raw_html"] == SAMPLE_HTML

    def test_no_schema_page(self):
        html = "<html><head><title>Simple</title></head><body><h1>Hello</h1><p>World is a great place to be today</p></body></html>"
        data = extract_page_data("https://testco.com/simple", html, "testco.com")
        assert data["schema_types"] == []
        assert data["has_faq_schema"] is False

    def test_no_table_page(self):
        html = "<html><head><title>Simple</title></head><body><h1>Hello</h1><p>World is a great place to be today</p></body></html>"
        data = extract_page_data("https://testco.com/simple", html, "testco.com")
        assert data["has_comparison_table"] is False


class TestDiscoverPagesFromSitemap:
    def test_parses_sitemap_xml(self):
        xml = '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/</loc></url><url><loc>https://example.com/about</loc></url></urlset>'
        urls = discover_pages_from_sitemap(xml, "example.com", max_pages=20)
        assert len(urls) == 2
        assert "https://example.com/" in urls

    def test_respects_max_pages(self):
        locs = "".join(f"<url><loc>https://example.com/page{i}</loc></url>" for i in range(50))
        xml = f'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{locs}</urlset>'
        urls = discover_pages_from_sitemap(xml, "example.com", max_pages=10)
        assert len(urls) == 10

    def test_filters_external_domains(self):
        xml = '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/</loc></url><url><loc>https://other.com/page</loc></url></urlset>'
        urls = discover_pages_from_sitemap(xml, "example.com", max_pages=20)
        assert len(urls) == 1

    def test_invalid_xml_returns_empty(self):
        urls = discover_pages_from_sitemap("not xml at all", "example.com", max_pages=20)
        assert urls == []
