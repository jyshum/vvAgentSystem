# AI Visibility Improvement Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current `run_audit → run_recommender` pipeline nodes with a unified, gap-driven improvement pipeline (Steps 1-6), add LangSmith tracing, and expose a schedule visibility endpoint.

**Architecture:** A new `agents/src/improvement/` package contains one module per pipeline step. A single LangGraph node `run_improvement_pipeline` orchestrates them sequentially, sharing in-memory state (raw HTML, embeddings) that shouldn't be serialized to graph state. The existing tracker, competitive gaps, stability, and query management systems are unchanged. New Supabase tables store improvement run data. LangSmith provides step-level observability via environment variables only.

**Tech Stack:** Python 3.11+, FastAPI, LangGraph, Supabase PostgreSQL, sentence-transformers (SBERT all-MiniLM-L6-v2), Claude Sonnet API, httpx, BeautifulSoup4

---

## File Structure

### New files

| File | Responsibility |
|------|---------------|
| `agents/src/improvement/__init__.py` | Package init, exports |
| `agents/src/improvement/crawlability.py` | Step 1: robots.txt parsing, JS rendering check, CDN block check, sitemap check, meta tag check, llms.txt check |
| `agents/src/improvement/inventory.py` | Step 2: site crawl, page data extraction (title, H1, first paragraph, schema types, word count, outbound links, etc.) |
| `agents/src/improvement/matcher.py` | Step 3: SBERT embedding loading, page+query embedding, cosine similarity, threshold classification |
| `agents/src/improvement/scorer.py` | Step 4: 9 deterministic structural checks + 1 Sonnet quality call per page |
| `agents/src/improvement/gap_check.py` | Step 5: competitive gap lookup from tracker data, max gap per query |
| `agents/src/improvement/reddit_scout.py` | Step 5b: Google search proxy for Reddit threads, brand/competitor mention detection |
| `agents/src/improvement/card_generator.py` | Step 6: rule-based action classification, Sonnet specifics generation, content brief generation |
| `agents/src/improvement/validators.py` | JSON-LD validation, HTML tag check, outbound link check |
| `agents/src/improvement/pipeline.py` | Orchestrator: runs Steps 1-6 sequentially, persists to Supabase, returns state dict |
| `agents/src/implementors/webflow_impl.py` | Webflow staging implementation via CMS API |
| `supabase/migrations/008_improvement_pipeline.sql` | New tables, altered columns, indexes, RLS policies |
| `agents/tests/test_crawlability.py` | Tests for Step 1 |
| `agents/tests/test_inventory.py` | Tests for Step 2 |
| `agents/tests/test_matcher.py` | Tests for Step 3 |
| `agents/tests/test_scorer.py` | Tests for Step 4 |
| `agents/tests/test_gap_check.py` | Tests for Step 5 |
| `agents/tests/test_reddit_scout_v2.py` | Tests for Step 5b (named v2 to avoid collision with existing `test_reddit_scout.py`) |
| `agents/tests/test_card_generator.py` | Tests for Step 6 |
| `agents/tests/test_validators.py` | Tests for validators |
| `agents/tests/test_improvement_pipeline.py` | Tests for the orchestrator |

### Modified files

| File | What changes |
|------|-------------|
| `agents/src/graph/state.py` | Add new fields (`improvement_run_id`, `crawlability_report`, `page_inventory`, `query_matches`, `citation_scores`, `competitive_gap_data`, `reddit_scout_data`), remove old fields (`audit_pages`, `audit_summary`, `audit_run_id`) |
| `agents/src/graph/pipeline.py` | Remove `run_audit`/`run_recommender` nodes, add `run_improvement_pipeline` node, update `route_after_config` and `route_after_gsc` routing |
| `agents/src/graph/nodes.py` | Add `run_improvement_pipeline_node`, remove `run_audit_node`/`run_recommender_node` |
| `agents/server.py` | Add `/api/schedules` GET endpoint |
| `agents/src/implementors/router.py` | Add `webflow` routing to `route_card()` |
| `agents/requirements.txt` | Add `sentence-transformers` |
| `agents/pyproject.toml` | Add `sentence-transformers` to dependencies |
| `agents/tests/test_pipeline.py` | Update node name assertions |
| `agents/tests/test_server.py` | Add test for `/api/schedules` endpoint |

---

## Task 1: Database Migration

**Files:**
- Create: `supabase/migrations/008_improvement_pipeline.sql`

- [ ] **Step 1: Write the migration file**

```sql
-- 008_improvement_pipeline.sql
-- New tables for the improvement pipeline

-- ══════════════════════════════════════════════
-- improvement_runs: tracks each improvement pipeline execution
-- ══════════════════════════════════════════════
create table public.improvement_runs (
    id uuid primary key default gen_random_uuid(),
    client_id uuid not null references public.clients(id) on delete cascade,
    ran_at timestamptz default now(),
    crawlability_report jsonb default '{}'::jsonb,
    pages_inventoried int default 0,
    queries_matched int default 0,
    content_gaps_found int default 0,
    competitive_gaps_found int default 0,
    cards_generated int default 0,
    status text default 'running'
        check (status in ('running', 'completed', 'error')),
    error_message text,
    completed_at timestamptz
);

-- ══════════════════════════════════════════════
-- page_inventory: site crawl results per run
-- ══════════════════════════════════════════════
create table public.page_inventory (
    id uuid primary key default gen_random_uuid(),
    run_id uuid not null references public.improvement_runs(id) on delete cascade,
    url text not null,
    title text default '',
    h1 text default '',
    first_paragraph text default '',
    schema_types text[] default '{}',
    word_count int default 0,
    last_modified timestamptz,
    outbound_link_count int default 0,
    has_faq_schema boolean default false,
    has_comparison_table boolean default false
);

-- ══════════════════════════════════════════════
-- query_page_matches: SBERT matching results
-- ══════════════════════════════════════════════
create table public.query_page_matches (
    id uuid primary key default gen_random_uuid(),
    run_id uuid not null references public.improvement_runs(id) on delete cascade,
    query_id uuid not null references public.queries(id) on delete cascade,
    query_text text not null,
    match_type text not null check (match_type in ('matched', 'weak', 'content_gap')),
    matched_page_url text,
    similarity_score float default 0,
    bucket text
);

-- ══════════════════════════════════════════════
-- page_citation_scores: citation-readiness scoring
-- ══════════════════════════════════════════════
create table public.page_citation_scores (
    id uuid primary key default gen_random_uuid(),
    run_id uuid not null references public.improvement_runs(id) on delete cascade,
    page_url text not null,
    structural_score int default 0,
    check_results jsonb default '{}'::jsonb,
    sonnet_quality jsonb default '{}'::jsonb,
    schema_status text default 'missing'
        check (schema_status in ('missing', 'broken', 'valid_incomplete', 'valid_complete')),
    schema_errors text[] default '{}'
);

-- ══════════════════════════════════════════════
-- Extend action_cards for two-track system
-- ══════════════════════════════════════════════
alter table public.action_cards
    add column if not exists client_id uuid references public.clients(id),
    add column if not exists query_id uuid references public.queries(id),
    add column if not exists action_type text default 'general',
    add column if not exists track text default 'automated'
        check (track in ('automated', 'manual')),
    add column if not exists priority int default 3,
    add column if not exists competitive_gap float,
    add column if not exists structural_score int,
    add column if not exists validation_passed boolean default true,
    add column if not exists brief jsonb,
    add column if not exists preview_url text,
    add column if not exists reddit_data jsonb;

-- Update cms_action constraint to include webflow_staging
alter table public.action_cards drop constraint if exists action_cards_cms_action_check;
alter table public.action_cards add constraint action_cards_cms_action_check
    check (cms_action in ('none', 'github_pr', 'wordpress_api', 'webflow_staging', 'copy_paste'));

-- ══════════════════════════════════════════════
-- Indexes
-- ══════════════════════════════════════════════
create index idx_improvement_runs_client on public.improvement_runs(client_id);
create index idx_page_inventory_run on public.page_inventory(run_id);
create index idx_query_page_matches_run on public.query_page_matches(run_id);
create index idx_query_page_matches_query on public.query_page_matches(query_id);
create index idx_page_citation_scores_run on public.page_citation_scores(run_id);
create index idx_action_cards_client on public.action_cards(client_id);
create index idx_action_cards_query on public.action_cards(query_id);
create index idx_action_cards_track on public.action_cards(track);

-- ══════════════════════════════════════════════
-- RLS policies (admin-only, same pattern as existing tables)
-- ══════════════════════════════════════════════
alter table public.improvement_runs enable row level security;
alter table public.page_inventory enable row level security;
alter table public.query_page_matches enable row level security;
alter table public.page_citation_scores enable row level security;

create policy "Admins can manage improvement_runs"
    on public.improvement_runs for all
    using (public.is_admin()) with check (public.is_admin());

create policy "Admins can manage page_inventory"
    on public.page_inventory for all
    using (public.is_admin()) with check (public.is_admin());

create policy "Admins can manage query_page_matches"
    on public.query_page_matches for all
    using (public.is_admin()) with check (public.is_admin());

create policy "Admins can manage page_citation_scores"
    on public.page_citation_scores for all
    using (public.is_admin()) with check (public.is_admin());
```

- [ ] **Step 2: Verify migration syntax**

Run: `cat supabase/migrations/008_improvement_pipeline.sql | head -5`
Expected: First lines of the file visible, no syntax errors from creation.

- [ ] **Step 3: Commit**

```bash
git add supabase/migrations/008_improvement_pipeline.sql
git commit -m "feat: add improvement pipeline database migration"
```

---

## Task 2: Step 1 — Crawlability Gate

**Files:**
- Create: `agents/src/improvement/__init__.py`
- Create: `agents/src/improvement/crawlability.py`
- Create: `agents/tests/test_crawlability.py`

- [ ] **Step 1: Create package init**

```python
# agents/src/improvement/__init__.py
```

- [ ] **Step 2: Write the failing tests**

```python
# agents/tests/test_crawlability.py
from src.improvement.crawlability import (
    check_robots_txt,
    check_js_rendering,
    check_cdn_blocks,
    check_sitemap,
    check_meta_tags,
    check_llms_txt,
    run_crawlability_gate,
)

AI_USER_AGENTS = [
    "GPTBot", "OAI-SearchBot", "ChatGPT-User",
    "ClaudeBot", "Claude-SearchBot", "anthropic-ai",
    "PerplexityBot", "Google-Extended",
]


class TestCheckRobotsTxt:
    def test_all_allowed(self):
        robots_content = "User-agent: *\nAllow: /\n"
        result = check_robots_txt(robots_content)
        assert result["status"] == "pass"
        assert result["blocked_agents"] == []

    def test_gptbot_blocked(self):
        robots_content = "User-agent: GPTBot\nDisallow: /\n"
        result = check_robots_txt(robots_content)
        assert result["status"] == "fail"
        assert "GPTBot" in result["blocked_agents"]

    def test_wildcard_disallow_all(self):
        robots_content = "User-agent: *\nDisallow: /\n"
        result = check_robots_txt(robots_content)
        assert result["status"] == "fail"
        assert len(result["blocked_agents"]) == len(AI_USER_AGENTS)

    def test_partial_disallow(self):
        robots_content = (
            "User-agent: GPTBot\nDisallow: /\n\n"
            "User-agent: ClaudeBot\nDisallow: /\n\n"
            "User-agent: *\nAllow: /\n"
        )
        result = check_robots_txt(robots_content)
        assert result["status"] == "fail"
        assert "GPTBot" in result["blocked_agents"]
        assert "ClaudeBot" in result["blocked_agents"]
        assert "PerplexityBot" not in result["blocked_agents"]

    def test_empty_robots(self):
        result = check_robots_txt("")
        assert result["status"] == "pass"

    def test_disallow_specific_path_not_root(self):
        robots_content = "User-agent: GPTBot\nDisallow: /private/\n"
        result = check_robots_txt(robots_content)
        assert result["status"] == "warning"
        assert "GPTBot" in result["partial_blocks"][0]


class TestCheckJsRendering:
    def test_sufficient_content(self):
        html = "<html><head><title>Test</title></head><body>" + " ".join(["word"] * 300) + "</body></html>"
        result = check_js_rendering(html, "https://example.com")
        assert result["status"] == "pass"

    def test_js_dependent_page(self):
        html = '<html><head><title>My App</title></head><body><div id="root"></div><script src="app.js"></script></body></html>'
        result = check_js_rendering(html, "https://example.com")
        assert result["status"] == "fail"
        assert "javascript" in result["detail"].lower() or "JS" in result["detail"]

    def test_minimal_but_enough_content(self):
        html = "<html><head><title>Test</title></head><body>" + " ".join(["word"] * 201) + "</body></html>"
        result = check_js_rendering(html, "https://example.com")
        assert result["status"] == "pass"


class TestCheckCdnBlocks:
    def test_200_ok(self):
        result = check_cdn_blocks(200, "OK")
        assert result["status"] == "pass"

    def test_403_blocked(self):
        result = check_cdn_blocks(403, "Forbidden")
        assert result["status"] == "fail"
        assert "403" in result["detail"]

    def test_503_blocked(self):
        result = check_cdn_blocks(503, "Service Unavailable")
        assert result["status"] == "fail"


class TestCheckSitemap:
    def test_valid_sitemap(self):
        xml = '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/</loc></url></urlset>'
        result = check_sitemap(200, xml, robots_references_sitemap=True)
        assert result["status"] == "pass"
        assert result["url_count"] == 1

    def test_missing_sitemap(self):
        result = check_sitemap(404, "", robots_references_sitemap=False)
        assert result["status"] == "warning"

    def test_sitemap_not_in_robots(self):
        xml = '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/</loc></url></urlset>'
        result = check_sitemap(200, xml, robots_references_sitemap=False)
        assert result["status"] == "warning"
        assert "robots.txt" in result["detail"]


class TestCheckMetaTags:
    def test_no_blocking_tags(self):
        html = '<html><head><meta name="description" content="Hello"></head><body>Content</body></html>'
        result = check_meta_tags(html)
        assert result["status"] == "pass"

    def test_noindex_found(self):
        html = '<html><head><meta name="robots" content="noindex"></head><body>Content</body></html>'
        result = check_meta_tags(html)
        assert result["status"] == "fail"
        assert "noindex" in result["detail"]

    def test_nosnippet_found(self):
        html = '<html><head><meta name="robots" content="nosnippet"></head><body>Content</body></html>'
        result = check_meta_tags(html)
        assert result["status"] == "warning"
        assert "nosnippet" in result["detail"]


class TestCheckLlmsTxt:
    def test_exists(self):
        result = check_llms_txt(200, "# LLMs.txt\nSome content")
        assert result["status"] == "pass"

    def test_missing(self):
        result = check_llms_txt(404, "")
        assert result["status"] == "info"


class TestRunCrawlabilityGate:
    def test_returns_report_structure(self):
        report = run_crawlability_gate.__wrapped__(
            domain="example.com",
            robots_content="User-agent: *\nAllow: /\n",
            homepage_html="<html><body>" + " ".join(["word"] * 300) + "</body></html>",
            homepage_status=200,
            sitemap_status=200,
            sitemap_content='<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/</loc></url></urlset>',
            llms_txt_status=404,
            llms_txt_content="",
            sample_pages_html=[],
        )
        assert "robots_txt" in report
        assert "js_rendering" in report
        assert "cdn_blocks" in report
        assert "sitemap" in report
        assert "meta_tags" in report
        assert "llms_txt" in report
        assert "has_critical_blocker" in report
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd agents && python -m pytest tests/test_crawlability.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.improvement'`

