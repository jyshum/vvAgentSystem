# AI Visibility Improvement Pipeline — Design Spec

## Goal

Replace the current `run_audit → run_recommender` pipeline with a sequential, gap-driven improvement pipeline that unifies query-level competitive data with page-level site quality into a single workflow. Add LangSmith tracing for step-level observability and a read-only schedules endpoint.

## What Stays Unchanged

- **Tracker** (Phase 1): 5 runs × N queries × 4 engines, mention detection, Haiku classification
- **Competitive Gaps** (Phase 2): `competitor_mention_rate - client_mention_rate`, stored per run
- **Stability Tracking** (Phase 3): `locked_in | gaining | declining | volatile | absent` computed from last 3 runs
- **Query Management** (Phase 4): queries table with bucket, set_type, status, versioning
- **Scheduling**: APScheduler with CronTrigger per client, `cycle_frequency` + `cycle_day`
- **Implementation router**: `route_card()` dispatching to WordPress/GitHub/Shopify/copy_paste

## What Gets Replaced

The current pipeline flow:

```
load_config → run_tracker → run_gsc → run_audit → run_recommender → await_approval → run_implementation
```

The `run_audit` node crawls up to 20 pages, scores all of them on 6 pillars (3 Haiku calls + 3 deterministic per page), and `run_recommender` generates one Haiku action card per low-scoring pillar per page. This produces 55+ unfocused action cards with no connection to which queries are actually losing competitively.

**New pipeline flow:**

```
load_config → run_tracker → run_gsc → run_improvement_pipeline → await_approval → run_implementation
```

`run_improvement_pipeline` is a single node that runs Steps 1-6 internally as a sequential process.

---

## Pipeline Steps

### Step 1: Crawlability Gate

Verify AI bots can access the client's website. All checks are deterministic HTTP requests — no API cost.

**Checks:**

1. **robots.txt** — Fetch `{domain}/robots.txt`. Parse for `Disallow` rules targeting these user agents:
   - `GPTBot`, `OAI-SearchBot`, `ChatGPT-User` (OpenAI)
   - `ClaudeBot`, `Claude-SearchBot`, `anthropic-ai` (Anthropic)
   - `PerplexityBot` (Perplexity)
   - `Google-Extended` (Google AI training)
   - Also check wildcard `User-agent: *` rules

2. **JavaScript rendering** — Fetch 3 key pages (homepage + 2 highest-traffic from sitemap) with a plain HTTP client (no JS). Compare word count of raw HTML vs what the page title/meta suggests. If raw HTML body contains < 200 words but page clearly has content → JS-dependent, GPTBot can't read it.

3. **CDN/hosting blocks** — Fetch homepage with `User-Agent: GPTBot/1.0` header. If response is 403/401/503 → CDN is blocking AI bots.

4. **XML sitemap** — Check `{domain}/sitemap.xml` exists, returns 200, contains `<loc>` entries. Check if referenced in robots.txt.

5. **Meta tags** — On sampled pages, check for `<meta name="robots" content="nosnippet">` or `noindex` on key pages.

6. **llms.txt** — Check if `{domain}/llms.txt` exists. If not, flag as a low-priority suggestion (no AI company reads it yet, but forward-looking).

**Gate behavior:** If a critical blocker is found (robots.txt blocking GPTBot, CDN 403, JS-only rendering), generate a single high-priority action card with the specific fix needed. Pipeline continues but flags the blocker prominently — don't stop entirely because other steps (inventory, matching) still provide value for planning.

**Output:** `CrawlabilityReport` dict with per-check pass/fail/warning status and details.

### Step 2: Site Inventory

Crawl the client's site and build a structured inventory. This replaces the current `discover_pages()` + `score_page()` in `auditor.py`, but separates discovery from scoring.

**Page discovery** (reuse existing `discover_pages()` logic):
- Try sitemap.xml first, fall back to homepage link crawl
- Max 20 pages per client (configurable via `client_config`)

