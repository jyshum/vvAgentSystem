import httpx
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=2)


@dataclass
class RenderResult:
    url: str
    html: str
    screenshot: bytes | None
    success: bool
    error: str | None


def _playwright_render(url: str, timeout: int) -> RenderResult:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (compatible; VV-Audit/1.0)",
            viewport={"width": 1280, "height": 720},
        )
        page.goto(url, wait_until="networkidle", timeout=timeout)
        page.wait_for_timeout(1000)

        screenshot = page.screenshot(full_page=True)
        html = page.content()

        browser.close()

        return RenderResult(
            url=url,
            html=html,
            screenshot=screenshot,
            success=True,
            error=None,
        )


def render_page(url: str, timeout: int = 30000) -> RenderResult:
    try:
        future = _executor.submit(_playwright_render, url, timeout)
        return future.result(timeout=timeout // 1000 + 10)
    except Exception as e:
        print(f"    Playwright failed for {url}: {e} — falling back to httpx")
        return _fallback_fetch(url)


def _fallback_fetch(url: str) -> RenderResult:
    try:
        resp = httpx.get(url, timeout=15, follow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0 (compatible; VV-Audit/1.0)"})
        return RenderResult(
            url=url,
            html=resp.text,
            screenshot=None,
            success=True,
            error="Playwright failed — used httpx fallback (no screenshot, raw HTML)",
        )
    except Exception as e:
        return RenderResult(
            url=url,
            html="",
            screenshot=None,
            success=False,
            error=str(e),
        )