- [ ] **Step 4: Implement crawlability module**

```python
# agents/src/improvement/crawlability.py
import re
from bs4 import BeautifulSoup
from xml.etree import ElementTree

AI_USER_AGENTS = [
    "GPTBot", "OAI-SearchBot", "ChatGPT-User",
    "ClaudeBot", "Claude-SearchBot", "anthropic-ai",
    "PerplexityBot", "Google-Extended",
]


def _parse_robots_rules(robots_content: str) -> dict[str, list[str]]:
    """Parse robots.txt into {user_agent: [disallow_paths]}."""
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
    """Check which AI user agents are blocked by robots.txt rules."""
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
    """Check if page content is available without JavaScript."""
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
    """Check if CDN/hosting blocks AI bot user agents."""
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
    """Check XML sitemap accessibility and validity."""
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
    """Check for noindex/nosnippet meta tags."""
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
        return {"status": "fail", "tags_found": issues, "detail": f"Found noindex — page will be excluded from AI indexing"}
    elif "nosnippet" in issues:
        return {"status": "warning", "tags_found": issues, "detail": f"Found nosnippet — prevents AI from citing page content"}
    elif issues:
        return {"status": "warning", "tags_found": issues, "detail": f"Found restrictive meta tags: {', '.join(issues)}"}

    return {"status": "pass", "tags_found": [], "detail": "No blocking meta tags found"}


def check_llms_txt(status_code: int, content: str) -> dict:
    """Check if llms.txt exists. Informational only — no AI company reads it yet."""
    if status_code == 200 and content.strip():
        return {"status": "pass", "detail": "llms.txt found (note: no major AI company reads this yet)"}
    return {"status": "info", "detail": "No llms.txt found — consider adding as a forward-looking step"}


def run_crawlability_gate(domain: str) -> dict:
    """Run all crawlability checks against a domain. Returns CrawlabilityReport dict."""
    import httpx

    base = f"https://{domain}"
    report = {}

    # 1. robots.txt
    robots_content = ""
    try:
        resp = httpx.get(f"{base}/robots.txt", timeout=10, follow_redirects=True)
        if resp.status_code == 200:
            robots_content = resp.text
    except Exception as e:
        print(f"  Crawlability: robots.txt fetch failed: {e}")
    report["robots_txt"] = check_robots_txt(robots_content)

    # Check if robots.txt references sitemap
    robots_references_sitemap = "sitemap:" in robots_content.lower()

    # 2. JS rendering — fetch homepage with plain HTTP
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

    # 3. CDN blocks — fetch with GPTBot user agent
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

    # 4. XML sitemap
    sitemap_status = 0
    sitemap_content = ""
    try:
        resp = httpx.get(f"{base}/sitemap.xml", timeout=10, follow_redirects=True)
        sitemap_status = resp.status_code
        sitemap_content = resp.text if resp.status_code == 200 else ""
    except Exception as e:
        print(f"  Crawlability: sitemap fetch failed: {e}")
    report["sitemap"] = check_sitemap(sitemap_status, sitemap_content, robots_references_sitemap)

    # 5. Meta tags — check homepage and a couple sample pages
    report["meta_tags"] = check_meta_tags(homepage_html)

    # 6. llms.txt
    llms_status = 0
    llms_content = ""
    try:
        resp = httpx.get(f"{base}/llms.txt", timeout=10, follow_redirects=True)
        llms_status = resp.status_code
        llms_content = resp.text if resp.status_code == 200 else ""
    except Exception:
        pass
    report["llms_txt"] = check_llms_txt(llms_status, llms_content)

    # Determine if there's a critical blocker
    critical_checks = ["robots_txt", "js_rendering", "cdn_blocks"]
    report["has_critical_blocker"] = any(
        report[check]["status"] == "fail" for check in critical_checks
    )

    return report


# Allow tests to call individual check functions without httpx by also providing
# a version that accepts pre-fetched data
run_crawlability_gate.__wrapped__ = lambda **kwargs: _run_gate_from_data(**kwargs)


def _run_gate_from_data(
    domain: str,
    robots_content: str,
    homepage_html: str,
    homepage_status: int,
    sitemap_status: int,
    sitemap_content: str,
    llms_txt_status: int,
    llms_txt_content: str,
    sample_pages_html: list[str],
) -> dict:
    """Test-friendly version that accepts pre-fetched data."""
    robots_references_sitemap = "sitemap:" in robots_content.lower()

    report = {
        "robots_txt": check_robots_txt(robots_content),
        "js_rendering": check_js_rendering(homepage_html, f"https://{domain}"),
        "cdn_blocks": check_cdn_blocks(homepage_status, "OK"),
        "sitemap": check_sitemap(sitemap_status, sitemap_content, robots_references_sitemap),
        "meta_tags": check_meta_tags(homepage_html),
        "llms_txt": check_llms_txt(llms_txt_status, llms_txt_content),
    }

    for i, page_html in enumerate(sample_pages_html):
        page_meta = check_meta_tags(page_html)
        if page_meta["status"] != "pass":
            report["meta_tags"] = page_meta
            break

    critical_checks = ["robots_txt", "js_rendering", "cdn_blocks"]
    report["has_critical_blocker"] = any(
        report[check]["status"] == "fail" for check in critical_checks
    )

    return report
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd agents && python -m pytest tests/test_crawlability.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add agents/src/improvement/__init__.py agents/src/improvement/crawlability.py agents/tests/test_crawlability.py
git commit -m "feat: add crawlability gate (Step 1) — robots.txt, JS rendering, CDN, sitemap, meta tags"
```

---

## Task 3: Step 2 — Site Inventory

**Files:**
- Create: `agents/src/improvement/inventory.py`
- Create: `agents/tests/test_inventory.py`

- [ ] **Step 1: Write the failing tests**

```python
# agents/tests/test_inventory.py
from src.improvement.inventory import extract_page_data, discover_pages_from_sitemap


SAMPLE_HTML = """
<html>
<head>
    <title>Best Budgeting Tools for Students</title>
    <meta property="article:modified_time" content="2026-06-15T00:00:00Z">
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": []}
    </script>
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "Organization", "name": "TestCo"}
    </script>
</head>
<body>
    <h1>Top 10 Budgeting Tools for College Students</h1>
    <p>Managing your finances in college can be challenging. Here are the best tools to help you budget effectively and save money while studying. These tools have been tested and reviewed by financial experts.</p>
    <h2>1. Mint</h2>
    <p>Mint is a free budgeting app that automatically tracks your spending.</p>
    <table>
        <thead><tr><th>Feature</th><th>Tool A</th><th>Tool B</th></tr></thead>
        <tbody><tr><td>Price</td><td>Free</td><td>$5/mo</td></tr></tbody>
    </table>
    <a href="https://external.com/source1">Source 1</a>
    <a href="https://external.com/source2">Source 2</a>
    <a href="https://testco.com/about">About Us</a>
</body>
</html>
"""


class TestExtractPageData:
    def test_extracts_title(self):
        data = extract_page_data("https://testco.com/blog/budgeting", SAMPLE_HTML, "testco.com")
        assert data["title"] == "Best Budgeting Tools for Students"

    def test_extracts_h1(self):
        data = extract_page_data("https://testco.com/blog/budgeting", SAMPLE_HTML, "testco.com")
        assert data["h1"] == "Top 10 Budgeting Tools for College Students"

    def test_extracts_first_paragraph(self):
        data = extract_page_data("https://testco.com/blog/budgeting", SAMPLE_HTML, "testco.com")
        assert "Managing your finances" in data["first_paragraph"]
        assert len(data["first_paragraph"]) <= 500

    def test_extracts_schema_types(self):
        data = extract_page_data("https://testco.com/blog/budgeting", SAMPLE_HTML, "testco.com")
        assert "FAQPage" in data["schema_types"]
        assert "Organization" in data["schema_types"]

    def test_counts_words(self):
        data = extract_page_data("https://testco.com/blog/budgeting", SAMPLE_HTML, "testco.com")
        assert data["word_count"] > 0

    def test_detects_last_modified(self):
        data = extract_page_data("https://testco.com/blog/budgeting", SAMPLE_HTML, "testco.com")
        assert data["last_modified"] is not None
        assert "2026-06-15" in data["last_modified"]

    def test_counts_outbound_links(self):
        data = extract_page_data("https://testco.com/blog/budgeting", SAMPLE_HTML, "testco.com")
        assert data["outbound_link_count"] == 2  # excludes testco.com self-links

    def test_detects_faq_schema(self):
        data = extract_page_data("https://testco.com/blog/budgeting", SAMPLE_HTML, "testco.com")
        assert data["has_faq_schema"] is True

    def test_detects_comparison_table(self):
        data = extract_page_data("https://testco.com/blog/budgeting", SAMPLE_HTML, "testco.com")
        assert data["has_comparison_table"] is True

    def test_stores_raw_html(self):
        data = extract_page_data("https://testco.com/blog/budgeting", SAMPLE_HTML, "testco.com")
        assert data["raw_html"] == SAMPLE_HTML

    def test_no_schema_page(self):
        html = "<html><head><title>Simple</title></head><body><h1>Hello</h1><p>World</p></body></html>"
        data = extract_page_data("https://testco.com/simple", html, "testco.com")
        assert data["schema_types"] == []
        assert data["has_faq_schema"] is False

    def test_no_table_page(self):
        html = "<html><head><title>Simple</title></head><body><h1>Hello</h1><p>World</p></body></html>"
        data = extract_page_data("https://testco.com/simple", html, "testco.com")
        assert data["has_comparison_table"] is False


class TestDiscoverPagesFromSitemap:
    def test_parses_sitemap_xml(self):
        xml = '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/</loc></url><url><loc>https://example.com/about</loc></url></urlset>'
        urls = discover_pages_from_sitemap(xml, "example.com", max_pages=20)
        assert len(urls) == 2
        assert "https://example.com/" in urls

    def test_respects_max_pages(self):
        locs = "".join(f"<url><loc>https://example.com/page{i}</loc></url>" for i in range(50))
        xml = f'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{locs}</urlset>'
        urls = discover_pages_from_sitemap(xml, "example.com", max_pages=10)
        assert len(urls) == 10

    def test_filters_external_domains(self):
        xml = '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/</loc></url><url><loc>https://other.com/page</loc></url></urlset>'
        urls = discover_pages_from_sitemap(xml, "example.com", max_pages=20)
        assert len(urls) == 1

    def test_invalid_xml_returns_empty(self):
        urls = discover_pages_from_sitemap("not xml at all", "example.com", max_pages=20)
        assert urls == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd agents && python -m pytest tests/test_inventory.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement inventory module**

```python
# agents/src/improvement/inventory.py
import json
import re
import httpx
from bs4 import BeautifulSoup
from xml.etree import ElementTree
from urllib.parse import urljoin, urlparse


def discover_pages_from_sitemap(xml_content: str, domain: str, max_pages: int = 20) -> list[str]:
    """Parse sitemap XML and return URLs belonging to the domain."""
    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError:
        return []

    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = root.findall(".//sm:loc", ns) or root.findall(".//loc")
    urls = [loc.text.strip() for loc in locs if loc.text and domain in loc.text]
    return urls[:max_pages]


def discover_pages(domain: str, max_pages: int = 20) -> list[str]:
    """Discover pages via sitemap.xml, falling back to homepage link crawl."""
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
    """Extract structured data from a page's HTML for inventory."""
    soup = BeautifulSoup(html, "html.parser")

    # Title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # H1
    h1_tag = soup.find("h1")
    h1 = h1_tag.get_text(strip=True) if h1_tag else ""

    # Schema types from JSON-LD
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

    # Last modified date from meta tags
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

    # Strip boilerplate for content analysis
    for tag in soup.find_all(["nav", "footer", "header", "aside", "script", "style"]):
        tag.decompose()

    # First paragraph (up to 500 chars of body text)
    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 20]
    first_paragraph = paragraphs[0][:500] if paragraphs else ""

    # Word count
    body = soup.find("body")
    raw_text = body.get_text(separator=" ", strip=True) if body else ""
    word_count = len(raw_text.split())

    # Outbound links (external, excluding self-domain)
    outbound_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http") and client_domain not in href:
            outbound_links.append(href)

    # Comparison table detection
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
    """Discover pages and extract inventory data for each."""
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents && python -m pytest tests/test_inventory.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/src/improvement/inventory.py agents/tests/test_inventory.py
git commit -m "feat: add site inventory (Step 2) — page discovery and data extraction"
```

---

## Task 4: Step 3 — Query-Page Matcher (SBERT)

**Files:**
- Create: `agents/src/improvement/matcher.py`
- Create: `agents/tests/test_matcher.py`
- Modify: `agents/requirements.txt`
- Modify: `agents/pyproject.toml`

- [ ] **Step 1: Add sentence-transformers dependency**

Add `sentence-transformers>=3.0.0` to `agents/requirements.txt` (new line after `supabase>=2.0.0`).

Add `"sentence-transformers>=3.0.0"` to the `dependencies` list in `agents/pyproject.toml`.

- [ ] **Step 2: Write the failing tests**

```python
# agents/tests/test_matcher.py
from src.improvement.matcher import (
    build_page_text,
    classify_match,
    match_queries_to_pages,
)