**Per page, extract:**
- `url` — full URL
- `title` — from `<title>` tag
- `h1` — first H1
- `first_paragraph` — first 500 chars of body text (for embedding)
- `schema_types` — list of `@type` values from any JSON-LD blocks on the page
- `word_count` — total body text word count
- `last_modified` — from `Last-Modified` header or `<meta>` tag, null if unavailable
- `outbound_links` — count of external links (for citation density check later)
- `has_faq_schema` — boolean
- `has_comparison_table` — boolean (check for `<table>` with comparison-style headers)
- `raw_html` — stored in memory only (not persisted), used by Step 4

**No scoring at this step.** Pure data collection.

**Output:** `list[PageInventory]` — one dict per discovered page.

### Step 3: Query-Page Matching

For each active target query, find the best-matching page from the inventory. This is the critical bridge between query-level tracker data and page-level actions.

**Method:** SBERT sentence embeddings with cosine similarity.

**Model:** `all-MiniLM-L6-v2` from `sentence-transformers` package. 80MB model, runs locally on CPU, no API cost.

**Process:**
1. For each page, concatenate `title + " " + h1 + " " + first_paragraph` as the page text representation
2. Embed all page texts in a single batch call to the model
3. Embed all active query texts in a single batch call
4. Compute cosine similarity matrix (queries × pages)
5. For each query, select the highest-similarity page

**Confidence thresholds:**
- `> 0.5` → **Matched** — this page addresses the query
- `0.3 - 0.5` → **Weak match** — flag for manual review, don't auto-generate action cards
- `< 0.3` → **Content gap** — no page on the site covers this topic

**Output per query:**
```python
{
    "query": str,
    "query_id": str,
    "match_type": "matched" | "weak" | "content_gap",
    "matched_page_url": str | None,
    "similarity_score": float,
    "bucket": "awareness" | "consideration" | "branded",
}
```

**Dependency:** `sentence-transformers` package added to `agents/requirements.txt`.

### Step 4: Citation-Readiness Scoring

Score only matched pages (similarity > 0.5), only on factors research shows drive AI citations. Each page is scored once even if multiple queries match to it.

**Deterministic structural checks (no API cost):**

| Check | Method | Score contribution |
|-------|--------|-------------------|
| Answer-first | First 150 words contain declarative sentence (not question, not filler intro) | 0-15 points |
| FAQ schema | JSON-LD `FAQPage` present, valid, Q&A pairs match visible content | 0-10 points |
| Comparison tables | `<table>` elements with comparison-pattern headers present | 0-10 points |
| Numbered/bulleted lists | Count of `<ol>` and `<ul>` elements in content area | 0-10 points |
| Freshness | `last_modified` date within 3 months | 0-10 points |
| Word count | >= 2,000 words with 3+ H2 sections | 0-10 points |
| Source citations | Outbound links to authoritative domains (not social, not self) | 0-10 points |
| Author attribution | Author name/bio, credentials, "reviewed by" markup | 0-10 points |
| Schema validation | Parse JSON-LD, validate structure, check for common errors | 0-15 points |

Total deterministic max: 100 points.

**Schema validation — 3 scenarios:**
1. **No schema** → Score 0/15 for schema check. Action: generate schema (Sonnet).
2. **Schema exists but broken** — Common issues: duplicate `Organization` graphs, `FAQPage` on ineligible pages, missing `@context`, missing required fields, type-content mismatches. Score based on severity. Action: fix specific issues (deterministic diagnosis).
3. **Schema exists and valid** — Check completeness: has `Organization` + `WebSite` + `BreadcrumbList` baseline? Score based on coverage. Action: suggest additions if incomplete.

**One Sonnet API call per matched page (quality judgment):**

Input: page content (first 3000 chars) + target query + structural check results.

Output (structured JSON):
```json
{
    "specificity": 1-5,
    "completeness": 1-5,
    "answer_directness": 1-5,
    "summary": "One sentence assessment"
}
```

The Sonnet scores are stored alongside the deterministic score but don't modify the 0-100 structural score. They're used for action card prioritization — a page scoring 70/100 structurally but 2/5 on specificity gets a "improve content depth" card.

