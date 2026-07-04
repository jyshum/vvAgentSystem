# GEO Agent System — Full Technical Design

**Date:** 2026-06-25
**Status:** Approved
**Supersedes:** 2026-06-23-audit-recommendation-implementation-design.md

---

## 1. System Overview

The GEO Agent System is an autonomous pipeline that measures and improves a brand's visibility in AI-generated search results. It runs as an always-on API server on Railway, orchestrated by LangGraph, with a Next.js dashboard on Vercel for monitoring and approval.

**Pipeline stages (orchestrated by LangGraph StateGraph):**

1. **Tracker** — queries AI engines (ChatGPT, Perplexity, Claude, Gemini) with client-defined search queries, detects whether the brand is mentioned/cited, and tracks competitor mentions
2. **Audit** — crawls a client's website, renders each page in a headless browser, visually classifies the page type, and scores applicable pages against 6 GEO pillars — reporting both strengths and weaknesses
3. **Recommendation** — reads audit scores, generates before/after action cards for pages scoring below 60/100
4. **Approval (HITL interrupt)** — graph pauses, action cards sit as `pending` in Supabase until approved/rejected in the dashboard
5. **Implementation** — graph resumes after approval, delivers changes to the client's site (GitHub PR, WordPress API, or copy-paste instructions)

Additionally, a **Reddit Scout** runs as a parallel node, searching Reddit for brand mentions and relevant discussions.

**Trigger paths:**
- **Automatic** — APScheduler triggers the full pipeline per client on their configured `cycle_day` and `cycle_frequency`
- **Manual** — "Run Now" (tracker) and "Run Audit" (audit + recommend) buttons on the dashboard call the LangGraph API for an immediate one-off run

---

## 2. LangGraph Orchestration

### StateGraph

The pipeline is a LangGraph `StateGraph` with typed state flowing between nodes. Each node wraps an existing Python module.

```python
class GEOState(TypedDict):
    client_id: str
    client_config: dict
    tracker_results: list[dict]
    tracker_scores: dict
    audit_pages: list[dict]
    audit_summary: dict
    action_cards: list[dict]
    approved_card_ids: list[str]
    implementation_results: list[dict]
    reddit_posts: list[dict]
    run_type: str  # "full" | "tracker_only" | "audit_only"
    error: str | None
```

### Graph nodes

| Node | Wraps | What it does |
|---|---|---|
| `load_config` | `tracker.load_client_config()` | Fetches client config from Supabase |
| `run_tracker` | `tracker.run_tracker()` | Queries 4 AI engines, writes results to Supabase |
| `run_audit` | `auditor.run_audit()` | Crawls site, renders pages, scores pillars, writes to Supabase |
| `run_recommender` | `recommender.run_recommender()` | Generates action cards for pillars <60, writes to Supabase |
| `run_reddit_scout` | `reddit_scout.run_scout()` | Searches Reddit for brand mentions |
| `await_approval` | `interrupt()` | Pauses graph — waits for dashboard to resume with approved card IDs |
| `run_implementation` | `implement.implement_card()` | Executes approved cards (GitHub PRs, WordPress API, copy-paste) |

### Graph edges and conditional routing

```python
graph = StateGraph(GEOState)

graph.add_node("load_config", load_config)
graph.add_node("run_tracker", run_tracker)
graph.add_node("run_audit", run_audit)
graph.add_node("run_recommender", run_recommender)
graph.add_node("run_reddit_scout", run_reddit_scout)
graph.add_node("await_approval", await_approval)
graph.add_node("run_implementation", run_implementation)

graph.set_entry_point("load_config")

# After config, route based on run_type
graph.add_conditional_edges("load_config", route_by_run_type, {
    "full": "run_tracker",
    "tracker_only": "run_tracker",
    "audit_only": "run_audit",
})

# Full pipeline: tracker → audit → recommend → approval → implement
graph.add_edge("run_tracker", "run_audit",
               condition=lambda s: s["run_type"] == "full")
graph.add_edge("run_tracker", END,
               condition=lambda s: s["run_type"] == "tracker_only")

graph.add_edge("run_audit", "run_recommender")
graph.add_edge("run_recommender", "await_approval")
graph.add_edge("await_approval", "run_implementation")
graph.add_edge("run_implementation", END)

# Reddit scout runs in parallel with audit (not blocking)
graph.add_edge("run_tracker", "run_reddit_scout",
               condition=lambda s: s["run_type"] == "full")
```