class TestBuildPageText:
    def test_concatenates_fields(self):
        page = {"title": "Best Tools", "h1": "Top 10 Tools", "first_paragraph": "Here are the tools."}
        result = build_page_text(page)
        assert "Best Tools" in result
        assert "Top 10 Tools" in result
        assert "Here are the tools" in result

    def test_handles_empty_h1(self):
        page = {"title": "Best Tools", "h1": "", "first_paragraph": "Content here."}
        result = build_page_text(page)
        assert "Best Tools" in result
        assert "Content here" in result


class TestClassifyMatch:
    def test_high_score_matched(self):
        assert classify_match(0.7) == "matched"

    def test_medium_score_weak(self):
        assert classify_match(0.4) == "weak"

    def test_low_score_content_gap(self):
        assert classify_match(0.2) == "content_gap"

    def test_boundary_matched(self):
        assert classify_match(0.51) == "matched"

    def test_boundary_weak(self):
        assert classify_match(0.5) == "weak"

    def test_boundary_gap(self):
        assert classify_match(0.3) == "weak"

    def test_boundary_gap_below(self):
        assert classify_match(0.29) == "content_gap"


class TestMatchQueriesToPages:
    def test_returns_match_per_query(self):
        pages = [
            {"url": "https://example.com/budgeting", "title": "Budgeting Guide", "h1": "How to Budget", "first_paragraph": "Learn budgeting strategies for saving money and managing expenses."},
            {"url": "https://example.com/investing", "title": "Investing 101", "h1": "Start Investing", "first_paragraph": "Learn how to invest in stocks, bonds, and mutual funds."},
        ]
        queries = [
            {"query": "best budgeting tips for students", "query_id": "q1", "bucket": "awareness"},
            {"query": "how to start investing in stocks", "query_id": "q2", "bucket": "consideration"},
        ]
        results = match_queries_to_pages(pages, queries)
        assert len(results) == 2
        assert all("match_type" in r for r in results)
        assert all("similarity_score" in r for r in results)
        assert all("query_id" in r for r in results)

    def test_content_gap_when_no_relevant_page(self):
        pages = [
            {"url": "https://example.com/about", "title": "About Us", "h1": "Our Company", "first_paragraph": "We are a company that does things."},
        ]
        queries = [
            {"query": "quantum computing applications in healthcare", "query_id": "q1", "bucket": "awareness"},
        ]
        results = match_queries_to_pages(pages, queries)
        assert len(results) == 1
        # A very irrelevant query should get a low score
        assert results[0]["similarity_score"] < 0.5

    def test_empty_pages_all_content_gaps(self):
        queries = [
            {"query": "test query", "query_id": "q1", "bucket": "awareness"},
        ]
        results = match_queries_to_pages([], queries)
        assert len(results) == 1
        assert results[0]["match_type"] == "content_gap"
        assert results[0]["matched_page_url"] is None

    def test_empty_queries_returns_empty(self):
        pages = [{"url": "https://example.com/", "title": "Home", "h1": "Welcome", "first_paragraph": "Hello world."}]
        results = match_queries_to_pages(pages, [])
        assert results == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd agents && python -m pytest tests/test_matcher.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Implement matcher module**

```python
# agents/src/improvement/matcher.py
import numpy as np

MATCH_THRESHOLD = 0.5
WEAK_THRESHOLD = 0.3

_model = None


def _get_model():
    """Lazy-load the SBERT model (80MB, first call downloads it)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def build_page_text(page: dict) -> str:
    """Concatenate title + H1 + first paragraph for embedding."""
    parts = [page.get("title", ""), page.get("h1", ""), page.get("first_paragraph", "")]
    return " ".join(p for p in parts if p).strip()


def classify_match(score: float) -> str:
    """Classify similarity score into match type."""
    if score > MATCH_THRESHOLD:
        return "matched"
    elif score >= WEAK_THRESHOLD:
        return "weak"
    else:
        return "content_gap"


def match_queries_to_pages(pages: list[dict], queries: list[dict]) -> list[dict]:
    """Match each query to its best page using SBERT cosine similarity.

    Args:
        pages: List of page inventory dicts with title, h1, first_paragraph, url.
        queries: List of dicts with query, query_id, bucket.

    Returns:
        List of match result dicts, one per query.
    """
    if not queries:
        return []

    if not pages:
        return [
            {
                "query": q["query"],
                "query_id": q["query_id"],
                "match_type": "content_gap",
                "matched_page_url": None,
                "similarity_score": 0.0,
                "bucket": q.get("bucket", ""),
            }
            for q in queries
        ]

    model = _get_model()

    page_texts = [build_page_text(p) for p in pages]
    query_texts = [q["query"] for q in queries]

    page_embeddings = model.encode(page_texts, convert_to_numpy=True, normalize_embeddings=True)
    query_embeddings = model.encode(query_texts, convert_to_numpy=True, normalize_embeddings=True)

    # Cosine similarity matrix: (num_queries, num_pages)
    # Since embeddings are normalized, dot product = cosine similarity
    similarity_matrix = np.dot(query_embeddings, page_embeddings.T)

    results = []
    for i, q in enumerate(queries):
        best_page_idx = int(np.argmax(similarity_matrix[i]))
        best_score = float(similarity_matrix[i][best_page_idx])
        match_type = classify_match(best_score)

        results.append({
            "query": q["query"],
            "query_id": q["query_id"],
            "match_type": match_type,
            "matched_page_url": pages[best_page_idx]["url"] if match_type != "content_gap" else None,
            "similarity_score": round(best_score, 4),
            "bucket": q.get("bucket", ""),
        })

    return results
```

- [ ] **Step 5: Install dependency and run tests**

Run: `cd agents && pip install sentence-transformers>=3.0.0 && python -m pytest tests/test_matcher.py -v`
Expected: All tests PASS (first run may take ~30s to download the 80MB model)

- [ ] **Step 6: Commit**

```bash
git add agents/src/improvement/matcher.py agents/tests/test_matcher.py agents/requirements.txt agents/pyproject.toml
git commit -m "feat: add query-page matcher (Step 3) — SBERT embeddings + cosine similarity"
```

---

## Task 5: Validators (used by Steps 4 and 6)

**Files:**
- Create: `agents/src/improvement/validators.py`
- Create: `agents/tests/test_validators.py`

- [ ] **Step 1: Write the failing tests**

```python
# agents/tests/test_validators.py
from src.improvement.validators import (
    validate_json_ld,
    validate_html_fragment,
    check_link_alive,
)


class TestValidateJsonLd:
    def test_valid_faq_schema(self):
        json_ld = '{"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": "What is GEO?", "acceptedAnswer": {"@type": "Answer", "text": "GEO stands for Generative Engine Optimization."}}]}'
        result = validate_json_ld(json_ld)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_invalid_json(self):
        result = validate_json_ld("{not valid json}")
        assert result["valid"] is False
        assert any("parse" in e.lower() or "json" in e.lower() for e in result["errors"])

    def test_missing_context(self):
        json_ld = '{"@type": "FAQPage", "mainEntity": []}'
        result = validate_json_ld(json_ld)
        assert result["valid"] is False
        assert any("@context" in e for e in result["errors"])

    def test_missing_type(self):
        json_ld = '{"@context": "https://schema.org", "name": "Test"}'
        result = validate_json_ld(json_ld)
        assert result["valid"] is False
        assert any("@type" in e for e in result["errors"])

    def test_empty_string(self):
        result = validate_json_ld("")
        assert result["valid"] is False

    def test_valid_organization(self):
        json_ld = '{"@context": "https://schema.org", "@type": "Organization", "name": "TestCo", "url": "https://testco.com"}'
        result = validate_json_ld(json_ld)
        assert result["valid"] is True


class TestValidateHtmlFragment:
    def test_valid_html(self):
        result = validate_html_fragment("<p>Hello <strong>world</strong></p>")
        assert result["valid"] is True

    def test_empty_string(self):
        result = validate_html_fragment("")
        assert result["valid"] is False

    def test_script_injection(self):
        result = validate_html_fragment('<p>Hello</p><script>alert("xss")</script>')
        assert result["valid"] is False
        assert any("script" in e.lower() for e in result["errors"])


class TestCheckLinkAlive:
    def test_returns_dict_structure(self):
        result = check_link_alive("https://httpbin.org/status/200")
        assert "alive" in result
        assert "status_code" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd agents && python -m pytest tests/test_validators.py -v`
Expected: FAIL

- [ ] **Step 3: Implement validators**

```python
# agents/src/improvement/validators.py
import json
import re
import httpx
from bs4 import BeautifulSoup

REQUIRED_FIELDS_BY_TYPE = {
    "FAQPage": ["mainEntity"],
    "Organization": ["name"],
    "WebSite": ["name", "url"],
    "Article": ["headline"],
    "BlogPosting": ["headline"],
    "NewsArticle": ["headline"],
    "HowTo": ["name", "step"],
    "BreadcrumbList": ["itemListElement"],
    "Product": ["name"],
    "LocalBusiness": ["name"],
}


def validate_json_ld(json_ld_str: str) -> dict:
    """Validate a JSON-LD string for structural correctness."""
    errors = []

    if not json_ld_str or not json_ld_str.strip():
        return {"valid": False, "errors": ["Empty JSON-LD string"]}

    try:
        data = json.loads(json_ld_str)
    except json.JSONDecodeError as e:
        return {"valid": False, "errors": [f"JSON parse error: {e}"]}

    if not isinstance(data, dict):
        return {"valid": False, "errors": ["JSON-LD must be an object"]}

    if "@context" not in data:
        errors.append("Missing @context — must be 'https://schema.org'")

    schema_type = data.get("@type")
    if not schema_type:
        errors.append("Missing @type — every JSON-LD block needs a schema.org type")

    if schema_type and schema_type in REQUIRED_FIELDS_BY_TYPE:
        for field in REQUIRED_FIELDS_BY_TYPE[schema_type]:
            if field not in data:
                errors.append(f"Missing required field '{field}' for @type '{schema_type}'")

    if errors:
        return {"valid": False, "errors": errors}

    return {"valid": True, "errors": []}


def validate_html_fragment(html: str) -> dict:
    """Validate an HTML fragment for safety and basic correctness."""
    errors = []

    if not html or not html.strip():
        return {"valid": False, "errors": ["Empty HTML fragment"]}

    if re.search(r'<script\b', html, re.I):
        errors.append("HTML contains <script> tag — potential XSS risk")

    if re.search(r'\bon\w+\s*=', html, re.I):
        errors.append("HTML contains inline event handlers — potential XSS risk")

    if errors:
        return {"valid": False, "errors": errors}

    return {"valid": True, "errors": []}


def check_link_alive(url: str, timeout: int = 5) -> dict:
    """Check if a URL returns a successful HTTP response."""
    try:
        resp = httpx.head(url, timeout=timeout, follow_redirects=True,
                          headers={"User-Agent": "Mozilla/5.0 (compatible; VV-LinkCheck/1.0)"})
        alive = resp.status_code < 400
        return {"alive": alive, "status_code": resp.status_code, "url": url}
    except Exception as e:
        return {"alive": False, "status_code": 0, "url": url, "error": str(e)}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents && python -m pytest tests/test_validators.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/src/improvement/validators.py agents/tests/test_validators.py
git commit -m "feat: add validators — JSON-LD, HTML fragment, link checks"
```

---

## Task 6: Step 4 — Citation-Readiness Scorer

**Files:**
- Create: `agents/src/improvement/scorer.py`
- Create: `agents/tests/test_scorer.py`

- [ ] **Step 1: Write the failing tests**

