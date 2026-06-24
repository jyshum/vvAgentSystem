from src.parsers import strip_boilerplate, parse_html


def test_strip_boilerplate_removes_nav_and_footer():
    html = """
    <html><body>
      <nav><a href="/">Home</a></nav>
      <main><p>This is real content with enough words to matter here.</p></main>
      <footer><p>Copyright 2026</p></footer>
    </body></html>
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    stripped = strip_boilerplate(soup)
    text = stripped.get_text()
    assert "Copyright" not in text
    assert "Home" not in text
    assert "real content" in text


def test_parsed_page_extracts_headings():
    html = """
    <html><body>
      <h1>Main Title</h1>
      <h2>How does this work?</h2>
      <h3>What are the benefits?</h3>
      <p>Some content here that is long enough to count as a paragraph body text.</p>
    </body></html>
    """
    page = parse_html("https://example.com", html, "example.com", 200)
    assert len(page.headings) == 3
    assert page.headings[1]["level"] == 2
    assert page.headings[1]["text"] == "How does this work?"


def test_parsed_page_finds_external_links_only():
    html = """
    <html><body>
      <p>See the <a href="https://ontario.ca/childcare">Ontario report</a> for details.
      Also visit our <a href="/about">about page</a>.</p>
    </body></html>
    """
    page = parse_html("https://childspot.ca/page", html, "childspot.ca", 200)
    assert len(page.external_links) == 1
    assert "ontario.ca" in page.external_links[0]
