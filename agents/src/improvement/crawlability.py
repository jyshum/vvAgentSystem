import re
from bs4 import BeautifulSoup
from xml.etree import ElementTree

AI_USER_AGENTS = [
    "GPTBot", "OAI-SearchBot", "ChatGPT-User",
    "ClaudeBot", "Claude-SearchBot", "anthropic-ai",
    "PerplexityBot", "Google-Extended",
]


def _parse_robots_rules(robots_content: str) -> dict[str, list[str]]:
    rules: dict[str, list[str]] = {}
    current_agent = None

    for line in robots_content.splitlines():
        line = line.strip()
        if line.startswith("#") or not line:
            continue

        if line.lower().startswith("user-agent:"):
            current_agent = line.split(":", 1)[1].strip()
            if current_agent not in rules:
                rules[current_agent] = []
        elif line.lower().startswith("disallow:") and current_agent:
            path = line.split(":", 1)[1].strip()
            if path:
                rules[current_agent].append(path)

    return rules


def check_robots_txt(robots_content: str) -> dict:
    if not robots_content.strip():
        return {"status": "pass", "blocked_agents": [], "partial_blocks": [], "detail": "Empty robots.txt — all agents allowed"}

    rules = _parse_robots_rules(robots_content)
    blocked = []
    partial = []

    wildcard_rules = rules.get("*", [])
    wildcard_blocks_root = "/" in wildcard_rules

    for agent in AI_USER_AGENTS:
        agent_rules = rules.get(agent, [])

        if "/" in agent_rules:
            blocked.append(agent)
        elif agent_rules:
            partial.append(f"{agent} blocked from: {', '.join(agent_rules)}")
        elif wildcard_blocks_root and agent not in rules:
            blocked.append(agent)

    if blocked:
        return {
            "status": "fail",
            "blocked_agents": blocked,
            "partial_blocks": partial,
            "detail": f"{len(blocked)} AI bot(s) fully blocked: {', '.join(blocked)}",
        }
    elif partial:
        return {
            "status": "warning",
            "blocked_agents": [],
            "partial_blocks": partial,
            "detail": f"{len(partial)} agent(s) have partial path blocks",
        }
    else:
        return {"status": "pass", "blocked_agents": [], "partial_blocks": [], "detail": "All AI agents allowed"}


def check_js_rendering(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["nav", "footer", "header", "script", "style", "noscript"]):
        tag.decompose()

    body = soup.find("body")
    if not body:
        return {"status": "fail", "word_count": 0, "detail": "No <body> tag found in raw HTML"}

    text = body.get_text(separator=" ", strip=True)
    word_count = len(text.split())

    if word_count < 200:
        return {
            "status": "fail",
            "word_count": word_count,
            "detail": f"Only {word_count} words in raw HTML body — page likely requires JavaScript to render content. GPTBot cannot execute JS.",
        }

    return {"status": "pass", "word_count": word_count, "detail": f"{word_count} words in raw HTML — content accessible without JS"}


def check_cdn_blocks(status_code: int, reason: str) -> dict:
    if status_code in (403, 401, 503):
        return {
            "status": "fail",
            "status_code": status_code,
            "detail": f"HTTP {status_code} ({reason}) when fetching with GPTBot user agent — CDN or hosting is blocking AI bots",
        }
    elif status_code >= 400:
        return {
            "status": "warning",
            "status_code": status_code,
            "detail": f"HTTP {status_code} when fetching with GPTBot user agent",
        }
    return {"status": "pass", "status_code": status_code, "detail": "No CDN blocks detected"}


def check_sitemap(status_code: int, content: str, robots_references_sitemap: bool) -> dict:
    if status_code != 200 or not content.strip():
        return {
            "status": "warning",
            "url_count": 0,
            "detail": "Sitemap not found or not accessible" + (" and not referenced in robots.txt" if not robots_references_sitemap else ""),
        }

    url_count = 0
    try:
        root = ElementTree.fromstring(content)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locs = root.findall(".//sm:loc", ns) or root.findall(".//loc")
        url_count = len(locs)
    except ElementTree.ParseError:
        return {"status": "warning", "url_count": 0, "detail": "Sitemap exists but has XML parse errors"}

    if not robots_references_sitemap:
        return {
            "status": "warning",
            "url_count": url_count,
            "detail": f"Sitemap found with {url_count} URLs but not referenced in robots.txt",
        }

    return {"status": "pass", "url_count": url_count, "detail": f"Sitemap accessible with {url_count} URLs"}


