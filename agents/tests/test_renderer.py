import pytest
from src.renderer import render_page, RenderResult


def test_render_result_has_required_fields():
    result = RenderResult(
        url="https://example.com",
        html="<html><body>Hello</body></html>",
        screenshot=b"fake-png-bytes",
        success=True,
        error=None,
    )
    assert result.url == "https://example.com"
    assert result.html.startswith("<html>")
    assert result.screenshot == b"fake-png-bytes"
    assert result.success is True


def test_render_page_returns_render_result():
    result = render_page("https://localhost:99999/nonexistent")
    assert isinstance(result, RenderResult)
    assert result.url == "https://localhost:99999/nonexistent"