**Output per page:**
```python
{
    "url": str,
    "structural_score": int,  # 0-100
    "check_results": dict,    # per-check breakdown
    "sonnet_quality": dict,   # specificity, completeness, directness
    "schema_status": "missing" | "broken" | "valid_incomplete" | "valid_complete",
    "schema_errors": list[str],
}
```

### Step 5: Competitive Gap Check

For each matched query, determine if a competitor is beating the client.

**Method:** Pull from existing `competitive_gaps` data (Phase 2, already computed and stored per tracker run in the same cycle).

**Calculation:** `competitor_mention_rate - client_mention_rate`
- Positive = competitor winning (gap exists)
- Zero = both equal (no gap)
- Negative = client winning (no gap)

**Direction is always `competitor - client`.** A positive value means the client is losing.

For queries with multiple competitors, use the max gap (worst-case competitor).

**Output per matched query:**
```python
{
    "query": str,
    "query_id": str,
    "competitive_gap": float,  # max across competitors, positive = losing
    "top_competitor": str,     # name of competitor with largest gap
    "client_mention_rate": float,
    "competitor_mention_rate": float,
}
```

### Step 5b: Reddit Scout (Gap Queries Only)

For queries where `competitive_gap > 0`, check community presence.

**Method:** Google search as proxy — `site:reddit.com "[query keywords]"` via `httpx` GET to Google search. No API key, no legal risk.

**Process per gap query:**
1. Search `site:reddit.com "{query text}"` via Google
2. Parse result snippets for thread titles and URLs
3. Check if client brand name or competitor names appear in thread titles/snippets
4. Collect up to 5 threads per query

**Output per gap query:**
```python
{
    "query": str,
    "threads_found": int,
    "threads": [{"title": str, "url": str, "snippet": str}],
    "client_mentioned": bool,
    "competitors_mentioned": list[str],
}
```

**Failure handling:** Google may rate-limit or return CAPTCHAs. If search fails, skip Reddit data for that query — it's supplementary, not critical.

### Step 6: Action Card Generation

Generate prioritized, actionable cards in two tracks.

**Ordering:**
1. **Competitive gap pages** — page exists but competitor is winning. Fix the matched page.
2. **Content gaps** — no page exists for a query where competitor is winning. Generate content brief (MANUAL track).
3. **General optimization** — no competitive gap, just improve page structural scores.

#### Track 1: Automated (agent implements on existing pages)

**Method:** Rule-based classification determines the action type (deterministic, never wrong). Sonnet generates specific changes.

**Rule-based classification:**
- Page missing FAQ schema → action type: `add_faq_schema`
- Page not answer-first → action type: `restructure_intro`
- Page has 0 source citations → action type: `add_citations`
- Content older than 3 months → action type: `update_freshness`
- Schema exists but broken → action type: `fix_schema` (with specific validator errors)
- Schema missing entirely → action type: `generate_schema`
- Low Sonnet specificity/completeness → action type: `improve_content_depth`

**Sonnet generates specifics (one call per action card):**
- Input: page content + query + rule-identified issue + competitive gap data
- Output: specific before/after text, exact schema JSON-LD, or rewritten intro paragraph

**Pre-surfacing validation (before card becomes visible):**
- Schema changes: JSON-LD parsed and validated programmatically. If invalid → card not surfaced.
- Content changes: HTML parsing check (no broken tags).
- New outbound links: HTTP HEAD check for 200 response.

**Action card schema (automated):**
```python
{
    "id": uuid,
    "run_id": uuid,           # improvement_run_id
    "client_id": uuid,
    "query_id": uuid | None,
    "page_url": str,
    "action_type": str,        # add_faq_schema, restructure_intro, etc.
    "track": "automated",
    "priority": int,           # 1=highest (competitive gap), 2=content gap, 3=optimization
    "competitive_gap": float | None,
    "structural_score": int,
    "issue": str,              # one sentence describing the problem
    "before_text": str,        # exact current text
    "after_text": str,         # exact replacement text
    "code_block": str,         # for schema/meta changes
    "validation_passed": bool,
    "status": "pending" | "approved" | "rejected" | "implemented",
    "cms_action": str,         # github_pr, wordpress_api, webflow_staging, copy_paste
    "created_at": timestamp,
}
```

