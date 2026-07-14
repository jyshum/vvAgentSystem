from src.technical_audit.observations import extract_page_observation, normalize_url


def test_extracts_all_head_declarations_without_semantic_judgment():
    page = {
        "url": "https://example.com/service",
        "raw_html": """<html><head>
          <title>Service | Example</title>
          <meta name="description" content="A precise service description.">
          <meta name="robots" content="index,follow">
          <link rel="canonical" href="/service">
        </head><body><h1>Service</h1></body></html>""",
    }
    observation = extract_page_observation(page, "2026-07-14T10:00:00+00:00")

    assert observation.id == "page:https://example.com/service"
    assert observation.data["titles"] == ["Service | Example"]
    assert observation.data["meta_descriptions"] == ["A precise service description."]
    assert observation.data["canonicals"] == ["https://example.com/service"]
    assert observation.data["robots_directives"] == ["index", "follow"]
    assert observation.data["h1_texts"] == ["Service"]
    assert observation.data["is_html"] is True
    assert len(observation.fingerprint) == 64


def test_preserves_duplicate_empty_declarations_for_checks_to_evaluate():
    page = {
        "url": "https://example.com/",
        "raw_html": '<html><head><title></title><title>Second</title><meta name="description" content=""></head></html>',
    }
    observation = extract_page_observation(page, "2026-07-14T10:00:00+00:00")

    assert observation.data["titles"] == ["", "Second"]
    assert observation.data["meta_descriptions"] == [""]


def test_normalize_url_lowercases_origin_and_removes_fragment():
    assert normalize_url("HTTPS://Example.COM#top") == "https://example.com/"
    assert normalize_url("https://Example.com/path?q=One#top") == "https://example.com/path?q=One"


def test_non_html_content_is_marked_without_guessing_from_markup():
    observation = extract_page_observation(
        {
            "url": "https://example.com/report.pdf",
            "raw_html": "<title>Text inside a PDF byte stream</title>",
            "content_type": "application/pdf",
        },
        "2026-07-14T10:00:00+00:00",
    )

    assert observation.data["is_html"] is False
