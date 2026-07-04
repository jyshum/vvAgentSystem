# AI Visibility Improvement Pipeline — Research & Design Decisions

> This document captures all research findings, design decisions, and open concerns from the Phase 5+ brainstorming sessions (July 2-3, 2026). This is NOT the final spec — it's the working document that the spec will be built from.

---

## Context: What Changed

The original Phase 5 was "Gap-Closing Workflow" — a narrow feature to diagnose competitive gaps and generate actions. Through brainstorming, we discovered that the entire audit/recommender pipeline needs reworking. The current system (6-pillar audit scoring every page, generating 55+ action cards) is being replaced with a sequential, gap-driven pipeline.

**What stays unchanged:** Tracker (Phase 1), Competitive Gaps (Phase 2), Stability Tracking (Phase 3), Query Management (Phase 4). These are solid and complete.

**What gets replaced:** The audit → recommender → implementation pipeline.

---

## Industry Research Summary

### Lumar 4-Pillar GEO Framework

The most structured industry framework. GEO is a sequential funnel — fix each layer in order:

1. **Technical GEO** — Can AI bots access your site? (robots.txt, SSR, crawl errors)
2. **Content GEO** — Is content answer-ready? (structure, citations, E-E-A-T)
3. **Entity GEO** — Does AI recognize your brand as a distinct entity? (schema, databases, consistency)
4. **Brand Authority GEO** — Does AI trust you enough to cite? (press, Reddit, reviews, awards)

Key insight: These are sequential, not parallel. Fixing content doesn't help if bots can't crawl you.

Source: https://www.lumar.io/blog/best-practice/4-pillar-geo-strategy-framework-for-ai-search-visibility/

### Goodie's Approach (Closest Competitor to What We're Building)

- Gap-first: compare client assets to sources AI cites for competitors
- Recommendations across 4 categories: owned content, earned media, technical, social/entity
- Priority calculated from: competitive gap size, current mention rate, prompt volume
- Each recommendation has: difficulty level, estimated timeline, projected impact on citation rate
- Limitation: "The tool gives recommendations, content suggestions, optimization paths, but someone needs to execute"
- Revenue: $1.2M by end of 2025, ~21 employees, pricing starts ~$495/month
- Goodie 2.0 launching with "function-specific agents" to bridge monitoring-to-execution gap — meaning they haven't solved it yet

Source: https://higoodie.com/features/ai-optimization-actions/

### Profound ($1B Unicorn)

- Runs 15M+ prompts/day across AI engines
- Tracks which pages AI crawlers visit and how often
- Agent-based automation: drafts content briefs, landing pages, optimizations
- Can auto-publish to WordPress, Sanity, Contentful via integrations
- But: "optimization features are light and execution still requires external tools"
- Inner mechanics are a black box — no public documentation of how they bridge visibility data to page-level actions

Source: https://www.rankability.com/blog/profound-ai-review/

### What Actually Drives AI Visibility (Hard Data)

| Factor | Evidence |
|---|---|
| Domain authority (32K+ referring domains) | 3.5x more likely to be cited by ChatGPT |
| Community platforms (Reddit, Quora) | Capture 52.5% of citations across ChatGPT, Perplexity, Google AI Overviews |
| Earned media | Drives 84% of AI citations. Press releases <2% |
| Content structure (organized headings) | 2.8x more likely to earn citations |
| First 30% of content | 44% of ChatGPT citations come from the first 30% of page text |
| Princeton GEO research | Citing sources +30%, statistics +32%, quotations +41% |
| Content freshness | Citation rates drop sharply after 3 months |
| Core Web Vitals fixes | One case study: 189% citation rate increase just from CWV fixes |
| Google SEO vs GEO divergence | Overlap between top Google links and AI-cited sources dropped from 70% to below 20% |

Sources:
- https://otterly.ai/blog/the-ai-citations-report-2026/
- https://almcorp.com/blog/chatgpt-citations-study-44-percent-first-third-content/

### GEO-SFE Research Framework (University of Tokyo, March 2026)

Structural optimization alone (independent of content quality) produces 17.3% improvement in AI citation rates.

| Structural Element | Citation Rate Improvement |
|---|---|
| Comparison table | 2.5x baseline |
| Answer-first block (first 150 words) | 1.9x baseline |
| Numbered list | 1.8x baseline |
| Bold declarative claim block | 1.6x baseline |
| FAQ section (query format) | 1.5x baseline |

Pages scoring GEO-16 quality >=0.70 with 12+ pillar hits achieved 78% cross-engine citation rate.

Virginia Tech: targeted structural interventions on 5% of content yielded 40% improvement vs 25% for generic full-content rewrites.