#### Track 2: Manual (agency team executes)

**Content gap → Content brief card:**
```python
{
    "id": uuid,
    "run_id": uuid,
    "client_id": uuid,
    "query_id": uuid,
    "page_url": None,          # no page exists yet
    "action_type": "content_brief",
    "track": "manual",
    "priority": 2,
    "competitive_gap": float,
    "issue": "No page exists for this query",
    "brief": {
        "target_query": str,
        "competitive_landscape": str,  # who appears, what they cover
        "recommended_title": str,
        "recommended_h1": str,
        "key_sections": list[str],
        "facts_to_include": list[str],
        "schema_type": str,
        "internal_link_targets": list[str],
        "word_count_target": int,
    },
    "status": "pending",
    "cms_action": "none",
}
```

**Reddit engagement card:**
```python
{
    "action_type": "reddit_engagement",
    "track": "manual",
    "priority": 2,
    "threads": list[dict],     # from Step 5b
    "competitors_present": list[str],
    "engagement_notes": str,
}
```

### Step 7: Implementation Safety

All automated changes go through a CMS-specific safety layer. **Never touch production directly.**

| CMS Type | Safety Mechanism | What Admin Sees |
|----------|-----------------|-----------------|
| WordPress | Create draft revision via REST API + generate preview URL | Live preview with changes applied |
| Webflow | Update on staging subdomain (`site.webflow.io`), don't publish | Staging URL showing the change |
| GitHub/Headless | Create PR with diff, trigger Vercel preview deployment | PR diff + preview deployment URL |
| Squarespace | N/A — manual only, treated as `copy_paste` | Action card with exact instructions |

**Approval flow:**
1. Action card created with `status: pending`
2. For automated track: implementer creates draft/PR/staging change, stores preview URL on the card
3. Admin sees preview URL + before/after diff on dashboard
4. Admin approves or rejects
5. If approved: publish/merge via CMS API
6. If rejected: discard draft/close PR
7. Tracker validates improvement next cycle

**Rollback:**
- WordPress: built-in revision history
- Webflow: restore from backup
- GitHub: revert PR

### Step 8: Validation (Tracker Closes the Loop)

Not a new step to build — this is the existing tracker running on the next cycle. After actions are implemented:

- Next tracker cycle re-measures mention rates for affected queries
- Stability tracking classifies trend changes
- If mention rate improved → action worked
- If not → surface for human review

The system is self-correcting over cycles.

---

## Observability & Monitoring

### LangSmith Integration

Add LangSmith tracing to the LangGraph pipeline for step-level observability.

**Setup:**
- Set `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` environment variables on Railway
- LangSmith auto-instruments LangGraph — no code changes to node functions needed
- Free tier: 5,000 traces/month, 14-day retention (sufficient for agency scale)

**What it provides:**
- Node-by-node execution graph with timing
- State diffs between steps
- Error traces with full context
- Cost aggregation per run
- Run history and replay

### Schedule Visibility Endpoint

Add a read-only `/api/schedules` GET endpoint to the FastAPI server.

**Response:**
```json
{
    "schedules": [
        {
            "client_id": "uuid",
            "client_name": "Brand Name",
            "cycle_frequency": "weekly",
            "cycle_day": "tue",
            "next_run": "2026-07-08T02:00:00Z",
            "last_run_status": "completed",
            "last_run_at": "2026-07-01T02:00:00Z"
        }
    ]
}
```

**Implementation:** Query APScheduler's `get_jobs()` for next run times, join with client names from Supabase, and pull latest `pipeline_runs` status per client.

---

## Database Changes

### New table: `improvement_runs`

Replaces `audit_runs` as the tracking table for the new pipeline.