```python
# agents/tests/test_scorer.py
from src.improvement.scorer import (
    check_answer_first,
    check_faq_schema,
    check_comparison_tables,
    check_lists,
    check_freshness,
    check_word_count,
    check_source_citations,
    check_author_attribution,
    check_schema_validation,
    compute_structural_score,
)


RICH_HTML = """
<html><head>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":"What is GEO?","acceptedAnswer":{"@type":"Answer","text":"GEO is optimization."}}]}</script>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Organization","name":"TestCo","url":"https://testco.com"}</script>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebSite","name":"TestCo","url":"https://testco.com"}</script>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"Home","item":"https://testco.com"}]}</script>
</head><body>
<h1>What is GEO?</h1>
<p>Generative Engine Optimization is a strategy that improves your brand visibility in AI-generated responses. Studies show that structured content increases citation rates by up to 17.3 percent according to research from the University of Tokyo.</p>
<h2>Key Benefits</h2>
<ol><li>Increased visibility</li><li>More citations</li><li>Better authority</li></ol>
<ul><li>Point A</li><li>Point B</li></ul>
<h2>Comparison</h2>
<table><thead><tr><th>Feature</th><th>GEO</th><th>SEO</th></tr></thead><tbody><tr><td>Focus</td><td>AI</td><td>Search</td></tr></tbody></table>
<h2>Sources</h2>
<p>According to <a href="https://example.edu/study">this study</a> and <a href="https://gov.example.org/report">this report</a> and <a href="https://external.com/data">external data</a>.</p>
<p>Written by Dr. Jane Smith, PhD in Computer Science. Reviewed by Prof. John Doe.</p>
</body></html>
"""


class TestCheckAnswerFirst:
    def test_declarative_opening(self):
        html = "<body><p>Generative Engine Optimization is a strategy that improves your brand visibility in AI responses. It works by structuring content for AI crawlers.</p></body>"
        result = check_answer_first(html)
        assert result["score"] > 0
        assert result["has_declarative_opening"] is True

    def test_question_opening(self):
        html = "<body><p>Have you ever wondered how AI search works? Let us explore the topic together and discover the answer.</p></body>"
        result = check_answer_first(html)
        assert result["score"] == 0
        assert result["has_declarative_opening"] is False

    def test_filler_opening(self):
        html = "<body><p>Welcome to our website! We are so glad you are here. Let us tell you about ourselves and what we do for our customers.</p></body>"
        result = check_answer_first(html)
        assert result["score"] == 0


class TestCheckFaqSchema:
    def test_valid_faq_present(self):
        result = check_faq_schema(RICH_HTML)
        assert result["score"] > 0
        assert result["has_faq"] is True

    def test_no_faq_schema(self):
        html = "<html><head></head><body><p>No FAQ here</p></body></html>"
        result = check_faq_schema(html)
        assert result["score"] == 0
        assert result["has_faq"] is False


class TestCheckComparisonTables:
    def test_table_with_comparison_headers(self):
        result = check_comparison_tables(RICH_HTML)
        assert result["score"] > 0
        assert result["table_count"] >= 1

    def test_no_tables(self):
        html = "<html><body><p>No tables</p></body></html>"
        result = check_comparison_tables(html)
        assert result["score"] == 0
        assert result["table_count"] == 0


class TestCheckLists:
    def test_has_lists(self):
        result = check_lists(RICH_HTML)
        assert result["score"] > 0
        assert result["list_count"] >= 2

    def test_no_lists(self):
        html = "<html><body><p>No lists</p></body></html>"
        result = check_lists(html)
        assert result["score"] == 0


class TestCheckFreshness:
    def test_recent_date(self):
        result = check_freshness("2026-07-01T00:00:00Z")
        assert result["score"] == 10

    def test_old_date(self):
        result = check_freshness("2025-01-01T00:00:00Z")
        assert result["score"] < 10

    def test_no_date(self):
        result = check_freshness(None)
        assert result["score"] == 0


class TestCheckWordCount:
    def test_long_content_with_sections(self):
        html = "<body>" + "<h2>Section</h2><p>" + " ".join(["word"] * 700) + "</p>" * 3 + "</body>"
        result = check_word_count(html)
        assert result["score"] == 10

    def test_short_content(self):
        html = "<body><p>Short content here.</p></body>"
        result = check_word_count(html)
        assert result["score"] < 10


class TestCheckSourceCitations:
    def test_has_authoritative_citations(self):
        result = check_source_citations(RICH_HTML, "testco.com")
        assert result["score"] > 0
        assert result["external_count"] >= 3

    def test_no_external_links(self):
        html = '<html><body><p>No links at all</p></body></html>'
        result = check_source_citations(html, "testco.com")
        assert result["score"] == 0
        assert result["external_count"] == 0


class TestCheckAuthorAttribution:
    def test_has_author(self):
        result = check_author_attribution(RICH_HTML)
        assert result["score"] > 0

    def test_no_author(self):
        html = "<html><body><p>Just content, no author info.</p></body></html>"
        result = check_author_attribution(html)
        assert result["score"] == 0


class TestCheckSchemaValidation:
    def test_complete_schema(self):
        result = check_schema_validation(RICH_HTML)
        assert result["score"] > 0
        assert result["schema_status"] in ("valid_complete", "valid_incomplete")

    def test_no_schema(self):
        html = "<html><head></head><body><p>No schema</p></body></html>"
        result = check_schema_validation(html)
        assert result["score"] == 0
        assert result["schema_status"] == "missing"

    def test_broken_schema(self):
        html = '<html><head><script type="application/ld+json">{not valid json}</script></head><body></body></html>'
        result = check_schema_validation(html)
        assert result["schema_status"] == "broken"


class TestComputeStructuralScore:
    def test_returns_total_and_breakdown(self):
        result = compute_structural_score(RICH_HTML, "testco.com", "2026-07-01T00:00:00Z")
        assert "structural_score" in result
        assert "check_results" in result
        assert 0 <= result["structural_score"] <= 100
        assert "answer_first" in result["check_results"]
        assert "schema_validation" in result["check_results"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd agents && python -m pytest tests/test_scorer.py -v`
Expected: FAIL

- [ ] **Step 3: Implement scorer module**

```python
# agents/src/improvement/scorer.py
import json
import re
from datetime import datetime, timezone
from bs4 import BeautifulSoup

FILLER_PATTERNS = re.compile(
    r"^(welcome|hello|hi |thanks for|thank you|we are (so )?glad|"
    r"let us |let's |in this (article|post|guide)|"
    r"are you looking|have you ever|do you want)",
    re.I
)

AUTHORITATIVE_TLDS = re.compile(r"\.(gov|edu|org|ac\.[a-z]{2})(/|$)")
CREDENTIAL_PATTERNS = re.compile(
    r"(ph\.?d|m\.?d|m\.?b\.?a|dr\.|prof\.|professor|"
    r"reviewed by|written by|author:|by [A-Z][a-z]+ [A-Z][a-z]+)",
    re.I
)

BASELINE_SCHEMA_TYPES = {"Organization", "WebSite", "BreadcrumbList"}
HIGH_VALUE_SCHEMA_TYPES = {"FAQPage", "HowTo", "Article", "NewsArticle", "BlogPosting", "Product"}


def check_answer_first(html: str) -> dict:
    """Check if first 150 words contain a declarative answer (0-15 points)."""
    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("body")
    if not body:
        return {"score": 0, "has_declarative_opening": False, "detail": "No body tag found"}

    for tag in body.find_all(["nav", "footer", "header", "aside", "script", "style"]):
        tag.decompose()

    paragraphs = [p.get_text(strip=True) for p in body.find_all("p") if len(p.get_text(strip=True)) > 20]
    if not paragraphs:
        return {"score": 0, "has_declarative_opening": False, "detail": "No paragraphs found"}

    first_text = paragraphs[0]
    first_words = " ".join(first_text.split()[:150])

    if first_text.strip().startswith("?") or first_text.strip().endswith("?"):
        return {"score": 0, "has_declarative_opening": False, "detail": "Opening is a question"}

    if FILLER_PATTERNS.match(first_text.strip()):
        return {"score": 0, "has_declarative_opening": False, "detail": "Opening uses filler/welcome language"}

    sentences = re.split(r'[.!]', first_words)
    declarative_sentences = [s.strip() for s in sentences if s.strip() and not s.strip().endswith("?")]

    if declarative_sentences and len(declarative_sentences[0].split()) >= 5:
        return {"score": 15, "has_declarative_opening": True, "detail": "Strong declarative opening"}

    return {"score": 0, "has_declarative_opening": False, "detail": "Opening lacks a clear declarative answer"}


def check_faq_schema(html: str) -> dict:
    """Check for valid FAQPage JSON-LD schema (0-10 points)."""
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if data.get("@type") == "FAQPage" and data.get("mainEntity"):
                qa_count = len(data["mainEntity"])
                return {"score": 10, "has_faq": True, "qa_count": qa_count, "detail": f"FAQPage schema with {qa_count} Q&A pair(s)"}
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass

    return {"score": 0, "has_faq": False, "qa_count": 0, "detail": "No FAQPage schema found"}


def check_comparison_tables(html: str) -> dict:
    """Check for comparison-style tables (0-10 points)."""
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    comparison_count = 0

    for table in tables:
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if len(headers) >= 3:
            comparison_count += 1

    if comparison_count > 0:
        return {"score": 10, "table_count": comparison_count, "detail": f"{comparison_count} comparison table(s) found"}
    return {"score": 0, "table_count": 0, "detail": "No comparison tables found"}


def check_lists(html: str) -> dict:
    """Check for ordered and unordered lists (0-10 points)."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["nav", "footer", "header"]):
        tag.decompose()

    ol_count = len(soup.find_all("ol"))
    ul_count = len(soup.find_all("ul"))
    total = ol_count + ul_count

    if total == 0:
        return {"score": 0, "list_count": 0, "detail": "No lists found"}
    elif total >= 3:
        return {"score": 10, "list_count": total, "detail": f"{total} lists found (ordered: {ol_count}, unordered: {ul_count})"}
    elif total >= 1:
        return {"score": 5, "list_count": total, "detail": f"{total} list(s) found"}
    return {"score": 0, "list_count": 0, "detail": "No lists found"}


def check_freshness(last_modified: str | None) -> dict:
    """Check content freshness based on last modified date (0-10 points)."""
    if not last_modified:
        return {"score": 0, "age_days": None, "detail": "No last-modified date available"}

    try:
        try:
            dt = datetime.fromisoformat(last_modified.replace("Z", "+00:00"))
        except ValueError:
            from dateutil import parser as dateutil_parser
            dt = dateutil_parser.parse(last_modified)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        age_days = (datetime.now(timezone.utc) - dt).days

        if age_days <= 90:
            return {"score": 10, "age_days": age_days, "detail": f"Content is {age_days} days old — fresh"}
        elif age_days <= 180:
            return {"score": 6, "age_days": age_days, "detail": f"Content is {age_days} days old — getting stale"}
        elif age_days <= 365:
            return {"score": 3, "age_days": age_days, "detail": f"Content is {age_days} days old — stale"}
        else:
            return {"score": 1, "age_days": age_days, "detail": f"Content is {age_days} days old — critically stale"}
    except Exception:
        return {"score": 0, "age_days": None, "detail": f"Could not parse date: {last_modified}"}


def check_word_count(html: str) -> dict:
    """Check word count and section structure (0-10 points)."""
    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("body")
    if not body:
        return {"score": 0, "word_count": 0, "h2_count": 0, "detail": "No body tag"}

    for tag in body.find_all(["nav", "footer", "header", "script", "style"]):
        tag.decompose()

    text = body.get_text(separator=" ", strip=True)
    word_count = len(text.split())
    h2_count = len(body.find_all("h2"))

    if word_count >= 2000 and h2_count >= 3:
        return {"score": 10, "word_count": word_count, "h2_count": h2_count, "detail": f"{word_count} words, {h2_count} H2 sections"}
    elif word_count >= 1000:
        return {"score": 6, "word_count": word_count, "h2_count": h2_count, "detail": f"{word_count} words — could be longer"}
    elif word_count >= 500:
        return {"score": 3, "word_count": word_count, "h2_count": h2_count, "detail": f"{word_count} words — thin content"}
    return {"score": 1, "word_count": word_count, "h2_count": h2_count, "detail": f"Only {word_count} words"}


def check_source_citations(html: str, client_domain: str) -> dict:
    """Check outbound links to authoritative sources (0-10 points)."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["nav", "footer", "header"]):
        tag.decompose()

    external_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http") and client_domain not in href:
            external_links.append(href)

    authoritative = [l for l in external_links if AUTHORITATIVE_TLDS.search(l)]

    if len(external_links) >= 5:
        score = 7
    elif len(external_links) >= 3:
        score = 5
    elif len(external_links) >= 1:
        score = 2
    else:
        return {"score": 0, "external_count": 0, "authoritative_count": 0, "detail": "No external citations"}

    score += min(3, len(authoritative))

    return {
        "score": min(10, score),
        "external_count": len(external_links),
        "authoritative_count": len(authoritative),
        "detail": f"{len(external_links)} external links, {len(authoritative)} authoritative (.gov/.edu/.org)",
    }


def check_author_attribution(html: str) -> dict:
    """Check for author name, credentials, or reviewed-by markup (0-10 points)."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)

    matches = CREDENTIAL_PATTERNS.findall(text)

    # Also check for schema.org author
    has_schema_author = False
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if "author" in data:
                has_schema_author = True
        except (json.JSONDecodeError, TypeError):
            pass

    if has_schema_author and matches:
        return {"score": 10, "has_author": True, "has_credentials": True, "detail": "Author with credentials and schema markup"}
    elif matches:
        return {"score": 7, "has_author": True, "has_credentials": True, "detail": f"Author attribution found: {matches[0]}"}
    elif has_schema_author:
        return {"score": 5, "has_author": True, "has_credentials": False, "detail": "Author in schema but no visible credentials"}
    return {"score": 0, "has_author": False, "has_credentials": False, "detail": "No author attribution found"}


def check_schema_validation(html: str) -> dict:
    """Validate JSON-LD schema blocks for completeness and correctness (0-15 points)."""
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.find_all("script", type="application/ld+json")

    if not scripts:
        return {"score": 0, "schema_status": "missing", "schema_errors": [], "types_found": [], "detail": "No JSON-LD schema found"}

    types_found = set()
    errors = []
    has_malformed = False

    for script in scripts:
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            has_malformed = True
            errors.append("Malformed JSON-LD block — crawlers silently ignore this")
            continue

        if "@context" not in data:
            errors.append("JSON-LD block missing @context")

        schema_type = data.get("@type")
        if not schema_type:
            errors.append("JSON-LD block missing @type")
        else:
            if isinstance(schema_type, list):
                types_found.update(schema_type)
            else:
                types_found.add(schema_type)

    if has_malformed and not types_found:
        return {"score": 2, "schema_status": "broken", "schema_errors": errors, "types_found": list(types_found), "detail": "Schema exists but is broken"}

    if errors:
        score = max(3, 15 - len(errors) * 3)
        return {"score": score, "schema_status": "broken", "schema_errors": errors, "types_found": list(types_found), "detail": f"Schema has {len(errors)} error(s)"}

    has_baseline = BASELINE_SCHEMA_TYPES.issubset(types_found)
    has_high_value = bool(types_found & HIGH_VALUE_SCHEMA_TYPES)

    if has_baseline and has_high_value:
        return {"score": 15, "schema_status": "valid_complete", "schema_errors": [], "types_found": list(types_found), "detail": "Complete schema coverage"}
    elif has_baseline or has_high_value:
        return {"score": 10, "schema_status": "valid_incomplete", "schema_errors": [], "types_found": list(types_found), "detail": f"Schema present ({', '.join(types_found)}) but incomplete"}
    else:
        return {"score": 5, "schema_status": "valid_incomplete", "schema_errors": [], "types_found": list(types_found), "detail": "Schema types found but missing baseline coverage"}


def compute_structural_score(html: str, client_domain: str, last_modified: str | None) -> dict:
    """Run all 9 deterministic checks and return total score + breakdown."""
    checks = {
        "answer_first": check_answer_first(html),
        "faq_schema": check_faq_schema(html),
        "comparison_tables": check_comparison_tables(html),
        "lists": check_lists(html),
        "freshness": check_freshness(last_modified),
        "word_count": check_word_count(html),
        "source_citations": check_source_citations(html, client_domain),
        "author_attribution": check_author_attribution(html),
        "schema_validation": check_schema_validation(html),
    }

    total = sum(check["score"] for check in checks.values())

    schema_result = checks["schema_validation"]

    return {
        "structural_score": min(100, total),
        "check_results": checks,
        "schema_status": schema_result["schema_status"],
        "schema_errors": schema_result.get("schema_errors", []),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents && python -m pytest tests/test_scorer.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/src/improvement/scorer.py agents/tests/test_scorer.py
git commit -m "feat: add citation-readiness scorer (Step 4) — 9 deterministic structural checks"
```