Source: https://machinerelations.ai/research/content-structure-ai-citation-rates-2026

### Case Study: 0 to 1,631 Citations in 12 Months

Workflow:
1. Weeks 1-3: Technical fixes (images, scripts, CDN, Core Web Vitals)
2. Weeks 4-8: Content restructuring (answer-first, question headings, FAQ/HowTo/Article schema, E-E-A-T, expand depth)
3. Weeks 9-24: Community validation (authentic Reddit participation by actual experts)
4. Ongoing: Measure and iterate

Critical: No shortcuts. Fixed technical before content, content before authority. Multi-signal authority required — no single factor was sufficient.

Source: https://medium.com/@makarenko.roman121/ai-search-optimization-case-study-from-zero-visibility-to-1-631-citations-across-chatgpt-9a40817f6cf1

---

## The Redesigned Pipeline

### Design Principle

The two sides of the pipeline (query-level competitive gaps and page-level site quality) are unified into a single sequential workflow where each step depends on the previous one. No branching, no parallel paths.

The tracker data doesn't start the workflow — it validates it at the end. The sequence is:

```
Crawlability → Site inventory → Query matching → Page scoring → Gap ranking → Action → Tracker validates
```

### Step 1: Crawlability Gate

**Purpose:** Verify AI bots can access the client's website. If blocked, nothing else matters.

**Checks (all deterministic, no API cost):**

1. **robots.txt — AI bot user agents**
   - OpenAI: GPTBot (training), OAI-SearchBot (search indexing), ChatGPT-User (real-time retrieval)
   - Anthropic: ClaudeBot, Claude-SearchBot, anthropic-ai
   - Google: Google-Extended (AI training), Googlebot (AI Overviews)
   - Perplexity: PerplexityBot
   - Check for Disallow rules blocking any of these

2. **JavaScript rendering check**
   - GPTBot skips JavaScript entirely — only reads static HTML
   - Test: fetch key pages, check if critical content appears in raw HTML without JS
   - If content disappears without JS → needs SSR, major blocker

3. **CDN/hosting-level blocks**
   - Cloudflare and other CDNs sometimes block non-browser user agents by default
   - Test: actual HTTP response when fetching with AI bot user-agent headers

4. **XML sitemap**
   - Must be accessible, up-to-date, referenced in robots.txt

5. **Meta tags**
   - Check for nosnippet (prevents AI citation even if crawlable)
   - Check for noindex on key pages

6. **llms.txt**
   - Proposed standard, but NO major AI company (OpenAI, Anthropic, Google) actually reads it yet
   - Zero visits from any AI crawler to llms.txt files in testing
   - Generate as a bonus/forward-looking step, don't gate on it

**Gate behavior:** If critical blocker found → single high-priority action card: "Fix crawler access." Pipeline stops here.

### Step 2: Site Inventory

**Purpose:** Crawl the client's site and build a topic inventory of what the site covers.

**For each page extract:**
- URL, title, H1, first paragraph
- Existing schema types (parse JSON-LD from page)
- Word count
- Last-modified date
- Outbound link count (for citation density)

**No scoring at this step.** Just inventory.

### Step 3: Query-Page Matching

**Purpose:** For each active target query, find the best-matching page from the inventory. This is the critical bridge between query-level data and page-level actions.

**Method: SBERT sentence embeddings + cosine similarity**