```sql
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
```

### New table: `page_inventory`

Stores the site inventory per improvement run.

```sql
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
```

### New table: `query_page_matches`

Stores the SBERT matching results.

```sql
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
```

### New table: `page_citation_scores`

Stores citation-readiness scoring results.

```sql
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
```

### Modify table: `action_cards`

The existing `action_cards` table needs new columns for the two-track system. Rather than migrating the old table structure, we add columns:

```sql
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
```

Update `cms_action` check constraint to include `webflow_staging`:
```sql
alter table public.action_cards drop constraint if exists action_cards_cms_action_check;
alter table public.action_cards add constraint action_cards_cms_action_check
    check (cms_action in ('none', 'github_pr', 'wordpress_api', 'webflow_staging', 'copy_paste'));
```

### Indexes

```sql
create index idx_improvement_runs_client on public.improvement_runs(client_id);
create index idx_page_inventory_run on public.page_inventory(run_id);
create index idx_query_page_matches_run on public.query_page_matches(run_id);
create index idx_query_page_matches_query on public.query_page_matches(query_id);
create index idx_page_citation_scores_run on public.page_citation_scores(run_id);
create index idx_action_cards_client on public.action_cards(client_id);
create index idx_action_cards_query on public.action_cards(query_id);
create index idx_action_cards_track on public.action_cards(track);
```

### RLS policies

All new tables get the same admin-only RLS pattern as existing tables:

```sql
alter table public.improvement_runs enable row level security;
alter table public.page_inventory enable row level security;
alter table public.query_page_matches enable row level security;
alter table public.page_citation_scores enable row level security;

create policy "Admins can manage improvement_runs"
    on public.improvement_runs for all
    using (public.is_admin()) with check (public.is_admin());
-- (same pattern for other 3 tables)
```

---

## GEOState Changes

The `GEOState` TypedDict in `agents/src/graph/state.py` gets new fields:

```python
class GEOState(TypedDict):
    # Existing fields (unchanged)
    client_id: str
    client_config: dict
    tracker_results: list[dict]
    tracker_scores: dict
    gsc_metrics: dict
    run_type: str
    thread_id: str
    error: str | None

    # Replaced fields
    # audit_pages → removed (replaced by improvement pipeline internal state)
    # audit_summary → removed
    # audit_run_id → removed

    # New fields
    improvement_run_id: str | None
    crawlability_report: dict
    page_inventory: list[dict]
    query_matches: list[dict]
    citation_scores: list[dict]
    competitive_gap_data: list[dict]
    reddit_scout_data: list[dict]
    action_cards: list[dict]        # kept, new schema
    approved_card_ids: list[str]    # kept
    implementation_results: list[dict]  # kept
```

---

## Pipeline Node Changes

In `agents/src/graph/pipeline.py`:

**Remove nodes:** `run_audit`, `run_recommender`

**Add node:** `run_improvement_pipeline` — single node that runs Steps 1-6 internally as sequential function calls. This is NOT 6 separate LangGraph nodes because the steps share in-memory state (page HTML, embeddings) that shouldn't be serialized to graph state.

**Updated graph:**
```python
graph.add_node("load_config", load_config)
graph.add_node("run_tracker", run_tracker_node)
graph.add_node("run_gsc", run_gsc_node)
graph.add_node("run_improvement_pipeline", run_improvement_pipeline_node)
graph.add_node("await_approval", await_approval)
graph.add_node("run_implementation", run_implementation_node)

graph.set_entry_point("load_config")
graph.add_conditional_edges("load_config", route_after_config, {...})
graph.add_edge("run_tracker", "run_gsc")
graph.add_conditional_edges("run_gsc", route_after_gsc, {
    END: END,                                    # tracker_only stops here
    "run_improvement_pipeline": "run_improvement_pipeline",  # full run continues
})
graph.add_edge("run_improvement_pipeline", "await_approval")
graph.add_edge("await_approval", "run_implementation")
graph.add_edge("run_implementation", END)
```

---

## File Structure

### New files

