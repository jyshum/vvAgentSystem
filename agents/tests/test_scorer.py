from src.improvement.scorer import (
    check_answer_first,
    check_faq_schema,
    check_comparison_tables,
    check_lists,
    check_freshness,
    check_word_count,
    check_source_citations,
    check_author_attribution,
    check_schema_validation,
    compute_structural_score,
    extract_body_text,
)


RICH_HTML = """
<html><head>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":"What is GEO?","acceptedAnswer":{"@type":"Answer","text":"GEO is optimization."}}]}</script>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Organization","name":"TestCo","url":"https://testco.com"}</script>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebSite","name":"TestCo","url":"https://testco.com"}</script>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"Home","item":"https://testco.com"}]}</script>
</head><body>
<h1>What is GEO?</h1>
<p>Generative Engine Optimization is a strategy that improves your brand visibility in AI-generated responses. Studies show that structured content increases citation rates by up to 17.3 percent according to research from the University of Tokyo.</p>
<h2>Key Benefits</h2>
<ol><li>Increased visibility</li><li>More citations</li><li>Better authority</li></ol>
<ul><li>Point A</li><li>Point B</li></ul>
<h2>Comparison</h2>
<table><thead><tr><th>Feature</th><th>GEO</th><th>SEO</th></tr></thead><tbody><tr><td>Focus</td><td>AI</td><td>Search</td></tr></tbody></table>
<h2>Sources</h2>
<p>According to <a href="https://example.edu/study">this study</a> and <a href="https://gov.example.org/report">this report</a> and <a href="https://external.com/data">external data</a>.</p>
<p>Written by Dr. Jane Smith, PhD in Computer Science. Reviewed by Prof. John Doe.</p>
</body></html>
"""


class TestCheckAnswerFirst:
    def test_declarative_opening(self):
        html = "<body><p>Generative Engine Optimization is a strategy that improves your brand visibility in AI responses. It works by structuring content for AI crawlers.</p></body>"
        result = check_answer_first(html)
        assert result["score"] > 0
        assert result["has_declarative_opening"] is True

    def test_question_opening(self):
        html = "<body><p>Have you ever wondered how AI search works? Let us explore the topic together and discover the answer.</p></body>"
        result = check_answer_first(html)
        assert result["score"] == 0

    def test_filler_opening(self):
        html = "<body><p>Welcome to our website! We are so glad you are here. Let us tell you about ourselves and what we do for our customers.</p></body>"
        result = check_answer_first(html)
        assert result["score"] == 0


class TestCheckFaqSchema:
    def test_valid_faq_present(self):
        result = check_faq_schema(RICH_HTML)
        assert result["score"] > 0
        assert result["has_faq"] is True

    def test_no_faq_schema(self):
        html = "<html><head></head><body><p>No FAQ here</p></body></html>"
        result = check_faq_schema(html)
        assert result["score"] == 0
        assert result["has_faq"] is False


class TestCheckComparisonTables:
    def test_table_with_comparison_headers(self):
        result = check_comparison_tables(RICH_HTML)
        assert result["score"] > 0
        assert result["table_count"] >= 1

    def test_no_tables(self):
        html = "<html><body><p>No tables</p></body></html>"
        result = check_comparison_tables(html)
        assert result["score"] == 0


class TestCheckLists:
    def test_has_lists(self):
        result = check_lists(RICH_HTML)
        assert result["score"] > 0
        assert result["list_count"] >= 2

    def test_no_lists(self):
        html = "<html><body><p>No lists</p></body></html>"
        result = check_lists(html)
        assert result["score"] == 0


class TestCheckFreshness:
    def test_recent_date(self):
        result = check_freshness("2026-07-01T00:00:00Z")
        assert result["score"] == 10

    def test_old_date(self):
        result = check_freshness("2025-01-01T00:00:00Z")
        assert result["score"] < 10

    def test_no_date(self):
        result = check_freshness(None)
        assert result["score"] == 0


class TestCheckWordCount:
    def test_long_content_with_sections(self):
        sections = "".join(f"<h2>Section {i}</h2><p>" + " ".join(["word"] * 700) + "</p>" for i in range(4))
        html = f"<body>{sections}</body>"
        result = check_word_count(html)
        assert result["score"] == 10

    def test_short_content(self):
        html = "<body><p>Short content here.</p></body>"
        result = check_word_count(html)
        assert result["score"] < 10


class TestCheckSourceCitations:
    def test_has_authoritative_citations(self):
        result = check_source_citations(RICH_HTML, "testco.com")
        assert result["score"] > 0
        assert result["external_count"] >= 3

    def test_no_external_links(self):
        html = '<html><body><p>No links at all</p></body></html>'
        result = check_source_citations(html, "testco.com")
        assert result["score"] == 0


class TestCheckAuthorAttribution:
    def test_has_author(self):
        result = check_author_attribution(RICH_HTML)
        assert result["score"] > 0

    def test_no_author(self):
        html = "<html><body><p>Just content, no author info.</p></body></html>"
        result = check_author_attribution(html)
        assert result["score"] == 0


class TestCheckSchemaValidation:
    def test_complete_schema(self):
        result = check_schema_validation(RICH_HTML)
        assert result["score"] > 0
        assert result["schema_status"] in ("valid_complete", "valid_incomplete")

    def test_no_schema(self):
        html = "<html><head></head><body><p>No schema</p></body></html>"
        result = check_schema_validation(html)
        assert result["score"] == 0
        assert result["schema_status"] == "missing"

    def test_broken_schema(self):
        html = '<html><head><script type="application/ld+json">{not valid json}</script></head><body></body></html>'
        result = check_schema_validation(html)
        assert result["schema_status"] == "broken"


class TestExtractBodyText:
    def test_strips_head_nav_and_scripts(self):
        html = """<html><head><title>T</title><style>.x{color:red}</style>
        <script>var a=1;</script></head>
        <body><nav>Menu Home About</nav>
        <p>Actual visible content about widgets.</p>
        <footer>Copyright</footer></body></html>"""
        text = extract_body_text(html)
        assert "Actual visible content about widgets." in text
        assert "var a=1" not in text
        assert "color:red" not in text
        assert "Menu Home About" not in text
        assert "Copyright" not in text

    def test_strips_script_and_style_in_body(self):
        html = """<html><head><title>T</title></head>
        <body><style>.y{color:blue}</style>
        <script>var b=2;</script>
        <p>Actual visible content about widgets.</p>
        </body></html>"""
        text = extract_body_text(html)
        assert "Actual visible content about widgets." in text
        assert "var b=2" not in text
        assert "color:blue" not in text

    def test_respects_max_chars(self):
        html = "<html><body><p>" + ("word " * 2000) + "</p></body></html>"
        assert len(extract_body_text(html, max_chars=500)) <= 500

    def test_empty_html_returns_empty_string(self):
        assert extract_body_text("") == ""


class TestComputeStructuralScore:
    def test_returns_total_and_breakdown(self):
        result = compute_structural_score(RICH_HTML, "testco.com", "2026-07-01T00:00:00Z")
        assert "structural_score" in result
        assert "check_results" in result
        assert 0 <= result["structural_score"] <= 100
        assert "answer_first" in result["check_results"]
        assert "schema_validation" in result["check_results"]