---

## Task 7: Step 5 — Competitive Gap Check

**Files:**
- Create: `agents/src/improvement/gap_check.py`
- Create: `agents/tests/test_gap_check.py`

- [ ] **Step 1: Write the failing tests**

```python
# agents/tests/test_gap_check.py
from src.improvement.gap_check import compute_gap_for_query, check_competitive_gaps


class TestComputeGapForQuery:
    def test_competitor_winning(self):
        gap_data = {
            "query": "best tools",
            "client_mention_rate": 0.4,
            "competitor_data": [
                {"name": "CompA", "mention_rate": 0.8},
                {"name": "CompB", "mention_rate": 0.6},
            ],
        }
        result = compute_gap_for_query(gap_data)
        assert result["competitive_gap"] > 0
        assert result["top_competitor"] == "CompA"
        assert abs(result["competitive_gap"] - 0.4) < 0.01

    def test_client_winning(self):
        gap_data = {
            "query": "best tools",
            "client_mention_rate": 0.9,
            "competitor_data": [
                {"name": "CompA", "mention_rate": 0.3},
            ],
        }
        result = compute_gap_for_query(gap_data)
        assert result["competitive_gap"] < 0

    def test_equal_rates(self):
        gap_data = {
            "query": "best tools",
            "client_mention_rate": 0.5,
            "competitor_data": [
                {"name": "CompA", "mention_rate": 0.5},
            ],
        }
        result = compute_gap_for_query(gap_data)
        assert result["competitive_gap"] == 0.0

    def test_no_competitors(self):
        gap_data = {
            "query": "best tools",
            "client_mention_rate": 0.5,
            "competitor_data": [],
        }
        result = compute_gap_for_query(gap_data)
        assert result["competitive_gap"] == 0.0
        assert result["top_competitor"] is None


class TestCheckCompetitiveGaps:
    def test_filters_to_matched_queries(self):
        matches = [
            {"query": "q1", "query_id": "id1", "match_type": "matched", "matched_page_url": "https://x.com/p1"},
            {"query": "q2", "query_id": "id2", "match_type": "content_gap", "matched_page_url": None},
        ]
        gap_data = [
            {"query": "q1", "client_mention_rate": 0.3, "competitor_data": [{"name": "CompA", "mention_rate": 0.8}]},
            {"query": "q2", "client_mention_rate": 0.0, "competitor_data": [{"name": "CompA", "mention_rate": 0.6}]},
            {"query": "q3", "client_mention_rate": 0.5, "competitor_data": []},
        ]
        results = check_competitive_gaps(matches, gap_data)
        assert len(results) == 2  # q1 and q2 from matches
        result_queries = {r["query"] for r in results}
        assert "q1" in result_queries
        assert "q2" in result_queries

    def test_empty_gaps_returns_zeros(self):
        matches = [
            {"query": "q1", "query_id": "id1", "match_type": "matched", "matched_page_url": "https://x.com/p1"},
        ]
        results = check_competitive_gaps(matches, [])
        assert len(results) == 1
        assert results[0]["competitive_gap"] == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd agents && python -m pytest tests/test_gap_check.py -v`
Expected: FAIL

- [ ] **Step 3: Implement gap check module**

```python
# agents/src/improvement/gap_check.py


def compute_gap_for_query(gap_data: dict) -> dict:
    """Compute the competitive gap for a single query.

    Gap = max(competitor_mention_rate) - client_mention_rate.
    Positive = competitor winning. Negative = client winning.
    """
    client_rate = gap_data.get("client_mention_rate", 0.0)
    competitors = gap_data.get("competitor_data", [])

    if not competitors:
        return {
            "query": gap_data["query"],
            "competitive_gap": 0.0,
            "top_competitor": None,
            "client_mention_rate": client_rate,
            "competitor_mention_rate": 0.0,
        }

    max_comp = max(competitors, key=lambda c: c.get("mention_rate", 0))
    comp_rate = max_comp.get("mention_rate", 0.0)
    gap = round(comp_rate - client_rate, 4)

    return {
        "query": gap_data["query"],
        "competitive_gap": gap,
        "top_competitor": max_comp["name"],
        "client_mention_rate": client_rate,
        "competitor_mention_rate": comp_rate,
    }


def check_competitive_gaps(
    matches: list[dict],
    gap_data_list: list[dict],
) -> list[dict]:
    """For each matched/content_gap query, look up its competitive gap.

    Args:
        matches: List of query-page match results from Step 3.
        gap_data_list: Competitive gap data from the tracker (Phase 2).

    Returns:
        List of gap results, one per query in matches.
    """
    gap_by_query = {g["query"]: g for g in gap_data_list}

    results = []
    for match in matches:
        query = match["query"]
        gap_data = gap_by_query.get(query)

        if gap_data:
            result = compute_gap_for_query(gap_data)
            result["query_id"] = match.get("query_id", "")
        else:
            result = {
                "query": query,
                "query_id": match.get("query_id", ""),
                "competitive_gap": 0.0,
                "top_competitor": None,
                "client_mention_rate": 0.0,
                "competitor_mention_rate": 0.0,
            }

        results.append(result)

    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents && python -m pytest tests/test_gap_check.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/src/improvement/gap_check.py agents/tests/test_gap_check.py
git commit -m "feat: add competitive gap check (Step 5) — gap computation from tracker data"
```

---

## Task 8: Step 5b — Reddit Scout (Google Proxy)

**Files:**
- Create: `agents/src/improvement/reddit_scout.py`
- Create: `agents/tests/test_reddit_scout_v2.py`

- [ ] **Step 1: Write the failing tests**

```python
# agents/tests/test_reddit_scout_v2.py
from src.improvement.reddit_scout import (
    parse_google_results,
    detect_brand_mentions,
    build_scout_result,
)


SAMPLE_GOOGLE_HTML = """
<html><body>
<div class="g">
    <a href="https://www.reddit.com/r/personalfinance/comments/abc123/best_budgeting_tools/"><h3>Best budgeting tools for students - Reddit</h3></a>
    <div class="VwiC3b">Looking for recommendations on budgeting apps. CompetitorA seems popular but wondering about alternatives like BrandX.</div>
</div>
<div class="g">
    <a href="https://www.reddit.com/r/FinancialPlanning/comments/def456/mint_vs_ynab/"><h3>Mint vs YNAB for college students</h3></a>
    <div class="VwiC3b">Has anyone compared Mint and YNAB? I heard CompetitorA is better for students.</div>
</div>
<div class="g">
    <a href="https://www.reddit.com/r/budgeting/comments/ghi789/free_budget_apps/"><h3>Free budget apps recommendation thread</h3></a>
    <div class="VwiC3b">What free budgeting apps do you recommend? I tried BrandX and it was decent.</div>
</div>
</body></html>
"""


class TestParseGoogleResults:
    def test_extracts_reddit_threads(self):
        threads = parse_google_results(SAMPLE_GOOGLE_HTML)
        assert len(threads) >= 2
        assert all("url" in t for t in threads)
        assert all("title" in t for t in threads)
        assert all("reddit.com" in t["url"] for t in threads)

    def test_empty_html_returns_empty(self):
        threads = parse_google_results("<html><body></body></html>")
        assert threads == []


class TestDetectBrandMentions:
    def test_detects_client_mention(self):
        threads = [
            {"title": "Best tools", "url": "https://reddit.com/r/test/1", "snippet": "BrandX is great"},
        ]
        result = detect_brand_mentions(threads, "BrandX", ["CompA", "CompB"])
        assert result["client_mentioned"] is True

    def test_detects_competitor_mentions(self):
        threads = [
            {"title": "Best tools - CompA review", "url": "https://reddit.com/r/test/1", "snippet": "CompA and CompB are popular"},
        ]
        result = detect_brand_mentions(threads, "BrandX", ["CompA", "CompB"])
        assert "CompA" in result["competitors_mentioned"]
        assert "CompB" in result["competitors_mentioned"]

    def test_no_mentions(self):
        threads = [
            {"title": "Random topic", "url": "https://reddit.com/r/test/1", "snippet": "Nothing relevant"},
        ]
        result = detect_brand_mentions(threads, "BrandX", ["CompA"])
        assert result["client_mentioned"] is False
        assert result["competitors_mentioned"] == []


class TestBuildScoutResult:
    def test_complete_result_structure(self):
        threads = [
            {"title": "Thread 1", "url": "https://reddit.com/1", "snippet": "text"},
            {"title": "Thread 2", "url": "https://reddit.com/2", "snippet": "text"},
        ]
        result = build_scout_result("best tools", threads, True, ["CompA"])
        assert result["query"] == "best tools"
        assert result["threads_found"] == 2
        assert result["client_mentioned"] is True
        assert "CompA" in result["competitors_mentioned"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd agents && python -m pytest tests/test_reddit_scout_v2.py -v`
Expected: FAIL

- [ ] **Step 3: Implement Reddit scout (Google proxy)**

```python
# agents/src/improvement/reddit_scout.py
import time
from urllib.parse import quote_plus
import httpx
from bs4 import BeautifulSoup

GOOGLE_SEARCH_URL = "https://www.google.com/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def parse_google_results(html: str) -> list[dict]:
    """Parse Google search results HTML for Reddit thread links."""
    soup = BeautifulSoup(html, "html.parser")
    threads = []

    for result_div in soup.find_all("div", class_="g"):
        link = result_div.find("a", href=True)
        if not link or "reddit.com" not in link["href"]:
            continue

        title_el = link.find("h3")
        title = title_el.get_text(strip=True) if title_el else ""

        snippet_el = result_div.find("div", class_="VwiC3b") or result_div.find("span", class_="aCOpRe")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""

        if not snippet:
            for span in result_div.find_all("span"):
                text = span.get_text(strip=True)
                if len(text) > 40:
                    snippet = text
                    break

        threads.append({
            "title": title,
            "url": link["href"],
            "snippet": snippet[:300],
        })

    return threads[:5]


def detect_brand_mentions(
    threads: list[dict],
    client_brand: str,
    competitors: list[str],
) -> dict:
    """Check if client or competitors are mentioned in thread titles/snippets."""
    all_text = " ".join(t["title"] + " " + t["snippet"] for t in threads).lower()
    client_lower = client_brand.lower()

    client_mentioned = client_lower in all_text
    competitors_mentioned = [c for c in competitors if c.lower() in all_text]

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
    """Build the final scout result dict."""
    return {
        "query": query,
        "threads_found": len(threads),
        "threads": threads,
        "client_mentioned": client_mentioned,
        "competitors_mentioned": competitors_mentioned,
    }


def scout_reddit_for_query(
    query: str,
    client_brand: str,
    competitors: list[str],
) -> dict:
    """Search Google for Reddit threads about a query. Returns scout result."""
    search_query = f'site:reddit.com "{query}"'
    params = {"q": search_query, "num": 5}

    try:
        resp = httpx.get(GOOGLE_SEARCH_URL, params=params, headers=HEADERS,
                         timeout=10, follow_redirects=True)
        if resp.status_code != 200:
            print(f"  Reddit scout: Google returned {resp.status_code} for '{query}'")
            return build_scout_result(query, [], False, [])

        threads = parse_google_results(resp.text)
        mentions = detect_brand_mentions(threads, client_brand, competitors)

        return build_scout_result(
            query, threads,
            mentions["client_mentioned"],
            mentions["competitors_mentioned"],
        )
    except Exception as e:
        print(f"  Reddit scout failed for '{query}': {e}")
        return build_scout_result(query, [], False, [])


def run_reddit_scout(
    gap_queries: list[dict],
    client_brand: str,
    competitors: list[str],
) -> list[dict]:
    """Run Reddit scout for all queries with competitive gaps.

    Args:
        gap_queries: List of dicts with 'query' key where competitive_gap > 0.
        client_brand: The client's brand name.
        competitors: List of competitor names.

    Returns:
        List of scout result dicts.
    """
    results = []

    for gap in gap_queries:
        query = gap["query"]
        print(f"  Reddit scout: {query}")
        result = scout_reddit_for_query(query, client_brand, competitors)
        results.append(result)
        time.sleep(2)

    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents && python -m pytest tests/test_reddit_scout_v2.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/src/improvement/reddit_scout.py agents/tests/test_reddit_scout_v2.py
git commit -m "feat: add Reddit scout via Google proxy (Step 5b) — thread discovery and brand detection"
```

---

## Task 9: Step 6 — Action Card Generator

**Files:**
- Create: `agents/src/improvement/card_generator.py`
- Create: `agents/tests/test_card_generator.py`

- [ ] **Step 1: Write the failing tests**