- Embed each page's "title + H1 + first paragraph" using pretrained all-MiniLM-L6-v2 (80MB model, runs locally, no API cost)
- Embed each target query
- Compute cosine similarity between query and all page embeddings
- Confidence thresholds:
  - Score > 0.5 → **Matched** (confident this page addresses the query)
  - Score 0.3-0.5 → **Weak match** (flag for manual review, don't auto-act)
  - Score < 0.3 → **Content gap** (no page on the site covers this topic)

**Why SBERT over keyword overlap:** Keyword overlap misses synonyms and paraphrasing. "Best budgeting tools for med students" would miss "/financial-planning-for-medical-school". SBERT captures semantic meaning.

**Why not fine-tuning for v1:** Our matching task is general-purpose semantic similarity (natural language queries to natural language page titles). Pretrained models handle this well. Fine-tuning helps for domain-specific jargon, which isn't our case.

**Validation plan:** Before deploying, test with existing clients — run their target queries against their site pages, manually verify matches. If accuracy < 90%, reconsider approach.

**Dependency:** Adds sentence-transformers to Python dependencies.

### Step 4: Citation-Readiness Scoring (Matched Pages Only)

**Purpose:** Score only the pages that matched to queries, only on factors research says drive AI citations.

**Method: Deterministic structural checks + one Sonnet call per page for quality judgment**

**Deterministic checks (no API cost):**
- Answer-first: Does the first 150 words contain a direct answer? (check for declarative sentences, absence of filler intro)
- FAQ schema: Present? Valid? How many Q&A pairs? Matches visible page content?
- Comparison tables: Present?
- Numbered/bulleted lists: Count and placement
- Freshness: Last-modified date < 3 months?
- Word count: >= 2,000 with structured sections?
- Source citation count: Outbound links to authoritative domains
- Author attribution: Author name, credentials, "reviewed by" markup present?
- Schema validation: Parse existing JSON-LD, validate against schema.org, flag missing required fields, type-content mismatches, duplicate graphs

**One Sonnet call per matched page (quality judgment):**
- Input: page content + target query + structural check results
- Output: specificity score (1-5), completeness score (1-5), answer directness score (1-5)
- This captures what deterministic checks can't — does the content actually answer the query WELL?

**Why Sonnet not Haiku for this step:** The quality judgment and any schema generation need the higher accuracy. Haiku is fine for content rewrites but not for structured code output.

**Schema-specific handling (3 scenarios):**
1. No schema → action: generate (Sonnet + JSON-LD validation before surfacing)
2. Schema exists but broken → action: fix specific issues (deterministic diagnosis from validator)
3. Schema exists and valid but incomplete → action: suggest additions

**Important research finding:** 78% of sites with deployed schema are silently broken. The most common issues are duplicate Organization graphs, FAQPage on ineligible pages, missing required fields, and type-content mismatches.

**FAQ schema note:** Google reduced FAQ rich results significantly (Aug 2023). FAQ Search Console reporting dropped June 2026. FAQ schema still matters for AI crawlers reading JSON-LD as plain text, but it's not the highest-leverage schema type anymore. Organization + WebSite + BreadcrumbList are the universal baseline.

### Step 5: Competitive Gap Check

**Purpose:** For each matched query, determine if a competitor is beating the client.

**Method:** `competitor_mention_rate - client_mention_rate`. Positive = competitor winning.

- Pull from existing competitive_gaps data (Phase 2, already computed and stored per run)
- Only flag queries where the delta is positive (competitor ahead)
- A gap of 0% (both at 80%) = correctly low priority — both brands winning

**Direction confirmed:** Always `competitor - client`. Positive = losing. Negative = winning.

### Step 5b: Reddit Scout (Gap Queries Only)

**Purpose:** For queries with competitive gaps, check community presence.

**Method: Google search as proxy + RSS feeds**

The Reddit API landscape has changed dramatically:
- Reddit .json endpoints return 403 Forbidden as of May 2026
- Pushshift public access revoked
- Self-service commercial API closed Nov 2025
- Reddit actively suing scrapers (Anthropic, SerpApi)
- PRAW free tier: 100 req/min but terms prohibit commercial use

**Recommended approach:**
- Search `site:reddit.com "[query keywords]"` via Google
- Returns thread URLs, titles, snippets — enough to know if relevant threads exist and if competitors/client are mentioned in titles
- RSS feeds (.rss suffix on subreddit URLs) for monitoring known relevant subreddits
- No legal risk, no API dependency, no rate limiting concerns

**Output per gap query:** "3 Reddit threads found about 'budgeting tools for med students'. CompetitorA in 2 thread titles. Client in 0."

### Step 6: Action Card Generation — Two Tracks

**Ordering principle:**
1. FIRST: Competitive gap pages (page exists but losing) — fix the matched page
2. SECOND: Content gaps (no page exists, competitor winning) — generate content brief (MANUAL)
3. THIRD: General optimization (no gap, just improving page scores)

**Track 1: Automated (agent implements on existing pages)**

Method: Hybrid — rule-based classification determines WHAT action, Sonnet generates SPECIFIC changes.

Rules determine action type (deterministic, never wrong):
- Page missing FAQ schema → "add FAQ schema"
- Page not answer-first → "restructure content"
- Page has 0 inline citations → "add source citations"
- Content older than 3 months → "update freshness"
- Schema exists but broken → "fix schema issues: [specific validator errors]"

Sonnet generates specifics:
- Input: page content + query + rule-identified issue + competitive gap data
- Output: specific before/after text, or exact schema JSON-LD, or rewritten intro paragraph
- Schema output MUST be validated programmatically (JSON-LD validator) before becoming an action card
- If validation fails → card not surfaced

**Track 2: Manual (agency team)**

Content gaps → Content brief (NOT an AI-generated page):
- Target query this page should answer
- Competitive landscape (who appears, what they say)
- Recommended page title and H1
- Key topics/sections to cover
- Specific facts/statistics to include
- Schema type to add
- Internal linking targets
- Word count target
- This goes to the content team (Kaden), not to an automated implementer

Reddit engagement:
- Specific threads surfaced by Step 5b
- Which competitors are mentioned
- Engagement recommendations

Press/media/authority:
- Off-site authority building targets
- Review site listings, directory submissions

### Step 7: Implementation Safety — Preview Before Deploy

**Critical principle: Never touch production directly.**

All automated changes go through a safety layer:

| CMS Type | Safety Mechanism | What Admin Sees |
|---|---|---|
| WordPress | Create draft revision via REST API, generate preview URL | Live preview of page with changes applied, side-by-side with current |
| Webflow | Update on staging subdomain (site.webflow.io), don't publish | Staging URL showing the change |
| GitHub/Headless | Create PR with diff, Vercel preview deployment | PR diff + preview deployment URL |
| Squarespace | N/A — manual only | Action card with exact instructions and code to paste |

**Before surfacing any automated action card:**
1. JSON-LD validator runs on any schema changes
2. HTML parsing check on any content modifications
3. Broken link check on any new outbound links

**Approval flow:**
```
Action card → Implementer creates draft/PR/staging change
→ Admin sees preview URL + before/after diff
→ Admin approves or rejects
→ If approved: publish/merge
→ If broke something: rollback via revision history/revert PR
→ Tracker validates improvement next cycle
```

**Rollback capabilities:**
- WordPress: Built-in revision history, one-click rollback
- Webflow: Restore from backup (no native per-change rollback)
- GitHub: Revert PR
- The cms_type field already exists on our clients table — route implementation by CMS type

### Step 8: Validation (Tracker Closes the Loop)

Next tracker cycle re-measures mention rates for the queries where actions were taken.

- Stability tracking (Phase 3) classifies the trend: gaining, declining, volatile, locked_in, absent
- Reddit scout re-checks community presence
- If mention rate improved → action worked, mark done
- If not → action was wrong or insufficient, surface for human review

The system is self-correcting over cycles. No separate QA layer needed beyond the tracker itself.

---

## Pipeline Node Changes

The LangGraph pipeline becomes:
```
load_config → run_tracker → run_gsc → run_improvement_pipeline → await_approval → run_implementation
```

`run_improvement_pipeline` replaces `run_audit` + `run_recommender`. Runs Steps 1-6 internally as a single sequential process.

---

## Cost Analysis

| Step | Approach | Cost per cycle |
|---|---|---|
| 1. Crawlability | HTTP requests only | ~$0 |
| 2. Site inventory | HTTP crawl | ~$0 |
| 3. Query-page matching | SBERT local model | ~$0 |
| 4. Citation-readiness scoring | Deterministic + 1 Sonnet call per matched page | ~$0.02/page |
| 5. Competitive gap check | Math on existing data | ~$0 |
| 5b. Reddit scout | Google search | ~$0 |
| 6. Action card generation | Rules + Sonnet for specifics | ~$0.02/card |
| 7. Implementation safety | Draft/PR creation | ~$0 |

Estimated total new cost per cycle (8 gap queries, 6 matched pages, 5 action cards): ~$0.20-0.30

On top of existing tracker cost (~$3.25/cycle/client).

---

## Technology Dependencies

| Component | Technology | Notes |
|---|---|---|
| SBERT embeddings | sentence-transformers Python package (all-MiniLM-L6-v2) | 80MB model, runs locally on CPU, no API |
| JSON-LD validation | Python jsonschema or dedicated schema.org validator | Deterministic, no API |
| Content scoring | Claude Sonnet API | 1 call per matched page |
| Action generation | Claude Sonnet API | 1 call per action card |
| Reddit scouting | Google search (site:reddit.com) | Public, no API key needed |
| CMS implementation | WordPress REST API, Webflow CMS API, GitHub API | Per-client CMS type |

---

## Open Concerns (To Address Before Spec)

1. ~~Schema improvements vs generation~~ — RESOLVED: 3 scenarios (missing, broken, incomplete), deterministic diagnosis
2. ~~Content gap = new page creation~~ — RESOLVED: manual track, content brief only, agency team executes
3. ~~Implementation safety~~ — RESOLVED: draft/staging/PR layer, preview URLs, programmatic validation, rollback
4. [USER TO CONTINUE] — any remaining concerns before finalizing spec

---

## Why We Have a Competitive Advantage

- Goodie/Profound sell recommendations but say "someone needs to execute"
- We ARE the execution layer — agency model means we have CMS access, we do the work
- The implementation gap is what nobody has solved at scale
- We can solve it for our specific clients (5-20) without needing a universal CMS abstraction
- Our tracker validates our own implementation — closed loop that SaaS tools can't offer