| File | Purpose |
|------|---------|
| `agents/src/improvement/__init__.py` | Package init |
| `agents/src/improvement/crawlability.py` | Step 1: robots.txt, JS check, CDN check, sitemap, meta tags |
| `agents/src/improvement/inventory.py` | Step 2: site crawl, page data extraction |
| `agents/src/improvement/matcher.py` | Step 3: SBERT embedding + cosine similarity matching |
| `agents/src/improvement/scorer.py` | Step 4: deterministic structural checks + Sonnet quality call |
| `agents/src/improvement/gap_check.py` | Step 5: competitive gap lookup from tracker data |
| `agents/src/improvement/reddit_scout.py` | Step 5b: Google search proxy for Reddit threads |
| `agents/src/improvement/card_generator.py` | Step 6: rule-based classification + Sonnet specifics |
| `agents/src/improvement/pipeline.py` | Orchestrator: runs Steps 1-6 sequentially, returns state |
| `agents/src/improvement/validators.py` | JSON-LD validation, HTML check, link check |
| `agents/src/implementors/webflow_impl.py` | Webflow staging implementation |
| `supabase/migrations/008_improvement_pipeline.sql` | All new tables, columns, indexes, RLS |

### Modified files

| File | Changes |
|------|---------|
| `agents/src/graph/state.py` | New fields, remove audit fields |
| `agents/src/graph/pipeline.py` | Replace audit/recommender nodes with improvement pipeline node |
| `agents/src/graph/nodes.py` | Add `run_improvement_pipeline_node`, remove `run_audit_node` and `run_recommender_node` |
| `agents/server.py` | Add `/api/schedules` GET endpoint, add LangSmith env vars |
| `agents/requirements.txt` | Add `sentence-transformers` |

### Kept but unused after migration

These files are NOT deleted (existing runs reference them) but are no longer called by the pipeline:

| File | Status |
|------|--------|
| `agents/src/auditor.py` | No longer called from pipeline |
| `agents/src/recommender.py` | No longer called from pipeline |
| `agents/src/scorers.py` | Partially reused (schema scoring logic) |
| `agents/src/reddit_scout.py` | Replaced by `improvement/reddit_scout.py` (new Google proxy approach) |

---

## Cost Per Cycle

| Step | Method | Cost |
|------|--------|------|
| 1. Crawlability | HTTP requests | ~$0 |
| 2. Site inventory | HTTP crawl | ~$0 |
| 3. Query-page matching | SBERT local | ~$0 |
| 4. Citation scoring | Deterministic + 1 Sonnet/page | ~$0.02/page |
| 5. Gap check | Math on existing data | ~$0 |
| 5b. Reddit scout | Google search | ~$0 |
| 6. Card generation | Rules + 1 Sonnet/card | ~$0.02/card |

**Estimated new cost per cycle** (10 queries, ~6 matched pages, ~5 action cards): **~$0.22**

**Existing tracker cost per cycle** (10 queries × 4 engines × 5 runs): **~$0.19**

**Total per cycle per client: ~$0.41**

---

## Dependencies

| Component | Package/Service | Notes |
|-----------|----------------|-------|
| SBERT embeddings | `sentence-transformers` (PyPI) | `all-MiniLM-L6-v2`, 80MB, CPU-only |
| JSON-LD validation | Built-in `json` + structural checks | No new dependency |
| Content scoring | Claude Sonnet API | Already in use |
| Action generation | Claude Sonnet API | Already in use |
| Reddit scouting | `httpx` (already installed) | Google search, no API key |
| Webflow staging | Webflow CMS API | New integration |
| LangSmith tracing | `langsmith` (already installed via `langchain`) | Config only |

---

## What This Spec Does NOT Cover

- **Frontend/dashboard changes** — deferred to unified frontend pass after all backend
- **Content gap page creation automation** — v1 is manual track with content briefs
- **Fine-tuning SBERT** — v1 uses pretrained model, evaluate accuracy first
- **Monthly/quarterly reporting changes** — existing reports unaffected