def check_meta_tags(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    issues = []

    for meta in soup.find_all("meta", attrs={"name": re.compile(r"robots", re.I)}):
        content = (meta.get("content") or "").lower()
        if "noindex" in content:
            issues.append("noindex")
        if "nosnippet" in content:
            issues.append("nosnippet")
        if "nofollow" in content:
            issues.append("nofollow")

    if "noindex" in issues:
        return {"status": "fail", "tags_found": issues, "detail": "Found noindex — page will be excluded from AI indexing"}
    elif "nosnippet" in issues:
        return {"status": "warning", "tags_found": issues, "detail": "Found nosnippet — prevents AI from citing page content"}
    elif issues:
        return {"status": "warning", "tags_found": issues, "detail": f"Found restrictive meta tags: {', '.join(issues)}"}

    return {"status": "pass", "tags_found": [], "detail": "No blocking meta tags found"}


def check_llms_txt(status_code: int, content: str) -> dict:
    if status_code == 200 and content.strip():
        return {"status": "pass", "detail": "llms.txt found (note: no major AI company reads this yet)"}
    return {"status": "info", "detail": "No llms.txt found — consider adding as a forward-looking step"}


def _run_gate_from_data(
    domain: str,
    robots_content: str,
    homepage_html: str,
    homepage_status: int,
    sitemap_status: int,
    sitemap_content: str,
    llms_txt_status: int,
    llms_txt_content: str,
    sample_pages_html: list[str] | None = None,
) -> dict:
    robots_references_sitemap = "sitemap:" in robots_content.lower()

    report = {
        "robots_txt": check_robots_txt(robots_content),
        "js_rendering": check_js_rendering(homepage_html, f"https://{domain}"),
        "cdn_blocks": check_cdn_blocks(homepage_status, "OK"),
        "sitemap": check_sitemap(sitemap_status, sitemap_content, robots_references_sitemap),
        "meta_tags": check_meta_tags(homepage_html),
        "llms_txt": check_llms_txt(llms_txt_status, llms_txt_content),
    }

    for page_html in (sample_pages_html or []):
        page_meta = check_meta_tags(page_html)
        if page_meta["status"] != "pass":
            report["meta_tags"] = page_meta
            break

    critical_checks = ["robots_txt", "js_rendering", "cdn_blocks"]
    report["has_critical_blocker"] = any(
        report[check]["status"] == "fail" for check in critical_checks
    )

    return report


def run_crawlability_gate(domain: str) -> dict:
    import httpx

    base = f"https://{domain}"
    report = {}

    robots_content = ""
    try:
        resp = httpx.get(f"{base}/robots.txt", timeout=10, follow_redirects=True)
        if resp.status_code == 200:
            robots_content = resp.text
    except Exception as e:
        print(f"  Crawlability: robots.txt fetch failed: {e}")
    report["robots_txt"] = check_robots_txt(robots_content)

    robots_references_sitemap = "sitemap:" in robots_content.lower()

    homepage_html = ""
    homepage_status = 0
    try:
        resp = httpx.get(base, timeout=15, follow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0 (compatible; VV-Audit/1.0)"})
        homepage_html = resp.text
        homepage_status = resp.status_code
    except Exception as e:
        print(f"  Crawlability: homepage fetch failed: {e}")
    report["js_rendering"] = check_js_rendering(homepage_html, base)

    cdn_status = 0
    cdn_reason = ""
    try:
        resp = httpx.get(base, timeout=10, follow_redirects=True,
                         headers={"User-Agent": "GPTBot/1.0 (+https://openai.com/gptbot)"})
        cdn_status = resp.status_code
        cdn_reason = resp.reason_phrase or ""
    except Exception as e:
        cdn_status = 0
        cdn_reason = str(e)
    report["cdn_blocks"] = check_cdn_blocks(cdn_status, cdn_reason)

    sitemap_status = 0
    sitemap_content = ""
    try:
        resp = httpx.get(f"{base}/sitemap.xml", timeout=10, follow_redirects=True)
        sitemap_status = resp.status_code
        sitemap_content = resp.text if resp.status_code == 200 else ""
    except Exception as e:
        print(f"  Crawlability: sitemap fetch failed: {e}")
    report["sitemap"] = check_sitemap(sitemap_status, sitemap_content, robots_references_sitemap)

    report["meta_tags"] = check_meta_tags(homepage_html)

    llms_status = 0
    llms_content = ""
    try:
        resp = httpx.get(f"{base}/llms.txt", timeout=10, follow_redirects=True)
        llms_status = resp.status_code
        llms_content = resp.text if resp.status_code == 200 else ""
    except Exception:
        pass
    report["llms_txt"] = check_llms_txt(llms_status, llms_content)

    critical_checks = ["robots_txt", "js_rendering", "cdn_blocks"]
    report["has_critical_blocker"] = any(
        report[check]["status"] == "fail" for check in critical_checks
    )

    return report


run_crawlability_gate.__wrapped__ = _run_gate_from_data