### HITL interrupt at approval

The `await_approval` node calls LangGraph's `interrupt()`. The graph execution pauses and persists its state. When the dashboard sends approved card IDs via the API, the graph resumes at `run_implementation`.

```python
from langgraph.types import interrupt

def await_approval(state: GEOState) -> dict:
    approved = interrupt({
        "action": "approve_cards",
        "pending_cards": state["action_cards"],
    })
    return {"approved_card_ids": approved}
```

### Thread management

Each graph execution gets a unique `thread_id`. LangGraph persists state per thread, so multiple clients can have concurrent in-flight pipelines:

```
Client A Monday run → thread_id = "client-a-2026-06-25"
Client B Wednesday run → thread_id = "client-b-2026-06-25"
```

The `thread_id` is stored on the Supabase `pipeline_runs` table so the dashboard knows which thread to resume when approving cards.

### Error handling

Each node catches exceptions and writes them to `state["error"]`. Conditional edges check for errors:
- If tracker fails → still attempt audit (partial data > no data)
- If audit fails → skip recommend, log error, don't create cards
- If implementation fails for one card → continue with remaining cards, mark failed card as `error`

---

## 3. API Server

### FastAPI on Railway (always-on)

The LangGraph graph runs inside a FastAPI application deployed on Railway as an always-on service. The dashboard calls this API directly.

```python
app = FastAPI()

@app.post("/api/run")
async def trigger_run(client_id: str, run_type: str = "full"):
    """Dashboard calls this for 'Run Now' or 'Run Audit'"""
    thread_id = f"{client_id}-{datetime.now().isoformat()}"
    result = await graph.ainvoke(
        {"client_id": client_id, "run_type": run_type},
        config={"configurable": {"thread_id": thread_id}},
    )
    return {"thread_id": thread_id, "status": "started"}

@app.post("/api/approve")
async def approve_cards(thread_id: str, approved_card_ids: list[str]):
    """Dashboard calls this when 'Finalize & Implement' is clicked"""
    result = await graph.ainvoke(
        Command(resume=approved_card_ids),
        config={"configurable": {"thread_id": thread_id}},
    )
    return {"status": "implementation_complete", "results": result}

@app.get("/api/status/{thread_id}")
async def get_status(thread_id: str):
    """Dashboard polls this for run progress"""
    state = graph.get_state(config={"configurable": {"thread_id": thread_id}})
    return {"status": state.next, "state": state.values}
```

### Authentication

Dashboard → API calls are authenticated with a shared API key in the `Authorization` header. The key is stored as an env var on both Vercel (`LANGGRAPH_API_KEY`) and Railway (`API_KEY`).

### State persistence

