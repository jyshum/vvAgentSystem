from unittest.mock import patch
from src.classifier import classify_page_with_vision, VALID_PAGE_TYPES


def test_valid_page_types_exist():
    assert "homepage" in VALID_PAGE_TYPES
    assert "utility/form" in VALID_PAGE_TYPES
    assert "service" in VALID_PAGE_TYPES


def test_classify_returns_valid_type():
    fake_response = "utility/form — This page contains two intake forms for donating and requesting flowers."

    with patch("src.classifier._call_haiku_vision", return_value=fake_response):
        result = classify_page_with_vision(b"fake-screenshot-bytes", "https://repeatfloral.org/request")

    assert result in VALID_PAGE_TYPES


def test_classify_falls_back_on_unparseable_response():
    with patch("src.classifier._call_haiku_vision", return_value="I don't know what this page is"):
        result = classify_page_with_vision(b"fake-screenshot-bytes", "https://example.com/something")

    assert result == "service"
