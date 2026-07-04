import json
import httpx
from bs4 import BeautifulSoup
from xml.etree import ElementTree
from urllib.parse import urljoin, urlparse


def discover_pages_from_sitemap(xml_content: str, domain: str, max_pages: int = 20) -> list[str]:
    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError:
        return []

    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = root.findall(".//sm:loc", ns) or root.findall(".//loc")
    urls = [loc.text.strip() for loc in locs if loc.text and domain in loc.text]
    return urls[:max_pages]


def discover_pages(domain: str, max_pages: int = 20) -> list[str]:
    base = f"https://{domain}"

    for sitemap_url in [f"{base}/sitemap.xml", f"{base}/sitemap_index.xml"]:
        try:
            resp = httpx.get(sitemap_url, timeout=10, follow_redirects=True)
            if resp.status_code == 200 and "<loc>" in resp.text:
                urls = discover_pages_from_sitemap(resp.text, domain, max_pages)
                if urls:
                    print(f"  Inventory: {len(urls)} URLs from sitemap")
                    return urls
        except Exception:
            continue

    print(f"  Inventory: No sitemap — crawling links from {base}")
    try:
        resp = httpx.get(base, timeout=10, follow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0 (compatible; VV-Audit/1.0)"})
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
        print(f"  Inventory: Homepage crawl failed: {e}")
        return [base]


def extract_page_data(url: str, html: str, client_domain: str,
                      last_modified_header: str | None = None) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    h1_tag = soup.find("h1")
    h1 = h1_tag.get_text(strip=True) if h1_tag else ""

    schema_types = []
    has_faq_schema = False
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            t = data.get("@type")
            if isinstance(t, list):
                schema_types.extend(t)
                if "FAQPage" in t:
                    has_faq_schema = True
            elif t:
                schema_types.append(t)
                if t == "FAQPage":
                    has_faq_schema = True
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass

    last_modified = last_modified_header
    if not last_modified:
        for meta_name in ["article:modified_time", "article:published_time", "date", "og:updated_time"]:
            tag = soup.find("meta", property=meta_name) or soup.find("meta", attrs={"name": meta_name})
            if tag and tag.get("content"):
                last_modified = tag["content"]
                break
        if not last_modified:
            time_tag = soup.find("time", datetime=True)
            if time_tag:
                last_modified = time_tag["datetime"]

    for tag in soup.find_all(["nav", "footer", "header", "aside", "script", "style"]):
        tag.decompose()

    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 20]
    first_paragraph = paragraphs[0][:500] if paragraphs else ""

    body = soup.find("body")
    raw_text = body.get_text(separator=" ", strip=True) if body else ""
    word_count = len(raw_text.split())

    outbound_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http") and client_domain not in href:
            outbound_links.append(href)

    has_comparison_table = False
    for table in soup.find_all("table"):
        headers = table.find_all("th")
        if len(headers) >= 3:
            has_comparison_table = True
            break

    return {
        "url": url,
        "title": title,
        "h1": h1,
        "first_paragraph": first_paragraph,
        "schema_types": schema_types,
        "word_count": word_count,
        "last_modified": last_modified,
        "outbound_link_count": len(outbound_links),
        "has_faq_schema": has_faq_schema,
        "has_comparison_table": has_comparison_table,
        "raw_html": html,
    }


def build_inventory(domain: str, max_pages: int = 20) -> list[dict]:
    urls = discover_pages(domain, max_pages)
    inventory = []

    for i, url in enumerate(urls, 1):
        print(f"  Inventory [{i}/{len(urls)}] {url}")
        try:
            resp = httpx.get(url, timeout=15, follow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0 (compatible; VV-Audit/1.0)"})
            if resp.status_code != 200:
                print(f"    HTTP {resp.status_code} — skipping")
                continue
            data = extract_page_data(url, resp.text, domain,
                                     last_modified_header=resp.headers.get("last-modified"))
            inventory.append(data)
        except Exception as e:
            print(f"    Fetch error: {e}")

    return inventory