LangGraph requires a checkpointer for `interrupt()` to work. Use `SqliteSaver` for MVP (file on Railway's persistent volume) or `PostgresSaver` pointing at the existing Supabase PostgreSQL instance.

```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(os.environ["SUPABASE_DB_URL"])
graph = graph.compile(checkpointer=checkpointer)
```

---

## 4. Scheduling

### APScheduler (in-process)

APScheduler runs inside the same FastAPI process on Railway. On startup, it reads all clients from Supabase and creates a scheduled job for each one.

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def start_scheduler():
    clients = await fetch_all_clients()
    for client in clients:
        scheduler.add_job(
            trigger_pipeline,
            trigger="cron",
            day_of_week=client["cycle_day"],  # 0=Mon, 6=Sun
            hour=2,
            minute=client_offset(client),  # stagger by 15min
            args=[client["id"]],
            id=f"cycle-{client['id']}",
        )
    scheduler.start()
```

### Per-client schedules

Each client has `cycle_frequency` and `cycle_day` stored in the `clients` table:

```sql
clients.cycle_frequency  — 'weekly' | 'biweekly' (default: 'weekly')
clients.cycle_day        — 0-6 (default: 1 = Monday)
```

**Example with 3 clients:**
```
Client A: weekly,    Monday    → runs every Monday 2:00am
Client B: biweekly,  Wednesday → runs every other Wednesday 2:15am
Client C: weekly,    Monday    → runs every Monday 2:30am (staggered)
```

### Dynamic schedule updates

When a client's `cycle_day` or `cycle_frequency` is changed in the dashboard config page, the API updates APScheduler's jobs:

```python
@app.post("/api/client/{client_id}/schedule")
async def update_schedule(client_id: str, cycle_day: int, cycle_frequency: str):
    scheduler.reschedule_job(f"cycle-{client_id}", ...)
```

### No human trigger required

The system runs its cadence autonomously. Humans interact only at the approval stage (reviewing action cards) and optionally via "Run Now" / "Run Audit" for immediate runs.

---

## 5. Tracker

### How it works

For each `(query, engine)` pair:
1. Send the query to the AI engine
2. Detect brand mention (case-insensitive match against `brand_variations` list)
3. Detect brand citation (domain URL appears in response text)
4. Detect competitor mentions (same matching against `competitors` list)

### Engines

| Engine | API Key Env Var | Model |
|---|---|---|
| ChatGPT | `OPENAI_API_KEY` | gpt-4o-mini |
| Perplexity | `PERPLEXITY_API_KEY` | sonar |
| Claude | `ANTHROPIC_API_KEY` | claude-haiku-4-5 |
| Gemini | `GOOGLE_GEMINI_API_KEY` | gemini-2.5-flash |

Engines are registered dynamically — if the API key is missing, the engine is skipped.

### Output

- Per-engine mention rate and citation rate
- Aggregate mention/citation rates across all engines
- Competitor mention rates for comparison

### Scoring

```
mention_rate  = mentions / total_queries per engine
citation_rate = citations / total_queries per engine
aggregate     = totals across all engines
```

### Database tables

```sql
tracker_runs    — one row per run (client_id, aggregate rates, per-engine scores, competitor scores)
tracker_results — one row per (query, engine) pair (mention/citation flags, response text)
```

---

## 6. Audit

### The 6 Pillars

| Pillar | Method | What it checks |
|---|---|---|
| 1 — Content Structure | Haiku | First paragraph answers a user question? H2/H3 as questions? Scannable sections? |
| 2 — Fact Density | Haiku | Specific numbers, percentages, dollar amounts per 200 words. Target: ≥1 per 200 words |
| 3 — Source Citations | Rules | External links in body content (no nav/footer). Bonus for .gov/.edu/.org. Target: 3–5 |
| 4 — Authority Signals | Haiku | Press mentions with outlet names, expert quotes with attribution, aggregate ratings |
| 5 — Schema Markup | Rules | JSON-LD blocks, @type values (FAQPage/HowTo = high value, Organization = baseline) |
| 6 — Freshness | Rules | article:modified_time → `<time>` → Last-Modified header → visible date. Score by age in days |

Rules = deterministic Python. Haiku = single LLM call per page for pillars 1, 2, and 4 combined.

### Pillar output format

Every pillar returns:
```json
{
  "score": 0-100,
  "strengths": ["specific things the page does well for this pillar"],
  "issues": ["specific things wrong"],
  "recommendations": ["specific actionable fixes"]
}
```

**Strengths** must be specific and evidence-based. "Has headings" is not a strength. "H2 headings map to the user journey (Rescue → Repurpose → Deliver)" is.

### Scoring thresholds

- **0–39**: Critical
- **40–59**: Needs work — action cards generated
- **60–79**: Acceptable — no action cards, noted in summary
- **80–100**: Good

### Page discovery

1. Fetch `https://domain.com/sitemap.xml` — parse all `<loc>` tags
2. If no sitemap: crawl homepage, follow internal `<a href>` links to depth 1
3. Cap at 20 pages per run

### Page rendering (Playwright)

Each discovered URL is loaded in a headless Chromium browser via Playwright, not fetched with a simple HTTP client. This is critical for two reasons:

1. **JavaScript rendering** — SPA sites (React, Next.js, Webflow) serve the same HTML shell for every route. A raw HTTP fetch returns identical content for `/about` and `/request`. Playwright renders the actual route-specific DOM.
2. **Visual classification** — a screenshot of the rendered page is sent to Haiku vision for page-type classification (see below).

**Per-page flow:**
1. Playwright loads the URL, waits for network idle / DOM settle
2. Captures a full-page **screenshot** (PNG)
3. Captures the **rendered DOM** (innerHTML after JS execution)
4. The rendered DOM is passed to `parse_html()` for content extraction
5. The screenshot is sent to Haiku vision for page-type classification

**Fallback:** If Playwright fails (timeout, blocked by site, crash), fall back to `httpx.get()` for raw HTML + URL-pattern classification. Log a warning so the user knows that page's classification may be less accurate.

**Dependency:** `playwright` Python package + Chromium (`playwright install chromium`).

### Page-type classification

Pages are classified to determine which pillars apply. Classification uses a two-tier approach:

**Tier 1 — URL pattern fast path (skip browser):**
Obvious utility pages are classified without rendering:
- `/contact`, `/privacy`, `/terms`, `/thank`, `/404`, `/sitemap`
- `/request`, `/donate`, `/apply`, `/signup`, `/register`, `/submit`

These go straight to `PILLAR_APPLICABILITY["utility"]` (Schema Markup only).

**Tier 2 — Haiku vision classification (primary method):**
For all other pages, the Playwright screenshot is sent to Claude Haiku with vision:

> "What type of page is this? Classify as one of: homepage, about, service, article, faq, utility/form, landing, gallery. Respond with the classification and one sentence explaining the page's primary purpose."

This handles arbitrary page structures — galleries, form pages, marketing landing pages, SPAs — without maintaining URL pattern lists. Cost: ~$0.002 per page.

**URL patterns as fallback only:** The existing URL pattern lists (article, FAQ, about, service) serve as fallback classification if Playwright or Haiku vision fails.

### Pillar applicability by page type

| Page Type | Applicable Pillars |
|---|---|
| homepage | Content Structure, Authority Signals, Schema Markup |
| about | Content Structure, Authority Signals, Schema Markup |
| service | Content Structure, Fact Density, Source Citations, Authority Signals, Schema Markup |
| article | All 6 pillars |
| faq | Content Structure, Source Citations, Schema Markup |
| utility/form | Schema Markup only |
| landing | Content Structure, Authority Signals, Schema Markup |
| gallery | Schema Markup only |

### HTML parsing (`parsers.py`)

Receives the **rendered DOM** from Playwright (not raw HTTP response) and extracts:
- Title from `<title>` tag
- Headings (H1–H4) with level and text
- Paragraphs with >30 chars (filters noise)
- External links (href starting with http, not matching client domain)
- JSON-LD schema blocks from `<script type="application/ld+json">`
- Modified date from meta tags or `<time>` elements
- Raw text (full page text after boilerplate strip)

**Boilerplate stripping:** Removes `<nav>`, `<footer>`, `<header>`, `<aside>` tags and elements with class names matching nav/footer/header/sidebar/menu.

### Haiku scoring prompt

A single Haiku call per page scores Content Structure, Fact Density, and Authority Signals together. The prompt receives:
- `raw_text[:3000]` — first 3000 chars of rendered page text
- First paragraph text
- All headings with levels
- **Page type and URL** — e.g. "This is a service page at /volunteer. Score the content accordingly — focus on content relevant to this page's purpose."

Returns JSON with `score`, `strengths[]`, `issues[]`, and `recommendations[]` per pillar.

### Rule-based scorers

**Source Citations:** Counts external links in body content. 0 links = 0, 1–2 = 30, 3–4 = 55, 5+ = 70. Bonus up to +30 for authoritative TLDs (.gov, .edu, .org) or research domains (pubmed, statcan, etc.). Strengths reported when citations are present (e.g. "Strong external citation density with X authoritative sources").

**Schema Markup:** Finds JSON-LD blocks and classifies @type values. High-value types (FAQPage, HowTo, Article) + baseline types (Organization, LocalBusiness) = 100. Flags malformed JSON. Strengths reported for high-value schema (e.g. "FAQPage and LocalBusiness schema both present — best-in-class coverage").

**Freshness:** Finds date from meta tags → `<time>` → Last-Modified header → regex for "Month DD, YYYY" in body. Scores by age: ≤90 days = 100, ≤180 = 65, ≤365 = 35, >365 = 10. No date found = 20. Strengths reported when current (e.g. "Content is current — last modified X days ago"). Page-type filtering ensures form/utility pages are never scored on Freshness.

### Shared content deprioritization (nice-to-have)

For multi-page audits on SPA sites, if hallucination persists despite rendered DOM + page-type context: diff rendered DOMs across pages. Content blocks appearing on 80%+ of pages get tagged as shared layout and deprioritized in the scoring prompt. Only implement if needed.

### Audit pipeline architecture

```
score_page(url)
  │
  ├─ URL in UTILITY_PATTERNS? ──yes──▶ page_type = "utility", fetch via httpx
  │
  └─ no
      │
      ├─ Playwright: load URL, wait for idle
      │   ├─ capture screenshot
      │   └─ capture rendered DOM
      │
      ├─ Haiku vision: classify page type from screenshot
      │
      ├─ parse_html(rendered_DOM) → ParsedPage
      │
      ├─ get_applicable_pillars(page_type)
      │
      ├─ Score applicable pillars only:
      │   ├─ Rule-based: Source Citations, Schema, Freshness (with strengths)
      │   └─ Haiku batch: Content Structure, Fact Density, Authority
      │       (with strengths + page type context)
      │
      └─ Return { url, title, page_type, pillars: { score, strengths, issues, recommendations } }
```

### Cost per page

| Step | Latency | API Cost |
|---|---|---|
| Playwright render | ~2-3s | $0 |
| Haiku vision classification | — | ~$0.002 |
| Haiku text scoring (3 pillars) | — | ~$0.003 |
| Rule-based scoring (3 pillars) | <0.1s | $0 |
| **Total per page** | **~3s** | **~$0.005** |

For a 10-page audit: ~$0.05 total, ~30s additional latency (parallelizable).

### Database tables

```sql
audit_runs  — one row per run (client_id, pages_audited, site_score, pillar_averages, weakest_pillar)
page_scores — one row per page per run (url, title, word_count, total_score, pillar_scores jsonb)
```

---

## 7. Recommendation Engine

### How it works

For each page in an audit run, for each pillar scoring below 60:
1. **Authority Signals** — generates suggestion-only cards directly from the issues/recommendations (no LLM call needed since these are off-page actions)
2. **All other pillars** — sends a Haiku prompt with the page URL, pillar name, score, issues, and page content (first 2000 chars) to generate a before/after action card

### Action card structure

```
run_id          — which audit run
page_url        — which page
pillar          — which of the 6 pillars
score           — current score (0–100)
issue           — one sentence describing what's wrong
before_text     — exact current content (quoted from the page, or empty for new content)
after_text      — exact replacement content, ready to paste
code_block      — for schema/meta changes: full code to paste
status          — pending | approved | rejected | implemented
cms_action      — none | github_pr | wordpress_api | copy_paste
```

Authority Signals cards always have `cms_action: none` (suggestion-only).

### Database table

```sql
action_cards — one row per recommendation (run_id, page_url, pillar, score, issue, before/after, status, cms_action)
```

---

## 8. Implementation Handlers

### CMS type detection

Stored on client record during onboarding. Auto-detection fallback from HTTP headers:
- `X-Powered-By: PHP` + `/wp-json/` accessible → `wordpress`
- `X-Generator: Webflow` → `webflow`
- GitHub repo URL in config → `github`
- Otherwise → `copy_paste`

### Per-pillar implementation by CMS

| Pillar | GitHub | WordPress | Webflow | Squarespace/Wix |
|---|---|---|---|---|
| Content Structure | PR: replace paragraph | REST API: update post | Manual | Copy-paste |
| Fact Density | PR: insert sentences | REST API: update post | Manual | Copy-paste |
| Source Citations | PR: wrap text in anchor | REST API: update post | Manual | Copy-paste |
| Authority Signals | Suggestion only | Suggestion only | Suggestion only | Suggestion only |
| Schema Markup | PR: inject JSON-LD | REST API: head via plugin | Webflow API | Copy-paste |
| Freshness | PR: update meta date | REST API: update date | Manual | Copy-paste |

### GitHub implementation flow

1. Fetch current file content via GitHub API
2. Apply string replacement (`before_text` → `after_text`) or inject `code_block` before `</head>`
3. Create branch `vv-audit-{pillar}-{date}`
4. Open PR with before/after diff and explanation

### WordPress implementation flow

1. `GET /wp-json/wp/v2/pages?slug={slug}` to find post ID
2. `PATCH /wp-json/wp/v2/pages/{id}` with updated content
3. For schema: inject into `yoast_head_json` or prepend to content

### Copy-paste fallback

Dashboard shows the exact text/code block to copy and step-by-step instructions for where to paste in their CMS.

### Database

Updates `action_cards.status` to `implemented` after successful execution.

---

## 9. Reddit Scout

Searches Reddit for brand-related discussions using public `.json` endpoints (no API key required). Runs as a parallel LangGraph node alongside the audit — non-blocking.

### Search queries generated

- `{brand_name}`
- `{brand_name} review`
- `{brand_name} alternative`
- Top 3 target keywords (words >4 chars extracted from `target_queries`)

### Relevance scoring

```
brand_name in text       → +0.40
each keyword hit         → +0.15 (max 0.45)
upvotes > 100            → +0.15
upvotes > 20             → +0.08
max score                → 1.0
```

### Output per post

```
title, url, subreddit, score, num_comments, selftext (first 500 chars), relevance_score
```

---

## 10. Dashboard

### Admin overview (`/admin`)

Client list with mention/citation rates, latest run info, and trigger buttons.

### Client detail (`/admin/clients/[id]`)

Tabs: CONFIG | RUNS | AUDIT

**Config tab** — edit brand name, queries, competitors, `cycle_day`, `cycle_frequency`

**Runs tab** — tracker run history with per-engine breakdown

**Audit tab** — audit run history with site scores, weakest pillar callout

### Trigger buttons (on client detail page)

- **"Run Now"** — calls `POST /api/run` with `run_type: "tracker_only"`. Triggers an immediate tracker run for this client. Does not start or affect the automatic schedule.
- **"Run Audit"** — calls `POST /api/run` with `run_type: "audit_only"`. Triggers audit → recommend → pauses at approval.

Both are manual one-off triggers. The automatic schedule runs independently.

### Approvals page (`/admin/approvals`) — NEW

A unified queue of all pending action cards across ALL clients. This is the primary review workflow — not per-client audit pages.

**Layout:**
- Filterable by client, pillar, priority (critical / needs work)
- Each card shows: client name, page URL, pillar, current score, issue summary, before/after preview
- Approve and reject are one-click actions per card
- Batch actions: "Approve all schema cards", "Approve all for [client]"

**"Finalize & Implement" button:**
- Appears when there are approved (but not yet implemented) cards
- Clicking it calls `POST /api/approve` with the `thread_id` and list of approved card IDs
- LangGraph resumes from `interrupt()` → implementation runs → cards marked as `implemented`
- Results appear inline (PR URLs, success/failure status per card)

**Why a separate page:** With multiple clients, visiting each client's audit page to review cards doesn't scale. One unified queue lets you review everything in a single session, batch approve low-risk items (schema cards), and carefully review high-risk items (content rewrites).

### Audit detail page (`/admin/clients/[id]/audit/[runId]`)

Remains read-only — shows page scores, pillar breakdowns with strengths and issues, and action card statuses. Links to the approvals page for taking action. No approve/reject buttons on this page.

---

## 11. Database Schema

### Client table

```sql
clients         — brand_name, website_domain, brand_variations[], target_queries[], competitors[]
                  cms_type ('github' | 'wordpress' | 'webflow' | 'copy_paste'), cms_config jsonb
                  cycle_frequency ('weekly' | 'biweekly'), cycle_day (0-6, default 1 = Monday)
```

### Tracker tables

```sql
tracker_runs    — client_id, aggregate_mention_rate, aggregate_citation_rate, per_engine_scores, competitor_scores
tracker_results — run_id, query, engine, model, brand_mentioned, brand_cited, citation_url, competitor_mentions[], response_text
```

### Audit tables

```sql
audit_runs      — client_id, pages_audited, site_score, pillar_averages jsonb, weakest_pillar
page_scores     — run_id, url, title, word_count, total_score, pillar_scores jsonb
action_cards    — run_id, page_url, pillar, score, issue, before_text, after_text, code_block, status, cms_action
```

### Pipeline tables (NEW)

```sql
pipeline_runs   — client_id, thread_id, run_type, status ('running' | 'awaiting_approval' | 'implementing' | 'completed' | 'error'), started_at, completed_at, error_message
```

---

## 12. Full Pipeline Flow

### Automatic weekly cycle (no human trigger)

```
Monday 2:00am — APScheduler fires for Client A
  │
  ├─ load_config → fetch client config from Supabase
  ├─ run_tracker → query 4 AI engines, write results
  ├─ run_audit → Playwright render, classify, score pages
  ├─ run_reddit_scout → search Reddit (parallel with audit)
  ├─ run_recommender → generate action cards for pillars <60
  ├─ await_approval → interrupt() — graph pauses
  │
  │   pipeline_runs.status = "awaiting_approval"
  │   Action cards in Supabase with status = "pending"
  │
  ╰── Graph is paused. Waiting for human.

Tuesday morning — You open the dashboard
  │
  ├─ /admin/approvals shows pending cards from Client A
  ├─ Review cards, approve/reject individually or in batch
  ├─ Click "Finalize & Implement"
  │
  ├─ Dashboard calls POST /api/approve with thread_id + approved IDs
  ├─ LangGraph resumes → run_implementation
  │   ├─ GitHub PRs opened for approved content changes
  │   ├─ WordPress API called for approved updates
  │   └─ Copy-paste cards marked as "implemented" (shown in dashboard)
  │
  └─ pipeline_runs.status = "completed"
```

### Manual "Run Now" (tracker only)

```
Dashboard → POST /api/run { client_id, run_type: "tracker_only" }
  │
  ├─ load_config → run_tracker → END
  └─ Results appear on the Runs tab immediately
```

### Manual "Run Audit"

```
Dashboard → POST /api/run { client_id, run_type: "audit_only" }
  │
  ├─ load_config → run_audit → run_recommender → await_approval
  ├─ Cards appear on /admin/approvals
  └─ Same approval → implementation flow as automatic cycle
```

---

## 13. Infrastructure

### Railway (always-on API server)

- FastAPI + LangGraph + APScheduler in a single process
- Persistent volume for Playwright browser cache
- PostgreSQL checkpointer using Supabase DB connection
- Env vars: all API keys, `SUPABASE_DB_URL`, `API_KEY` (for dashboard auth)

### Vercel (dashboard)

- Next.js app, existing deployment
- Env vars: `LANGGRAPH_API_URL` (Railway URL), `LANGGRAPH_API_KEY`
- API routes call Railway FastAPI directly via `fetch`

### Dependencies (new)

```
langgraph>=0.4.0
fastapi>=0.115.0
uvicorn>=0.34.0
apscheduler>=3.10.0
playwright>=1.49.0
```

---

## 14. What This Does Not Cover

- Client-facing dashboard (admin-only for now)
- Webflow API integration (copy-paste fallback until a Webflow client onboards)
- Server-side PDF generation (deferred)
- Google Search Console integration (deferred — spec exists in original design doc)
- Additional freshness date sources (sitemap lastmod, Wayback Machine) — page-type filtering handles false positives
- Shared content diffing across pages — only implement if hallucination persists after rendered DOM changes
- Conditional routing intelligence (e.g. skip audit if tracker scores are high) — graph structure supports it, implement when patterns emerge from data
