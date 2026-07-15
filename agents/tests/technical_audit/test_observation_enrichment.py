from src.technical_audit.observations import extract_page_observation
from src.technical_audit.site import SiteIdentity


IDENTITY = SiteIdentity.from_domain("example.com", "other")


def _observation(html, url="https://example.com/page"):
    return extract_page_observation(
        {
            "url": url,
            "final_url": url,
            "raw_html": html,
            "content_type": "text/html",
            "available": True,
            "status_code": 200,
        },
        "2026-07-15T12:00:00+00:00",
        identity=IDENTITY,
    )


def test_links_are_classified_and_carry_fragments_and_content_flag():
    html = (
        "<html><body>"
        "<nav><a href='/nav-page'>Nav</a></nav>"
        "<main><a href='/inside#section'>Internal</a>"
        "<a href='https://other.example/doc'>External</a>"
        "<a href='mailto:x@example.com'>Mail</a></main>"
        "<footer><a href='/legal'>Legal</a></footer>"
        "</body></html>"
    )
    data = _observation(html).data
    links = {link["url"]: link for link in data["links"]}

    assert links["https://example.com/inside#section"]["kind"] == "internal"
    assert links["https://example.com/inside#section"]["fragment"] == "section"
    assert links["https://example.com/inside#section"]["in_content"] is True
    assert links["https://other.example/doc"]["kind"] == "external"
    assert links["https://example.com/nav-page"]["in_content"] is False
    assert links["https://example.com/legal"]["in_content"] is False
    assert "mailto:x@example.com" not in links


def test_images_record_alt_state_and_link_ancestry():
    html = (
        "<html><body>"
        "<img src='/a.jpg' alt='Described'>"
        "<img src='/b.jpg' alt=''>"
        "<img src='/c.jpg'>"
        "<a href='/target'><img src='/d.jpg' alt=''></a>"
        "</body></html>"
    )
    images = {img["src"]: img for img in _observation(html).data["images"]}

    assert images["https://example.com/a.jpg"]["alt"] == "Described"
    assert images["https://example.com/b.jpg"]["alt"] == ""
    assert images["https://example.com/c.jpg"]["alt"] is None
    assert images["https://example.com/d.jpg"]["in_link"] is True
    assert images["https://example.com/a.jpg"]["in_link"] is False


def test_active_mixed_content_candidates_exclude_plain_hyperlinks():
    html = (
        "<html><head>"
        "<script src='http://cdn.example/app.js'></script>"
        "<link rel='stylesheet' href='http://cdn.example/style.css'>"
        "</head><body>"
        "<img src='http://cdn.example/pic.png'>"
        "<iframe src='http://frames.example/'></iframe>"
        "<a href='http://plain.example/'>plain link</a>"
        "</body></html>"
    )
    candidates = _observation(html).data["active_mixed_candidates"]

    assert "http://cdn.example/app.js" in candidates
    assert "http://cdn.example/style.css" in candidates
    assert "http://cdn.example/pic.png" in candidates
    assert "http://frames.example/" in candidates
    assert "http://plain.example/" not in candidates


def test_jsonld_blocks_and_other_syntax_flags():
    html = (
        "<html><head>"
        '<script type="application/ld+json">{"@type": "Organization"}</script>'
        "</head><body>"
        "<div itemscope itemtype='https://schema.org/Person'></div>"
        "</body></html>"
    )
    data = _observation(html).data

    assert data["jsonld_blocks"] == ['{"@type": "Organization"}']
    assert data["has_microdata"] is True
    assert data["has_rdfa"] is False


def test_visible_dates_extracted_from_time_and_article_meta():
    html = (
        "<html><head>"
        '<meta property="article:published_time" content="2026-01-05T09:00:00Z">'
        '<meta property="article:modified_time" content="2026-02-01T09:00:00Z">'
        "</head><body>"
        "<time datetime='2026-02-01'>February 1, 2026</time>"
        "</body></html>"
    )
    data = _observation(html).data

    assert "2026-02-01" in data["visible_dates"]
    assert data["meta_dates"]["published"] == "2026-01-05T09:00:00Z"
    assert data["meta_dates"]["modified"] == "2026-02-01T09:00:00Z"


def test_enrichment_is_bounded():
    anchors = "".join(f"<a href='/p{i}'>x</a>" for i in range(250))
    images = "".join(f"<img src='/i{i}.png' alt=''>" for i in range(80))
    html = f"<html><body>{anchors}{images}</body></html>"
    data = _observation(html).data

    assert len(data["links"]) == 200
    assert len(data["images"]) == 60


def test_extraction_without_identity_still_works():
    observation = extract_page_observation(
        {
            "url": "https://example.com/",
            "final_url": "https://example.com/",
            "raw_html": "<html><body><a href='/x'>x</a></body></html>",
            "content_type": "text/html",
        },
        "2026-07-15T12:00:00+00:00",
    )
    assert observation.data["links"][0]["kind"] == "unknown"
