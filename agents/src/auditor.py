import time
import httpx
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

from src.parsers import parse_html
from src.scorers import (
    score_source_citations,
    score_schema_markup,
    score_freshness,
    score_with_haiku_batch,
)
from src.renderer import render_page
from src.classifier import classify_page_with_vision

PILLAR_NAMES = [
    "Content Structure",
    "Fact Density",
    "Source Citations",
    "Authority Signals",
    "Schema Markup",
    "Freshness",
]


UTILITY_PATTERNS = ["/contact", "/privacy", "/terms", "/thank", "/404", "/sitemap",
                    "/request", "/donate", "/apply", "/signup", "/register", "/submit"]
ARTICLE_PATTERNS = ["/blog/", "/news/", "/post/", "/article/", "/guide/", "/tips/"]
FAQ_PATTERNS = ["/faq", "/help/", "/support/", "/questions/"]
ABOUT_PATTERNS = ["/about", "/team", "/story", "/mission"]
SERVICE_PATTERNS = ["/service", "/product", "/solution", "/feature", "/pricing", "/how-it-works"]

PILLAR_APPLICABILITY = {
    "homepage": ["Content Structure", "Authority Signals", "Schema Markup"],
    "about":    ["Content Structure", "Authority Signals", "Schema Markup"],
    "service":  ["Content Structure", "Fact Density", "Source Citations", "Authority Signals", "Schema Markup"],
    "article":  ["Content Structure", "Fact Density", "Source Citations", "Authority Signals", "Schema Markup", "Freshness"],
    "faq":      ["Content Structure", "Source Citations", "Schema Markup"],
    "utility":  ["Schema Markup"],
    "utility/form": ["Schema Markup"],
    "landing":  ["Content Structure", "Authority Signals", "Schema Markup"],
    "gallery":  ["Schema Markup"],
}


def classify_page_type(url: str, title: str, raw_text: str) -> str:
    path = url.lower().split("?")[0]

    if any(p in path for p in UTILITY_PATTERNS):
        return "utility"
    if any(p in path for p in ARTICLE_PATTERNS):
        return "article"
    if any(p in path for p in FAQ_PATTERNS):
        return "faq"
    if any(p in path for p in ABOUT_PATTERNS):
        return "about"
    if any(p in path for p in SERVICE_PATTERNS):
        return "service"

    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.path.strip("/") == "":
        return "homepage"

    return "service"


def get_applicable_pillars(page_type: str) -> list[str]:
    return PILLAR_APPLICABILITY.get(page_type, PILLAR_APPLICABILITY["service"])


def discover_pages(domain: str, max_pages: int = 20) -> list[str]:
    base = f"https://{domain}"

    for sitemap_url in [f"{base}/sitemap.xml", f"{base}/sitemap_index.xml"]:
        try:
            resp = httpx.get(sitemap_url, timeout=10, follow_redirects=True)
            if resp.status_code == 200 and "<loc>" in resp.text:
                root = ElementTree.fromstring(resp.text)
                ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
                locs = root.findall(".//sm:loc", ns) or root.findall(".//loc")
                urls = [loc.text.strip() for loc in locs if loc.text and domain in loc.text]
                if urls:
                    print(f"  Sitemap: {len(urls)} URLs found")
                    return urls[:max_pages]
        except Exception:
            continue

    print(f"  No sitemap — crawling from {base}")
    try:
        resp = httpx.get(base, timeout=10, follow_redirects=True)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        seen = {base, base + "/"}
        urls = []
        for a in soup.find_all("a", href=True):
            full = urljoin(base, a["href"])
            parsed = urlparse(full)
            if parsed.netloc == domain and parsed.scheme in ("http", "https"):
                clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if clean not in seen:
                    seen.add(clean)
                    urls.append(clean)
        return urls[:max_pages] if urls else [base]
    except Exception as e:
        print(f"  Homepage crawl failed: {e}")
        return [base]


