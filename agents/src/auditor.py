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

PILLAR_NAMES = [
    "Content Structure",
    "Fact Density",
    "Source Citations",
    "Authority Signals",
    "Schema Markup",
    "Freshness",
]


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
    try:
        resp = httpx.get(url, timeout=15, follow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0 (compatible; VV-Audit/1.0)"})
    except httpx.RequestError as e:
        print(f"    Fetch error: {e}")
        return None

    if resp.status_code != 200:
        print(f"    HTTP {resp.status_code} — skipping")
        return None

    page = parse_html(url, resp.text, client_domain, resp.status_code,
                      last_modified_header=resp.headers.get("last-modified"))

    rules_scores = {
        "Source Citations": score_source_citations(page, client_domain),
        "Schema Markup": score_schema_markup(page),
        "Freshness": score_freshness(page),
    }

    haiku_scores = score_with_haiku_batch(page.raw_text, page.paragraphs, page.headings)

    pillars = {
        "Content Structure": haiku_scores.get("content_structure", {"score": 0, "issues": [], "recommendations": []}),
        "Fact Density": haiku_scores.get("fact_density", {"score": 0, "issues": [], "recommendations": []}),
        "Source Citations": rules_scores["Source Citations"],
        "Authority Signals": haiku_scores.get("authority_signals", {"score": 0, "issues": [], "recommendations": []}),
        "Schema Markup": rules_scores["Schema Markup"],
        "Freshness": rules_scores["Freshness"],
    }

    total_score = sum(p["score"] for p in pillars.values()) // len(pillars)

    return {
        "url": url,
        "title": page.title,
        "word_count": page.word_count,
        "total_score": total_score,
        "pillars": pillars,
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