```python
# agents/tests/test_card_generator.py
from src.improvement.card_generator import (
    classify_actions,
    build_content_brief,
    prioritize_cards,
)


class TestClassifyActions:
    def test_missing_faq_schema(self):
        score_result = {
            "structural_score": 60,
            "check_results": {
                "faq_schema": {"score": 0, "has_faq": False},
                "answer_first": {"score": 15, "has_declarative_opening": True},
                "source_citations": {"score": 8, "external_count": 5},
                "freshness": {"score": 10, "age_days": 30},
                "schema_validation": {"score": 5, "schema_status": "valid_incomplete"},
                "comparison_tables": {"score": 10, "table_count": 1},
                "lists": {"score": 10, "list_count": 3},
                "word_count": {"score": 10, "word_count": 2500},
                "author_attribution": {"score": 7, "has_author": True},
            },
            "schema_status": "valid_incomplete",
        }
        actions = classify_actions(score_result, "https://example.com/page")
        action_types = [a["action_type"] for a in actions]
        assert "add_faq_schema" in action_types

    def test_not_answer_first(self):
        score_result = {
            "structural_score": 50,
            "check_results": {
                "faq_schema": {"score": 10, "has_faq": True},
                "answer_first": {"score": 0, "has_declarative_opening": False},
                "source_citations": {"score": 8, "external_count": 5},
                "freshness": {"score": 10, "age_days": 30},
                "schema_validation": {"score": 15, "schema_status": "valid_complete"},
                "comparison_tables": {"score": 10, "table_count": 1},
                "lists": {"score": 10, "list_count": 3},
                "word_count": {"score": 10, "word_count": 2500},
                "author_attribution": {"score": 7, "has_author": True},
            },
            "schema_status": "valid_complete",
        }
        actions = classify_actions(score_result, "https://example.com/page")
        action_types = [a["action_type"] for a in actions]
        assert "restructure_intro" in action_types

    def test_no_citations(self):
        score_result = {
            "structural_score": 40,
            "check_results": {
                "faq_schema": {"score": 10, "has_faq": True},
                "answer_first": {"score": 15, "has_declarative_opening": True},
                "source_citations": {"score": 0, "external_count": 0},
                "freshness": {"score": 10, "age_days": 30},
                "schema_validation": {"score": 15, "schema_status": "valid_complete"},
                "comparison_tables": {"score": 10, "table_count": 1},
                "lists": {"score": 10, "list_count": 3},
                "word_count": {"score": 10, "word_count": 2500},
                "author_attribution": {"score": 7, "has_author": True},
            },
            "schema_status": "valid_complete",
        }
        actions = classify_actions(score_result, "https://example.com/page")
        action_types = [a["action_type"] for a in actions]
        assert "add_citations" in action_types

    def test_stale_content(self):
        score_result = {
            "structural_score": 70,
            "check_results": {
                "faq_schema": {"score": 10, "has_faq": True},
                "answer_first": {"score": 15, "has_declarative_opening": True},
                "source_citations": {"score": 8, "external_count": 5},
                "freshness": {"score": 1, "age_days": 400},
                "schema_validation": {"score": 15, "schema_status": "valid_complete"},
                "comparison_tables": {"score": 10, "table_count": 1},
                "lists": {"score": 10, "list_count": 3},
                "word_count": {"score": 10, "word_count": 2500},
                "author_attribution": {"score": 7, "has_author": True},
            },
            "schema_status": "valid_complete",
        }
        actions = classify_actions(score_result, "https://example.com/page")
        action_types = [a["action_type"] for a in actions]
        assert "update_freshness" in action_types

    def test_missing_schema(self):
        score_result = {
            "structural_score": 30,
            "check_results": {
                "faq_schema": {"score": 0, "has_faq": False},
                "answer_first": {"score": 15, "has_declarative_opening": True},
                "source_citations": {"score": 8, "external_count": 5},
                "freshness": {"score": 10, "age_days": 30},
                "schema_validation": {"score": 0, "schema_status": "missing"},
                "comparison_tables": {"score": 10, "table_count": 1},
                "lists": {"score": 10, "list_count": 3},
                "word_count": {"score": 10, "word_count": 2500},
                "author_attribution": {"score": 7, "has_author": True},
            },
            "schema_status": "missing",
        }
        actions = classify_actions(score_result, "https://example.com/page")
        action_types = [a["action_type"] for a in actions]
        assert "generate_schema" in action_types

    def test_perfect_score_no_actions(self):
        score_result = {
            "structural_score": 100,
            "check_results": {
                "faq_schema": {"score": 10, "has_faq": True},
                "answer_first": {"score": 15, "has_declarative_opening": True},
                "source_citations": {"score": 10, "external_count": 6},
                "freshness": {"score": 10, "age_days": 30},
                "schema_validation": {"score": 15, "schema_status": "valid_complete"},
                "comparison_tables": {"score": 10, "table_count": 1},
                "lists": {"score": 10, "list_count": 3},
                "word_count": {"score": 10, "word_count": 2500},
                "author_attribution": {"score": 10, "has_author": True},
            },
            "schema_status": "valid_complete",
        }
        actions = classify_actions(score_result, "https://example.com/page")
        assert len(actions) == 0


class TestBuildContentBrief:
    def test_returns_brief_structure(self):
        brief = build_content_brief(
            query="best budgeting tools for med students",
            query_id="q1",
            competitive_gap=0.4,
            top_competitor="CompA",
        )
        assert brief["action_type"] == "content_brief"
        assert brief["track"] == "manual"
        assert brief["priority"] == 2
        assert brief["brief"]["target_query"] == "best budgeting tools for med students"
        assert brief["competitive_gap"] == 0.4

    def test_brief_has_required_fields(self):
        brief = build_content_brief(
            query="test query",
            query_id="q1",
            competitive_gap=0.2,
            top_competitor="CompB",
        )
        required_keys = ["target_query", "recommended_title", "recommended_h1",
                         "key_sections", "schema_type", "word_count_target"]
        for key in required_keys:
            assert key in brief["brief"], f"Missing key: {key}"


class TestPrioritizeCards:
    def test_competitive_gap_pages_first(self):
        cards = [
            {"action_type": "add_faq_schema", "priority": 3, "competitive_gap": None},
            {"action_type": "restructure_intro", "priority": 1, "competitive_gap": 0.4},
            {"action_type": "content_brief", "priority": 2, "competitive_gap": 0.6},
        ]
        sorted_cards = prioritize_cards(cards)
        assert sorted_cards[0]["priority"] == 1
        assert sorted_cards[-1]["priority"] == 3

    def test_within_same_priority_sort_by_gap(self):
        cards = [
            {"action_type": "a", "priority": 1, "competitive_gap": 0.2},
            {"action_type": "b", "priority": 1, "competitive_gap": 0.8},
        ]
        sorted_cards = prioritize_cards(cards)
        assert sorted_cards[0]["competitive_gap"] == 0.8
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd agents && python -m pytest tests/test_card_generator.py -v`
Expected: FAIL

- [ ] **Step 3: Implement card generator**

```python
# agents/src/improvement/card_generator.py
import os
import json
import anthropic

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def classify_actions(score_result: dict, page_url: str) -> list[dict]:
    """Rule-based classification of what actions a page needs.

    Returns list of action dicts with action_type and issue description.
    """
    actions = []
    checks = score_result["check_results"]

    if checks["answer_first"]["score"] == 0:
        actions.append({
            "action_type": "restructure_intro",
            "page_url": page_url,
            "issue": checks["answer_first"].get("detail", "Opening paragraph lacks a direct declarative answer"),
        })

    if not checks["faq_schema"].get("has_faq", False):
        actions.append({
            "action_type": "add_faq_schema",
            "page_url": page_url,
            "issue": "No FAQPage schema found — adding FAQ schema improves AI crawler comprehension",
        })

    if checks["source_citations"].get("external_count", 0) == 0:
        actions.append({
            "action_type": "add_citations",
            "page_url": page_url,
            "issue": "No external source citations — pages with 3+ citations are 2.8x more likely to be cited by AI",
        })

    freshness_score = checks["freshness"].get("score", 0)
    if freshness_score <= 3:
        age = checks["freshness"].get("age_days")
        detail = f"Content is {age} days old" if age else "No modification date found"
        actions.append({
            "action_type": "update_freshness",
            "page_url": page_url,
            "issue": f"{detail} — citation rates drop sharply after 3 months",
        })

    schema_status = score_result.get("schema_status", "missing")
    if schema_status == "missing":
        actions.append({
            "action_type": "generate_schema",
            "page_url": page_url,
            "issue": "No JSON-LD schema markup found — 78% of sites with deployed schema are silently broken; starting clean is better",
        })
    elif schema_status == "broken":
        errors = score_result.get("schema_errors", [])
        actions.append({
            "action_type": "fix_schema",
            "page_url": page_url,
            "issue": f"Schema has errors: {'; '.join(errors[:3])}",
        })

    return actions


def build_content_brief(
    query: str,
    query_id: str,
    competitive_gap: float,
    top_competitor: str | None,
) -> dict:
    """Build a manual-track content brief card for a content gap."""
    return {
        "query_id": query_id,
        "page_url": None,
        "action_type": "content_brief",
        "track": "manual",
        "priority": 2,
        "competitive_gap": competitive_gap,
        "issue": f"No page exists for query '{query}'" + (f" — {top_competitor} has {competitive_gap:.0%} mention rate advantage" if top_competitor else ""),
        "brief": {
            "target_query": query,
            "competitive_landscape": f"{top_competitor} currently dominates this query" if top_competitor else "No dominant competitor",
            "recommended_title": f"{query.title()} — Complete Guide",
            "recommended_h1": query.title(),
            "key_sections": [
                "Direct answer to the query in the opening paragraph",
                "Comparison of top options (table format)",
                "Detailed analysis with statistics and sources",
                "FAQ section addressing related questions",
            ],
            "facts_to_include": [
                "Industry statistics from authoritative sources (.gov, .edu, .org)",
                "Comparison data between options",
            ],
            "schema_type": "Article",
            "internal_link_targets": [],
            "word_count_target": 2000,
        },
        "status": "pending",
        "cms_action": "none",
    }


def build_reddit_card(query: str, scout_data: dict) -> dict:
    """Build a manual-track Reddit engagement card."""
    return {
        "page_url": None,
        "action_type": "reddit_engagement",
        "track": "manual",
        "priority": 2,
        "competitive_gap": None,
        "issue": f"{scout_data['threads_found']} Reddit threads found for '{query}' — competitors present in {len(scout_data.get('competitors_mentioned', []))} thread(s)",
        "reddit_data": {
            "threads": scout_data.get("threads", []),
            "competitors_present": scout_data.get("competitors_mentioned", []),
        },
        "status": "pending",
        "cms_action": "none",
    }


def generate_sonnet_specifics(
    page_content: str,
    query: str,
    action_type: str,
    issue: str,
    competitive_gap_info: str,
) -> dict:
    """Call Sonnet to generate specific before/after text for an action card.

    Returns dict with before_text, after_text, code_block.
    """
    prompt = f"""You are a GEO (Generative Engine Optimization) specialist. Generate a specific, actionable fix.

ACTION TYPE: {action_type}
ISSUE: {issue}
TARGET QUERY: {query}
COMPETITIVE CONTEXT: {competitive_gap_info}

PAGE CONTENT (first 3000 chars):
{page_content[:3000]}

Return ONLY valid JSON with these fields:
{{
    "before_text": "The exact current text that needs to change (quote from page content above, or 'none' if adding new content)",
    "after_text": "The exact replacement text — specific, complete, ready to paste",
    "code_block": "For schema/meta changes: the full JSON-LD or meta tag. Empty string otherwise."
}}

Rules:
- For restructure_intro: rewrite the opening paragraph with a direct declarative answer to the target query in the first sentence
- For add_faq_schema: generate a complete FAQPage JSON-LD block with 3-5 Q&A pairs relevant to the page content
- For add_citations: suggest 3 specific sentences that should include source citations with example authoritative URLs
- For generate_schema: generate Organization + Article/FAQPage JSON-LD appropriate for the page
- For fix_schema: provide the corrected JSON-LD block
- For update_freshness: provide updated meta tag with today's date
- All schema output must include @context and valid @type"""

    try:
        response = _get_client().messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                return {"before_text": "", "after_text": "", "code_block": ""}

        return {
            "before_text": data.get("before_text", ""),
            "after_text": data.get("after_text", ""),
            "code_block": data.get("code_block", ""),
        }
    except Exception as e:
        print(f"  Sonnet card generation failed: {e}")
        return {"before_text": "", "after_text": "", "code_block": ""}


def generate_sonnet_quality(page_content: str, query: str, check_results: dict) -> dict:
    """Call Sonnet for quality judgment on a matched page."""
    checks_summary = "\n".join(f"- {k}: {v.get('detail', 'N/A')}" for k, v in check_results.items())

    prompt = f"""You are a GEO specialist. Judge how well this page answers the query for AI citation.

TARGET QUERY: {query}
STRUCTURAL CHECK RESULTS:
{checks_summary}

PAGE CONTENT (first 3000 chars):
{page_content[:3000]}

Return ONLY valid JSON:
{{
    "specificity": 1-5,
    "completeness": 1-5,
    "answer_directness": 1-5,
    "summary": "One sentence assessment"
}}

Scoring guide:
- specificity: Does the content address the exact query topic with specific details, not generic advice?
- completeness: Does the content cover all major aspects someone asking this query would want to know?
- answer_directness: Can an AI extract a clear, citable answer from the first few paragraphs?"""

    try:
        response = _get_client().messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                return {"specificity": 0, "completeness": 0, "answer_directness": 0, "summary": "Sonnet call failed"}

        return {
            "specificity": data.get("specificity", 0),
            "completeness": data.get("completeness", 0),
            "answer_directness": data.get("answer_directness", 0),
            "summary": data.get("summary", ""),
        }
    except Exception as e:
        print(f"  Sonnet quality scoring failed: {e}")
        return {"specificity": 0, "completeness": 0, "answer_directness": 0, "summary": str(e)}


def prioritize_cards(cards: list[dict]) -> list[dict]:
    """Sort cards by priority (1 first), then by competitive gap (largest first)."""
    return sorted(
        cards,
        key=lambda c: (c.get("priority", 3), -(c.get("competitive_gap") or 0)),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents && python -m pytest tests/test_card_generator.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/src/improvement/card_generator.py agents/tests/test_card_generator.py
git commit -m "feat: add action card generator (Step 6) — rule-based classification + Sonnet specifics"
```

---

## Task 10: Pipeline Orchestrator

**Files:**
- Create: `agents/src/improvement/pipeline.py`
- Create: `agents/tests/test_improvement_pipeline.py`

- [ ] **Step 1: Write the failing tests**

