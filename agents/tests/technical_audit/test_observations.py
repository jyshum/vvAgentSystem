import json

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


def test_canonical_fragment_is_preserved_for_the_check_to_reject():
    observation = extract_page_observation(
        {
            "url": "https://example.com/page",
            "raw_html": '<html><head><link rel="canonical" href="/page#section"></head></html>',
        },
        "2026-07-14T10:00:00+00:00",
    )

    assert observation.data["canonicals"] == ["https://example.com/page#section"]


def test_extracted_head_fields_have_count_and_length_bounds():
    repeated = "".join(
        f"<title>{'T' * 900}</title><meta name='description' content='{'D' * 3000}'>"
        f"<link rel='canonical' href='/{'c' * 3000}'>"
        for _ in range(20)
    )
    headings = "".join(f"<h1>{'H' * 3000}</h1>" for _ in range(20))
    html = f"<html><head>{repeated}</head><body>{headings}</body></html>"
    observation = extract_page_observation(
        {"url": "https://example.com/", "raw_html": html},
        "2026-07-14T10:00:00+00:00",
    )

    assert len(observation.data["titles"]) == 10
    assert max(map(len, observation.data["titles"])) == 500
    assert len(observation.data["meta_descriptions"]) == 10
    assert max(map(len, observation.data["meta_descriptions"])) == 1_000
    assert len(observation.data["canonicals"]) == 10
    assert max(map(len, observation.data["canonicals"])) <= 2_048
    assert len(observation.data["h1_texts"]) == 10
    assert max(map(len, observation.data["h1_texts"])) == 1_000


def test_observation_bounds_are_measured_in_bytes_for_multibyte_text():
    emoji = "🧪"
    repeated = "".join(
        f"<title>{emoji * 900}</title>"
        f"<meta name='description' content='{emoji * 3000}'>"
        f"<link rel='canonical' href='/{emoji * 3000}'>"
        for _ in range(20)
    )
    headings = "".join(f"<h1>{emoji * 3000}</h1>" for _ in range(20))
    observation = extract_page_observation(
        {
            "url": f"https://example.com/{emoji * 3000}",
            "raw_html": f"<html><head>{repeated}</head><body>{headings}</body></html>",
            "fetch_error": emoji * 3000,
        },
        "2026-07-14T10:00:00+00:00",
    )

    encoded = json.dumps(observation.data, ensure_ascii=False).encode("utf-8")
    assert len(encoded) <= 60_000
