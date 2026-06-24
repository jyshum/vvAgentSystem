import time
from urllib.parse import urlencode
import httpx


REDDIT_SEARCH_BASE = "https://www.reddit.com/search.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; VV-GEO-Scout/1.0; +https://victoryvelocity.co)"
}


def build_search_url(query: str, sort: str = "top", time_filter: str = "month", limit: int = 10) -> str:
    params = {"q": query, "sort": sort, "t": time_filter, "limit": limit}
    return f"{REDDIT_SEARCH_BASE}?{urlencode(params)}"


def parse_reddit_results(data: dict) -> list[dict]:
    posts = []
    children = data.get("data", {}).get("children", [])
    for child in children:
        d = child.get("data", {})
        posts.append({
            "title": d.get("title", ""),
            "url": f"https://www.reddit.com{d.get('permalink', '')}",
            "subreddit": d.get("subreddit", ""),
            "score": d.get("score", 0),
            "num_comments": d.get("num_comments", 0),
            "selftext": d.get("selftext", "")[:500],
        })
    return posts


def score_relevance(post: dict, brand_name: str, keywords: list[str]) -> float:
    text = (post.get("title", "") + " " + post.get("selftext", "")).lower()
    brand_lower = brand_name.lower()

    score = 0.0

    if brand_lower in text:
        score += 0.4

    keyword_hits = sum(1 for kw in keywords if kw.lower() in text)
    score += min(keyword_hits * 0.15, 0.45)

    upvotes = post.get("score", 0)
    if upvotes > 100:
        score += 0.15
    elif upvotes > 20:
        score += 0.08

    return min(score, 1.0)


def search_reddit(query: str) -> list[dict]:
    url = build_search_url(query)
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=10, follow_redirects=True)
        resp.raise_for_status()
        return parse_reddit_results(resp.json())
    except Exception as e:
        print(f"    Reddit fetch failed for '{query}': {e}")
        return []


def run_scout(config: dict) -> list[dict]:
    brand_name = config.get("brand_name", config.get("client_name", ""))
    website_domain = config.get("website_domain", "")
    keywords = config.get("target_keywords", [])

    if not keywords:
        target_queries = config.get("target_queries", [])
        keywords = list({word for q in target_queries for word in q.lower().split() if len(word) > 4})[:10]

    queries = [
        brand_name,
        f"{brand_name} review",
        f"{brand_name} alternative",
    ]

    for kw in keywords[:3]:
        queries.append(kw)

    all_posts = []
    seen_urls = set()

    for query in queries:
        print(f"  Searching: {query}")
        posts = search_reddit(query)
        for post in posts:
            if post["url"] not in seen_urls:
                seen_urls.add(post["url"])
                post["relevance_score"] = score_relevance(post, brand_name, keywords)
                all_posts.append(post)
        time.sleep(1.5)

    return sorted(all_posts, key=lambda p: p["relevance_score"], reverse=True)