```python
# agents/tests/test_improvement_pipeline.py
from unittest.mock import patch, MagicMock
from src.improvement.pipeline import run_improvement_pipeline


class TestRunImprovementPipeline:
    @patch("src.improvement.pipeline._get_supabase")
    @patch("src.improvement.pipeline.run_crawlability_gate")
    @patch("src.improvement.pipeline.build_inventory")
    @patch("src.improvement.pipeline.match_queries_to_pages")
    @patch("src.improvement.pipeline.compute_structural_score")
    @patch("src.improvement.pipeline.generate_sonnet_quality")
    @patch("src.improvement.pipeline.check_competitive_gaps")
    @patch("src.improvement.pipeline.run_reddit_scout")
    @patch("src.improvement.pipeline.classify_actions")
    @patch("src.improvement.pipeline.generate_sonnet_specifics")
    @patch("src.improvement.pipeline.validate_json_ld")
    def test_returns_expected_state_keys(
        self, mock_validate, mock_sonnet, mock_classify, mock_reddit,
        mock_gaps, mock_quality, mock_score, mock_match, mock_inv,
        mock_crawl, mock_sb,
    ):
        mock_sb.return_value = MagicMock()
        mock_sb.return_value.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "run-123"}])
        mock_sb.return_value.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        mock_crawl.return_value = {"has_critical_blocker": False, "robots_txt": {"status": "pass"}}
        mock_inv.return_value = [
            {"url": "https://x.com/p1", "title": "Page 1", "h1": "H1", "first_paragraph": "text", "raw_html": "<html></html>", "last_modified": None, "word_count": 500, "outbound_link_count": 0, "has_faq_schema": False, "has_comparison_table": False, "schema_types": []},
        ]
        mock_match.return_value = [
            {"query": "q1", "query_id": "id1", "match_type": "matched", "matched_page_url": "https://x.com/p1", "similarity_score": 0.7, "bucket": "awareness"},
        ]
        mock_score.return_value = {"structural_score": 60, "check_results": {}, "schema_status": "missing", "schema_errors": []}
        mock_quality.return_value = {"specificity": 3, "completeness": 3, "answer_directness": 3, "summary": "OK"}
        mock_gaps.return_value = [{"query": "q1", "query_id": "id1", "competitive_gap": 0.2, "top_competitor": "CompA", "client_mention_rate": 0.3, "competitor_mention_rate": 0.5}]
        mock_reddit.return_value = []
        mock_classify.return_value = [{"action_type": "generate_schema", "page_url": "https://x.com/p1", "issue": "No schema"}]
        mock_sonnet.return_value = {"before_text": "", "after_text": "", "code_block": '{"@context":"https://schema.org","@type":"Organization","name":"X"}'}
        mock_validate.return_value = {"valid": True, "errors": []}

        state = {
            "client_id": "client-1",
            "client_config": {
                "website_domain": "x.com",
                "brand_name": "BrandX",
                "competitors": ["CompA"],
                "target_queries": ["q1"],
            },
            "tracker_results": [],
        }
        queries = [{"id": "id1", "prompt_text": "q1", "bucket": "awareness"}]

        result = run_improvement_pipeline(state, queries, competitive_gaps_data=[
            {"query": "q1", "client_mention_rate": 0.3, "competitor_data": [{"name": "CompA", "mention_rate": 0.5}]}
        ])

        assert "improvement_run_id" in result
        assert "crawlability_report" in result
        assert "page_inventory" in result
        assert "query_matches" in result
        assert "citation_scores" in result
        assert "action_cards" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd agents && python -m pytest tests/test_improvement_pipeline.py -v`
Expected: FAIL

- [ ] **Step 3: Implement pipeline orchestrator**

```python
# agents/src/improvement/pipeline.py
import os
from datetime import datetime, timezone

from src.improvement.crawlability import run_crawlability_gate
from src.improvement.inventory import build_inventory, extract_page_data
from src.improvement.matcher import match_queries_to_pages
from src.improvement.scorer import compute_structural_score
from src.improvement.gap_check import check_competitive_gaps
from src.improvement.reddit_scout import run_reddit_scout
from src.improvement.card_generator import (
    classify_actions,
    build_content_brief,
    build_reddit_card,
    generate_sonnet_specifics,
    generate_sonnet_quality,
    prioritize_cards,
)
from src.improvement.validators import validate_json_ld


def _get_supabase():
    from supabase import create_client
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def run_improvement_pipeline(
    state: dict,
    queries: list[dict],
    competitive_gaps_data: list[dict] | None = None,
) -> dict:
    """Run the full improvement pipeline (Steps 1-6).

    Args:
        state: GEOState dict with client_id, client_config, tracker_results.
        queries: List of active query dicts from the queries table.
        competitive_gaps_data: Pre-computed competitive gap data from the tracker.

    Returns:
        Dict with all pipeline outputs to merge into GEOState.
    """
    config = state["client_config"]
    domain = config["website_domain"]
    client_id = state["client_id"]
    brand_name = config.get("brand_name", "")
    competitors = config.get("competitors", [])

    sb = _get_supabase()

    # Create improvement run record
    run_resp = sb.table("improvement_runs").insert({
        "client_id": client_id,
        "status": "running",
    }).execute()
    run_id = run_resp.data[0]["id"]

    try:
        # Step 1: Crawlability Gate
        print("  Step 1: Crawlability gate...")
        crawl_report = run_crawlability_gate(domain)

        # Step 2: Site Inventory
        print("  Step 2: Site inventory...")
        inventory = build_inventory(domain, max_pages=config.get("audit_max_pages", 20))

        # Persist inventory to DB (without raw_html)
        if inventory:
            inv_rows = [{
                "run_id": run_id,
                "url": p["url"],
                "title": p["title"],
                "h1": p["h1"],
                "first_paragraph": p["first_paragraph"],
                "schema_types": p["schema_types"],
                "word_count": p["word_count"],
                "last_modified": p.get("last_modified"),
                "outbound_link_count": p["outbound_link_count"],
                "has_faq_schema": p["has_faq_schema"],
                "has_comparison_table": p["has_comparison_table"],
            } for p in inventory]
            sb.table("page_inventory").insert(inv_rows).execute()

        # Step 3: Query-Page Matching
        print("  Step 3: Query-page matching...")
        query_dicts = [{"query": q["prompt_text"], "query_id": q["id"], "bucket": q.get("bucket", "")} for q in queries]
        matches = match_queries_to_pages(inventory, query_dicts)

        # Persist matches to DB
        if matches:
            match_rows = [{
                "run_id": run_id,
                "query_id": m["query_id"],
                "query_text": m["query"],
                "match_type": m["match_type"],
                "matched_page_url": m.get("matched_page_url"),
                "similarity_score": m["similarity_score"],
                "bucket": m.get("bucket"),
            } for m in matches]
            sb.table("query_page_matches").insert(match_rows).execute()

        # Step 4: Citation-Readiness Scoring (matched pages only)
        print("  Step 4: Citation-readiness scoring...")
        matched_pages = {m["matched_page_url"] for m in matches if m["match_type"] == "matched" and m["matched_page_url"]}
        page_by_url = {p["url"]: p for p in inventory}

        citation_scores = []
        for page_url in matched_pages:
            page = page_by_url.get(page_url)
            if not page:
                continue

            score_result = compute_structural_score(
                page.get("raw_html", ""),
                domain,
                page.get("last_modified"),
            )

            # Sonnet quality judgment
            matched_queries = [m["query"] for m in matches if m["matched_page_url"] == page_url]
            query_text = matched_queries[0] if matched_queries else ""
            sonnet_quality = generate_sonnet_quality(
                page.get("raw_html", "")[:3000],
                query_text,
                score_result["check_results"],
            )

            score_entry = {
                "url": page_url,
                **score_result,
                "sonnet_quality": sonnet_quality,
            }
            citation_scores.append(score_entry)

            # Persist to DB
            sb.table("page_citation_scores").insert({
                "run_id": run_id,
                "page_url": page_url,
                "structural_score": score_result["structural_score"],
                "check_results": score_result["check_results"],
                "sonnet_quality": sonnet_quality,
                "schema_status": score_result["schema_status"],
                "schema_errors": score_result.get("schema_errors", []),
            }).execute()

        # Step 5: Competitive Gap Check
        print("  Step 5: Competitive gap check...")
        gap_results = check_competitive_gaps(matches, competitive_gaps_data or [])

        # Step 5b: Reddit Scout (gap queries only)
        print("  Step 5b: Reddit scout...")
        gap_queries = [g for g in gap_results if g["competitive_gap"] > 0]
        reddit_data = run_reddit_scout(gap_queries, brand_name, competitors) if gap_queries else []

        # Step 6: Action Card Generation
        print("  Step 6: Generating action cards...")
        all_cards = []
        score_by_url = {s["url"]: s for s in citation_scores}

        # Track 1: Automated cards for matched pages
        for match in matches:
            if match["match_type"] != "matched" or not match["matched_page_url"]:
                continue

            page_url = match["matched_page_url"]
            score = score_by_url.get(page_url)
            if not score:
                continue

            gap_info = next((g for g in gap_results if g["query"] == match["query"]), None)
            has_gap = gap_info and gap_info["competitive_gap"] > 0

            actions = classify_actions(score, page_url)
            page = page_by_url.get(page_url, {})

            for action in actions:
                gap_text = f"Competitor {gap_info['top_competitor']} has {gap_info['competitive_gap']:.0%} advantage" if has_gap and gap_info else "No competitive gap"

                specifics = generate_sonnet_specifics(
                    page.get("raw_html", "")[:3000],
                    match["query"],
                    action["action_type"],
                    action["issue"],
                    gap_text,
                )

                # Validate schema output
                validation_passed = True
                if action["action_type"] in ("generate_schema", "fix_schema", "add_faq_schema") and specifics.get("code_block"):
                    validation = validate_json_ld(specifics["code_block"])
                    validation_passed = validation["valid"]
                    if not validation_passed:
                        print(f"    Schema validation failed for {action['action_type']}: {validation['errors']}")
                        continue

                card = {
                    "run_id": run_id,
                    "client_id": client_id,
                    "query_id": match.get("query_id"),
                    "page_url": page_url,
                    "pillar": action["action_type"],
                    "action_type": action["action_type"],
                    "track": "automated",
                    "priority": 1 if has_gap else 3,
                    "competitive_gap": gap_info["competitive_gap"] if gap_info else None,
                    "structural_score": score["structural_score"],
                    "score": score["structural_score"],
                    "issue": action["issue"],
                    "before_text": specifics.get("before_text", ""),
                    "after_text": specifics.get("after_text", ""),
                    "code_block": specifics.get("code_block", ""),
                    "validation_passed": validation_passed,
                    "status": "pending",
                    "cms_action": "copy_paste",
                }
                all_cards.append(card)

        # Track 2: Content brief cards for content gaps
        for match in matches:
            if match["match_type"] != "content_gap":
                continue

            gap_info = next((g for g in gap_results if g["query"] == match["query"]), None)
            if gap_info and gap_info["competitive_gap"] > 0:
                brief = build_content_brief(
                    query=match["query"],
                    query_id=match["query_id"],
                    competitive_gap=gap_info["competitive_gap"],
                    top_competitor=gap_info["top_competitor"],
                )
                brief["run_id"] = run_id
                brief["client_id"] = client_id
                brief["pillar"] = "content_gap"
                brief["score"] = 0
                brief["before_text"] = ""
                brief["after_text"] = ""
                brief["code_block"] = ""
                brief["validation_passed"] = True
                all_cards.append(brief)

        # Track 2: Reddit engagement cards
        reddit_by_query = {r["query"]: r for r in reddit_data}
        for gap in gap_queries:
            scout = reddit_by_query.get(gap["query"])
            if scout and scout["threads_found"] > 0:
                reddit_card = build_reddit_card(gap["query"], scout)
                reddit_card["run_id"] = run_id
                reddit_card["client_id"] = client_id
                reddit_card["query_id"] = gap.get("query_id")
                reddit_card["pillar"] = "reddit"
                reddit_card["score"] = 0
                reddit_card["before_text"] = ""
                reddit_card["after_text"] = ""
                reddit_card["code_block"] = ""
                reddit_card["validation_passed"] = True
                all_cards.append(reddit_card)

        # Prioritize and persist
        all_cards = prioritize_cards(all_cards)

        if all_cards:
            card_rows = [{k: v for k, v in c.items() if k != "brief" and k != "reddit_data"} for c in all_cards]
            for row in card_rows:
                brief_data = next((c.get("brief") for c in all_cards if c.get("run_id") == row["run_id"] and c.get("action_type") == row.get("action_type") and c.get("query_id") == row.get("query_id")), None)
                if brief_data:
                    row["brief"] = brief_data
                reddit = next((c.get("reddit_data") for c in all_cards if c.get("run_id") == row["run_id"] and c.get("action_type") == row.get("action_type") and c.get("query_id") == row.get("query_id")), None)
                if reddit:
                    row["reddit_data"] = reddit
            sb.table("action_cards").insert(card_rows).execute()

        # Update run record
        content_gaps = sum(1 for m in matches if m["match_type"] == "content_gap")
        comp_gaps = sum(1 for g in gap_results if g["competitive_gap"] > 0)

        sb.table("improvement_runs").update({
            "status": "completed",
            "crawlability_report": crawl_report,
            "pages_inventoried": len(inventory),
            "queries_matched": sum(1 for m in matches if m["match_type"] == "matched"),
            "content_gaps_found": content_gaps,
            "competitive_gaps_found": comp_gaps,
            "cards_generated": len(all_cards),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", run_id).execute()

        print(f"  Pipeline complete: {len(inventory)} pages, {len(matches)} matches, {len(all_cards)} cards")

        return {
            "improvement_run_id": run_id,
            "crawlability_report": crawl_report,
            "page_inventory": [{k: v for k, v in p.items() if k != "raw_html"} for p in inventory],
            "query_matches": matches,
            "citation_scores": citation_scores,
            "competitive_gap_data": gap_results,
            "reddit_scout_data": reddit_data,
            "action_cards": all_cards,
        }

    except Exception as e:
        sb.table("improvement_runs").update({
            "status": "error",
            "error_message": str(e)[:500],
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", run_id).execute()
        raise
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents && python -m pytest tests/test_improvement_pipeline.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/src/improvement/pipeline.py agents/tests/test_improvement_pipeline.py
git commit -m "feat: add improvement pipeline orchestrator — runs Steps 1-6 sequentially"
```