def score_page(url: str, client_domain: str) -> dict | None:
    path = url.lower().split("?")[0]
    is_utility = any(p in path for p in UTILITY_PATTERNS)

    if is_utility:
        try:
            resp = httpx.get(url, timeout=15, follow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0 (compatible; VV-Audit/1.0)"})
        except httpx.RequestError as e:
            print(f"    Fetch error: {e}")
            return None
        if resp.status_code != 200:
            print(f"    HTTP {resp.status_code} — skipping")
            return None
        html = resp.text
        page_type = "utility"
        last_modified = resp.headers.get("last-modified")
    else:
        rendered = render_page(url)
        if not rendered.success and not rendered.html:
            print(f"    Render failed: {rendered.error}")
            return None
        html = rendered.html
        last_modified = None
        if rendered.screenshot:
            page_type = classify_page_with_vision(rendered.screenshot, url)
        else:
            page_type = classify_page_type(url, "", "")

    page = parse_html(url, html, client_domain, 200,
                      last_modified_header=last_modified)

    rules_scores = {
        "Source Citations": score_source_citations(page, client_domain),
        "Schema Markup": score_schema_markup(page),
        "Freshness": score_freshness(page),
    }

    haiku_scores = score_with_haiku_batch(page.raw_text, page.paragraphs, page.headings,
                                          page_type=page_type, url=url)

    pillars = {
        "Content Structure": haiku_scores.get("content_structure", {"score": 0, "strengths": [], "issues": [], "recommendations": []}),
        "Fact Density": haiku_scores.get("fact_density", {"score": 0, "strengths": [], "issues": [], "recommendations": []}),
        "Source Citations": rules_scores["Source Citations"],
        "Authority Signals": haiku_scores.get("authority_signals", {"score": 0, "strengths": [], "issues": [], "recommendations": []}),
        "Schema Markup": rules_scores["Schema Markup"],
        "Freshness": rules_scores["Freshness"],
    }

    applicable = get_applicable_pillars(page_type)
    filtered_pillars = {name: data for name, data in pillars.items() if name in applicable}
    total_score = sum(p["score"] for p in filtered_pillars.values()) // len(filtered_pillars)

    return {
        "url": url,
        "title": page.title,
        "page_type": page_type,
        "word_count": page.word_count,
        "total_score": total_score,
        "pillars": filtered_pillars,
        "paragraphs": page.paragraphs[:10],
    }


def compute_site_summary(pages: list[dict]) -> dict:
    if not pages:
        return {}

    pillar_averages = {}
    for name in PILLAR_NAMES:
        scores = [p["pillars"][name]["score"] for p in pages if name in p["pillars"]]
        pillar_averages[name] = round(sum(scores) / len(scores)) if scores else 0

    total_scores = [p["total_score"] for p in pages]
    site_score = round(sum(total_scores) / len(total_scores))
    weakest_pillar = min(pillar_averages, key=pillar_averages.get)
    weakest_pages = sorted(pages, key=lambda p: p["total_score"])[:3]

    return {
        "pages_audited": len(pages),
        "site_score": site_score,
        "pillar_averages": pillar_averages,
        "weakest_pillar": weakest_pillar,
        "weakest_pages": [{"url": p["url"], "score": p["total_score"]} for p in weakest_pages],
    }


def run_audit(config: dict) -> tuple[list[dict], dict]:
    domain = config["website_domain"]
    max_pages = config.get("audit_max_pages", 20)

    print(f"\n  Discovering pages on {domain}...")
    urls = discover_pages(domain, max_pages)

    page_results = []
    for i, url in enumerate(urls, 1):
        print(f"  [{i}/{len(urls)}] {url}")
        result = score_page(url, domain)
        if result:
            page_results.append(result)
            print(f"    → {result['total_score']}/100")
        time.sleep(0.5)

    summary = compute_site_summary(page_results)
    return page_results, summary
