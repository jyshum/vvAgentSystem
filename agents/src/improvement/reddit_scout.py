"""
Reddit Scout — Google Proxy Approach (Step 5b)

Finds Reddit threads about a query using Google's site:reddit.com search.
This avoids Reddit API legal/rate-limit issues while still surfacing relevant
community discussions. Results feed into action card generation: threads where
competitors are mentioned but the client is not are GEO opportunities.
"""

import time
from urllib.parse import urlencode

import httpx
from bs4 import BeautifulSoup

GOOGLE_SEARCH_URL = "https://www.google.com/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def parse_google_results(html: str) -> list[dict]:
    """Parse Google search results HTML and return up to 5 Reddit thread dicts.

    Each result: {"title": str, "url": str, "snippet": str (max 300 chars)}
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    results = []

    for block in soup.find_all("div", class_="g"):
        if len(results) >= 5:
            break

        # Find the first <a href> containing "reddit.com"
        link_tag = None
        for a in block.find_all("a", href=True):
            if "reddit.com" in a["href"]:
                link_tag = a
                break

        if link_tag is None:
            continue

        url = link_tag["href"]

        # Extract title from <h3>
        h3 = link_tag.find("h3") or block.find("h3")
        title = h3.get_text(strip=True) if h3 else ""

        # Extract snippet: prefer VwiC3b div, then aCOpRe span, then any 40+ char span
        snippet = ""
        vcb = block.find("div", class_="VwiC3b")
        if vcb:
            snippet = vcb.get_text(strip=True)
        else:
            acr = block.find("span", class_="aCOpRe")
            if acr:
                snippet = acr.get_text(strip=True)
            else:
                for span in block.find_all("span"):
                    text = span.get_text(strip=True)
                    if len(text) >= 40:
                        snippet = text
                        break

        results.append({
            "title": title,
            "url": url,
            "snippet": snippet[:300],
        })

    return results


def detect_brand_mentions(
    threads: list[dict], client_brand: str, competitors: list[str]
) -> dict:
    """Check which brands appear in thread titles and snippets.

    Returns:
        {"client_mentioned": bool, "competitors_mentioned": [str]}
        Competitor names in the returned list preserve original casing from the
        `competitors` argument.
    """
    # Concatenate all text content, lowercased
    combined = " ".join(
        (t.get("title", "") + " " + t.get("snippet", "")).lower()
        for t in threads
    )

    client_mentioned = client_brand.lower() in combined

    competitors_mentioned = [
        comp for comp in competitors if comp.lower() in combined
    ]

    return {
        "client_mentioned": client_mentioned,
        "competitors_mentioned": competitors_mentioned,
    }


def build_scout_result(
    query: str,
    threads: list[dict],
    client_mentioned: bool,
    competitors_mentioned: list[str],
) -> dict:
    """Build the final structured scout result dict."""
    return {
        "query": query,
        "threads_found": len(threads),
        "threads": threads,
        "client_mentioned": client_mentioned,
        "competitors_mentioned": competitors_mentioned,
    }


def scout_reddit_for_query(
    query: str, client_brand: str, competitors: list[str]
) -> dict:
    """Search Google for Reddit threads about `query` and return a scout result.

    On any HTTP or network error, returns an empty scout result so callers
    can continue processing other queries.
    """
    search_query = f'site:reddit.com "{query}"'
    params = {"q": search_query}

    try:
        response = httpx.get(
            GOOGLE_SEARCH_URL,
            params=params,
            headers=HEADERS,
            timeout=15.0,
            follow_redirects=True,
        )
        response.raise_for_status()
        threads = parse_google_results(response.text)
    except Exception:
        return build_scout_result(query, [], False, [])

    mentions = detect_brand_mentions(threads, client_brand, competitors)
    return build_scout_result(
        query=query,
        threads=threads,
        client_mentioned=mentions["client_mentioned"],
        competitors_mentioned=mentions["competitors_mentioned"],
    )


def run_reddit_scout(
    gap_queries: list[dict], client_brand: str, competitors: list[str]
) -> list[dict]:
    """Run the Reddit scout for all gap queries.

    Args:
        gap_queries: List of dicts with at least a "query" key.
        client_brand: The client's brand name to look for.
        competitors: List of competitor brand names to detect.

    Returns:
        List of scout result dicts, one per query.
    """
    results = []
    for i, gap in enumerate(gap_queries):
        query = gap.get("query", "")
        result = scout_reddit_for_query(query, client_brand, competitors)
        results.append(result)
        # Rate limiting: sleep between requests (skip after last item)
        if i < len(gap_queries) - 1:
            time.sleep(2)
    return results