---

## Task 11: Update GEOState, Pipeline Graph, and Nodes

**Files:**
- Modify: `agents/src/graph/state.py`
- Modify: `agents/src/graph/pipeline.py`
- Modify: `agents/src/graph/nodes.py`
- Modify: `agents/tests/test_pipeline.py`

- [ ] **Step 1: Update GEOState**

Replace the contents of `agents/src/graph/state.py`:

```python
# agents/src/graph/state.py
from typing import TypedDict


class GEOState(TypedDict):
    client_id: str
    client_config: dict
    tracker_results: list[dict]
    tracker_scores: dict
    gsc_metrics: dict
    run_type: str
    thread_id: str
    error: str | None

    # Improvement pipeline fields
    improvement_run_id: str | None
    crawlability_report: dict
    page_inventory: list[dict]
    query_matches: list[dict]
    citation_scores: list[dict]
    competitive_gap_data: list[dict]
    reddit_scout_data: list[dict]
    action_cards: list[dict]
    approved_card_ids: list[str]
    implementation_results: list[dict]
```

- [ ] **Step 2: Update pipeline graph**

Replace the contents of `agents/src/graph/pipeline.py`:

```python
# agents/src/graph/pipeline.py
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from src.graph.state import GEOState
from src.graph.nodes import (
    load_config,
    run_tracker_node,
    run_gsc_node,
    run_improvement_pipeline_node,
    await_approval,
    run_implementation_node,
)


def route_after_config(state: GEOState) -> str:
    if state.get("run_type") == "improvement_only":
        return "run_improvement_pipeline"
    return "run_tracker"


def route_after_gsc(state: GEOState) -> str:
    if state.get("run_type") == "tracker_only":
        return END
    return "run_improvement_pipeline"


def build_graph(checkpointer=None):
    graph = StateGraph(GEOState)

    graph.add_node("load_config", load_config)
    graph.add_node("run_tracker", run_tracker_node)
    graph.add_node("run_gsc", run_gsc_node)
    graph.add_node("run_improvement_pipeline", run_improvement_pipeline_node)
    graph.add_node("await_approval", await_approval)
    graph.add_node("run_implementation", run_implementation_node)

    graph.set_entry_point("load_config")

    graph.add_conditional_edges("load_config", route_after_config, {
        "run_tracker": "run_tracker",
        "run_improvement_pipeline": "run_improvement_pipeline",
    })

    graph.add_edge("run_tracker", "run_gsc")

    graph.add_conditional_edges("run_gsc", route_after_gsc, {
        END: END,
        "run_improvement_pipeline": "run_improvement_pipeline",
    })

    graph.add_edge("run_improvement_pipeline", "await_approval")
    graph.add_edge("await_approval", "run_implementation")
    graph.add_edge("run_implementation", END)

    if checkpointer is None:
        checkpointer = MemorySaver()

    return graph.compile(checkpointer=checkpointer)
```

- [ ] **Step 3: Add run_improvement_pipeline_node to nodes.py**

Add this function to `agents/src/graph/nodes.py` (after the existing `run_gsc_node` function, replacing `run_audit_node` and `run_recommender_node`). Remove the `run_audit_node` and `run_recommender_node` functions.

```python
def run_improvement_pipeline_node(state: GEOState) -> dict:
    from src.improvement.pipeline import run_improvement_pipeline
    sb = _get_supabase()

    # Load active queries
    queries_resp = sb.table("queries").select("*").eq("client_id", state["client_id"]).eq("status", "active").execute()
    queries = queries_resp.data or []

    # Load competitive gaps from latest tracker run
    competitive_gaps = []
    if state.get("tracker_results"):
        latest_run = sb.table("tracker_runs") \
            .select("id") \
            .eq("client_id", state["client_id"]) \
            .order("ran_at", desc=True) \
            .limit(1) \
            .execute()
        if latest_run.data:
            run_id = latest_run.data[0]["id"]
            gaps_resp = sb.table("competitive_gaps") \
                .select("*") \
                .eq("run_id", run_id) \
                .execute()
            competitive_gaps = gaps_resp.data or []

    try:
        result = run_improvement_pipeline(state, queries, competitive_gaps)
        return result
    except Exception as e:
        print(f"  Improvement pipeline failed: {e}")
        return {
            "improvement_run_id": None,
            "crawlability_report": {},
            "page_inventory": [],
            "query_matches": [],
            "citation_scores": [],
            "competitive_gap_data": [],
            "reddit_scout_data": [],
            "action_cards": [],
            "error": str(e),
        }
```

- [ ] **Step 4: Update test_pipeline.py**

Replace the contents of `agents/tests/test_pipeline.py`:

```python
from src.graph.pipeline import build_graph


def test_build_graph_returns_compiled_graph():
    graph = build_graph()
    assert graph is not None
    assert hasattr(graph, "invoke")


def test_build_graph_has_expected_nodes():
    graph = build_graph()
    node_names = set(graph.get_graph().nodes.keys())
    assert "load_config" in node_names
    assert "run_tracker" in node_names
    assert "run_improvement_pipeline" in node_names
    assert "await_approval" in node_names
    assert "run_implementation" in node_names
    assert "run_audit" not in node_names
    assert "run_recommender" not in node_names
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd agents && python -m pytest tests/test_pipeline.py -v`
Expected: All tests PASS

- [ ] **Step 6: Update server.py initial state**

In `agents/server.py`, update the initial state dict in both `trigger_scheduled_run` (line ~41) and `_run_graph_background` (line ~170) to include the new fields and remove the old ones. Replace:

```python
{
    "client_id": client_id,
    "run_type": run_type,  # or "full" for trigger_scheduled_run
    "thread_id": thread_id,
    "client_config": {},
    "tracker_results": [],
    "tracker_scores": {},
    "gsc_metrics": {},
    "audit_pages": [],
    "audit_summary": {},
    "audit_run_id": None,
    "action_cards": [],
    "approved_card_ids": [],
    "implementation_results": [],
    "reddit_posts": [],
    "error": None,
}
```

With:

```python
{
    "client_id": client_id,
    "run_type": run_type,  # or "full" for trigger_scheduled_run
    "thread_id": thread_id,
    "client_config": {},
    "tracker_results": [],
    "tracker_scores": {},
    "gsc_metrics": {},
    "improvement_run_id": None,
    "crawlability_report": {},
    "page_inventory": [],
    "query_matches": [],
    "citation_scores": [],
    "competitive_gap_data": [],
    "reddit_scout_data": [],
    "action_cards": [],
    "approved_card_ids": [],
    "implementation_results": [],
    "error": None,
}
```

- [ ] **Step 7: Commit**

```bash
git add agents/src/graph/state.py agents/src/graph/pipeline.py agents/src/graph/nodes.py agents/tests/test_pipeline.py agents/server.py
git commit -m "feat: wire improvement pipeline into LangGraph — replace audit/recommender nodes"
```

---

## Task 12: Schedule Visibility Endpoint

**Files:**
- Modify: `agents/server.py`
- Modify: `agents/tests/test_server.py`

- [ ] **Step 1: Add /api/schedules endpoint to server.py**

Add this endpoint after the existing `/api/reload-schedules` endpoint in `agents/server.py`:

```python
@app.get("/api/schedules")
async def get_schedules(authorization: str | None = Header(None)):
    verify_auth(authorization)
    sb = _get_supabase()

    # Get client names
    clients_resp = sb.table("clients").select("id, brand_name, cycle_frequency, cycle_day").execute()
    client_map = {c["id"]: c for c in clients_resp.data}

    # Get latest pipeline run per client
    runs_resp = sb.table("pipeline_runs").select("client_id, status, created_at").order("created_at", desc=True).execute()
    latest_runs = {}
    for run in runs_resp.data:
        cid = run["client_id"]
        if cid not in latest_runs:
            latest_runs[cid] = run

    # Build schedule list from APScheduler jobs
    day_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
    schedules = []
    for job in scheduler.get_jobs():
        if not job.id.startswith("cycle-"):
            continue
        client_id = job.id.replace("cycle-", "")
        client = client_map.get(client_id, {})
        last_run = latest_runs.get(client_id)

        schedules.append({
            "client_id": client_id,
            "client_name": client.get("brand_name", "Unknown"),
            "cycle_frequency": client.get("cycle_frequency", "weekly"),
            "cycle_day": day_map.get(client.get("cycle_day", 1), "tue"),
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "last_run_status": last_run["status"] if last_run else None,
            "last_run_at": last_run["created_at"] if last_run else None,
        })

    return {"schedules": schedules}
```

- [ ] **Step 2: Add test for schedules endpoint**

Add to `agents/tests/test_server.py`:

```python
def test_schedules_endpoint_requires_auth():
    from server import app
    client = TestClient(app)
    resp = client.get("/api/schedules")
    assert resp.status_code == 401
```

- [ ] **Step 3: Run tests**

Run: `cd agents && python -m pytest tests/test_server.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add agents/server.py agents/tests/test_server.py
git commit -m "feat: add /api/schedules endpoint — read-only schedule visibility"
```

---

## Task 13: Webflow Implementor

**Files:**
- Create: `agents/src/implementors/webflow_impl.py`
- Modify: `agents/src/implementors/router.py`

- [ ] **Step 1: Implement Webflow staging**

```python
# agents/src/implementors/webflow_impl.py
import httpx


def apply_webflow_change(card: dict, cms_config: dict) -> dict:
    """Apply a change to Webflow staging (site.webflow.io), NOT production."""
    api_token = cms_config.get("api_token", "")
    site_id = cms_config.get("site_id", "")

    if not api_token or not site_id:
        return {"status": "error", "error": "Webflow API token or site ID not configured"}

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
        "accept-version": "2.0.0",
    }

    page_url = card.get("page_url", "")
    slug = page_url.rstrip("/").split("/")[-1] or "index"

    # Find the collection item or static page matching this URL
    try:
        # Try static pages first
        resp = httpx.get(
            f"https://api.webflow.com/v2/sites/{site_id}/pages",
            headers=headers,
            timeout=15,
        )
        if resp.status_code != 200:
            return {"status": "error", "error": f"Webflow API returned {resp.status_code}: {resp.text[:200]}"}

        pages = resp.json().get("pages", [])
        matched_page = None
        for page in pages:
            if page.get("slug") == slug or page.get("title", "").lower().replace(" ", "-") == slug:
                matched_page = page
                break

        if not matched_page:
            return {"status": "error", "error": f"Could not find Webflow page matching slug '{slug}'"}

        page_id = matched_page["id"]

        # Apply changes to staging (don't publish)
        update_data = {}
        if card.get("code_block"):
            # For schema changes, append to custom code head
            current_head = matched_page.get("seo", {}).get("customHeadCode", "")
            schema_tag = f'<script type="application/ld+json">\n{card["code_block"]}\n</script>'
            update_data["seo"] = {"customHeadCode": (current_head + "\n" + schema_tag).strip()}

        if update_data:
            resp = httpx.patch(
                f"https://api.webflow.com/v2/sites/{site_id}/pages/{page_id}",
                headers=headers,
                json=update_data,
                timeout=15,
            )
            if resp.status_code not in (200, 201):
                return {"status": "error", "error": f"Webflow page update returned {resp.status_code}: {resp.text[:200]}"}

        staging_domain = cms_config.get("staging_domain", f"{site_id}.webflow.io")
        staging_url = f"https://{staging_domain}/{slug}" if slug != "index" else f"https://{staging_domain}/"

        return {
            "status": "implemented",
            "preview_url": staging_url,
            "webflow_page_id": page_id,
            "note": "Change applied to staging only — NOT published to production",
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}
```

- [ ] **Step 2: Update router.py**

Add the `webflow` case to `agents/src/implementors/router.py`. Add this block before the final fallback `print` statement:

```python
    if cms_type == "webflow":
        from src.implementors.webflow_impl import apply_webflow_change
        return apply_webflow_change(card, cms_config)
```

- [ ] **Step 3: Commit**

```bash
git add agents/src/implementors/webflow_impl.py agents/src/implementors/router.py
git commit -m "feat: add Webflow staging implementor + route in router"
```

---

## Task 14: LangSmith Tracing Setup

**Files:**
- Modify: `agents/server.py`

- [ ] **Step 1: Add LangSmith environment variable setup**

At the top of `agents/server.py`, after the existing `load_dotenv()` call and before the `API_KEY` line, add:

```python
# LangSmith tracing — auto-instruments LangGraph when enabled
# Set LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY in .env or Railway env vars
if os.environ.get("LANGCHAIN_TRACING_V2") == "true":
    print("  [LangSmith] Tracing enabled")
```

- [ ] **Step 2: Add to .env.example (if it exists) or document**

If `agents/.env.example` exists, add:
```
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=
```

If it doesn't exist, create `agents/.env.example` with all required env vars.

- [ ] **Step 3: Commit**

```bash
git add agents/server.py agents/.env.example
git commit -m "feat: add LangSmith tracing config — auto-instruments LangGraph"
```

---

## Task 15: Run Full Test Suite

**Files:** None (verification only)

- [ ] **Step 1: Run all tests**

Run: `cd agents && python -m pytest tests/ -v --tb=short`
Expected: All tests PASS. If any fail, fix them before proceeding.

- [ ] **Step 2: Verify no import errors**

Run: `cd agents && python -c "from src.improvement.pipeline import run_improvement_pipeline; print('Import OK')"`
Expected: `Import OK`

- [ ] **Step 3: Verify graph builds correctly**

Run: `cd agents && python -c "from src.graph.pipeline import build_graph; g = build_graph(); print('Nodes:', sorted(n for n in g.get_graph().nodes.keys() if n not in ('__start__', '__end__')))"`
Expected: `Nodes: ['await_approval', 'load_config', 'run_gsc', 'run_implementation', 'run_improvement_pipeline', 'run_tracker']`

- [ ] **Step 4: Final commit (if any fixes were needed)**

```bash
git add -A
git commit -m "fix: resolve test failures from pipeline integration"
```
