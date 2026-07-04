# AI Visibility Tracker — Overhaul Plan

> This document covers the overhaul of Victory Velocity's AI visibility tracker. It transforms the current binary single-run system into a multi-run, multi-signal measurement platform with managed query lifecycle, competitive gap analysis, and a gap-closing workflow. It does NOT cover the full agent system, audit, schema generation, or reporting — those are defined in the existing technical design documents.

---

## 1. What Exists Now and Why It's Indefensible

The tracker queries 4 LLMs (ChatGPT, Perplexity, Claude, Gemini) and checks two booleans per response: `brand_mentioned` and `brand_url_cited`. Each prompt runs once per LLM per cycle.

The SparkToro/Gumshoe study (January 2026, 2,961 prompt runs across ChatGPT/Claude/Google AI with 600 volunteers) established:
- Less than a 1-in-100 chance that any LLM returns the same brand list twice for the same prompt
- Less than a 1-in-1,000 chance of the same list in the same order
- The only metric that survives statistical scrutiny is **visibility percentage across many runs**
- Brands genuinely in a model's "consideration set" appeared consistently (85/95 runs in one tested category) even though exact lists shuffled every time

A single run per prompt is a sample size of one from a highly variable distribution. Reporting this as "you were mentioned" or "you weren't" is noise dressed as signal.

Additional research from Search Engine Land (February 2026) found ChatGPT mentions an average of 44 different brands across 100 runs of the same prompt, but only 6-7 "dominant" brands appear in 80%+ of responses in competitive categories versus 21% in niche categories.

---

## 2. Multi-Run Methodology

### The change

Every prompt runs **5 times per LLM per cycle** instead of once.

### Why 5

5 runs is the minimum defensible sample. It distinguishes "rarely appears" (1/5) from "usually appears" (4/5) from "never appears" (0/5) within acceptable confidence intervals. 10+ runs would be more precise but doubles cost for marginal improvement at current client scale. The tradeoff is statistical rigor vs cost discipline.

### Cost impact

Current: 20 prompts × 4 LLMs × 1 run = 80 calls/cycle → ~$0.64/month per client
Overhauled: 24 prompts × 4 LLMs × 5 runs = 480 calls/cycle → ~$3.20/month per client

With prompt caching (system prompt identical across all calls per LLM): ~$2.20/month per client.

---

## 3. Scoring System

### Design philosophy

The scoring system uses two clean metrics and one contextual metric. No compound formulas. No multipliers. No phantom penalties from LLM platform behavior clients can't control.

### Metric 1: Mention Rate (frequency signal)

How often the brand appears at all. Binary — did the brand show up in this run or not.

```
mention_rate = runs_with_any_mention / total_runs × 100
```

This is the top-line number reported to clients. "Budget Your MD appears in 72% of AI responses for your target queries." Simple, defensible, intuitive.

### Metric 2: Average Mention Level (quality signal)

When the brand IS mentioned, how prominent is the mention? This captures the quality of visibility, not just the quantity.

| Level | Value | Description |
|---|---|---|
| Not mentioned | 0 | Brand doesn't appear |
| Passing mention | 1 | In a list without recommendation — "...resources include Budget Your MD and others..." |
| Listed with context | 2 | Described but not endorsed — "Budget Your MD offers a budget template for medical students." |
| Recommended | 3 | AI actively recommends — "For Canadian med students, Budget Your MD is a great resource..." |
| Primary recommendation | 4 | Lead answer — "The best resource for this is Budget Your MD..." |

```
avg_mention_level = sum(levels_of_runs_where_mentioned) / runs_where_mentioned
```

Only calculated across runs where the brand appeared. Not diluted by zero-mention runs — mention rate already captures frequency.

**Example — 5 runs for one prompt:**
- Run 1: Recommended (3)
- Run 2: Passing mention (1)
- Run 3: Not mentioned (skip)
- Run 4: Listed with context (2)
- Run 5: Recommended (3)

Mention rate: 4/5 = 80%
Average mention level: (3 + 1 + 2 + 3) / 4 = 2.25
Reported as: "80% mention rate, average level: Listed with Context"

### Metric 3: Citation Rate (contextual, reported per LLM)

How often the brand's URL is cited when the brand is mentioned. Reported separately per LLM because citation behavior varies by platform — Perplexity explicitly cites URLs in every response, while ChatGPT, Claude, and Gemini rarely output clickable citations in API responses.

```
citation_rate = runs_where_url_cited / runs_where_mentioned × 100
```

This is NOT multiplied into the mention rate or mention level. It's a separate data point that tells its own story:
- High citation rate on Perplexity + low on others = normal platform behavior, not a client problem
- Low citation rate on Perplexity specifically = the site isn't trusted as a source even when the brand is mentioned — site quality issue

### Why not a combined weighted score

An earlier version of this plan proposed a combined "GEO Score" that multiplied mention weights by citation multipliers. This was rejected for three reasons:

1. **Citation penalties punish 3 out of 4 LLMs.** ChatGPT, Claude, and Gemini almost never cite URLs in API responses. A brand recommended everywhere would score ~58% because three platforms can't produce citations. The score would reflect LLM platform behavior, not client GEO quality.

2. **Passing mentions at low weight produce demoralizing scores.** A brand mentioned in every response as a passing mention would score 25%. But being in the consideration set at all is a win for a new client. The number contradicts the actual story.

3. **Multiple compound scores confuse clients.** "Your mention rate is 80% but your GEO score is 38%" — which one matters? Clients pick whichever looks best and ask why the other is lower. Now you're defending your scoring system instead of discussing strategy.

Two clean numbers (mention rate + average level) tell the full story without any of these problems.

### How the upgrade story works

"Your mention rate went from 60% to 75% AND your average level went from 1.5 to 2.8 — you're not just appearing more often, you're being recommended instead of just listed."

Two numbers, one coherent narrative, no confusion.

---

## 4. Mention Classification

### Implementation

After detecting a mention via string match, send the response snippet to Claude Haiku for classification:

"How is [brand_name] positioned in this AI response? Classify as one of: passing_mention, listed_with_context, recommended, primary_recommendation. Respond with only the classification."

One additional Haiku call per detected mention. At ~40% mention rate across runs, approximately 192 extra calls per cycle per client. Cost: ~$0.04/month per client. Negligible.

### Industry validation

Goodie tracks "answer positioning and depth." Writesonic tracks how AI talks about the brand. Our 4-level classification (excluding "not mentioned" which is the absence of classification) captures both positioning and recommendation strength in one metric.

---

## 5. Mention × Citation Overlap Diagnosis

Cross-reference mention level and citation rate to produce actionable diagnoses. The diagnosis changes based on mention quality, not just binary mentioned/not mentioned.

### High mention level (avg 3-4: Recommended or Primary) + High citation rate
**Diagnosis:** Best possible position. AI recommends the brand AND trusts the site.
**Action:** Protect. Keep content fresh. Don't change what's working.
**Priority:** Low — maintenance only.

### High mention level (avg 3-4) + Low citation rate
**Diagnosis:** Brand authority is strong — AI confidently recommends you. But the site isn't earning citation trust. This is the closest gap to close.
**Action:** Fix site quality — improve content structure, add schema, increase fact density, add source citations. The brand recognition is already there; the site needs to catch up.
**Priority:** High — easiest win. One step from the best position.

### Low mention level (avg 1-2: Passing or Listed) + High citation rate
**Diagnosis:** Unusual but real. Site content is useful enough to be linked as a reference, but the brand isn't prominent in the AI's recommendation. The LLM uses your page but doesn't endorse your brand.
**Action:** Build brand authority — Reddit mentions, press coverage, review sites, directory listings. The site is working; the brand needs more corroboration across the web.
**Priority:** Medium — requires off-site work which is slower.

### Low mention level (avg 1-2) + Low citation rate
**Diagnosis:** Barely visible. In the consideration set but not confidently. Both brand and site are weak.
**Action:** Everything simultaneously — content, schema, authority. Prioritize content first because you can't be recommended for something if no page targets that query.
**Priority:** High — but more work than the "high level + low citation" case.

### Not mentioned (avg 0)
**Diagnosis:** Invisible regardless of citation.
**Action:** Check if the prompt produces brand mentions for anyone. If yes, competitive gap — audit the competitors who appear. If no brands appear, consider retiring the prompt from the core set.
**Priority:** Depends on competitive analysis.

---

## 6. Competitive Gap Matrix

### The change

Structure competitor data as a prompt-level comparison showing both mention rate and quality, not just aggregate counts.

| Prompt | Client | Competitor A | Competitor B | Reddit/Forum |
|---|---|---|---|---|
| "best budgeting tools..." | 0% (absent) | 80% @ avg 3.2 (recommended) | 40% @ avg 1.5 (listed) | 3/5 cited |
| "how to manage LOC..." | 60% @ avg 1.8 (listed) | 20% @ avg 3.0 (recommended) | 0% | 5/5 cited |

### What the matrix reveals

**Coverage gaps:** First row — client is absent, competitors dominate. Highest priority.

**Quality gaps:** Second row — client appears more often (60% vs 20%) but at lower quality (listed vs recommended). The action isn't "appear more" — it's "get upgraded from listed to recommended." Binary-only tracking would miss this entirely.

**Authority signals:** When Reddit/forums are cited as primary sources, the gap is authority, not content. The action is community engagement, not page creation.

### Auto-discovery

When a brand NOT in the client's competitor list appears in 3+ runs for the same prompt, flag it as a discovered competitor and surface in the dashboard.

### Crowd-source detection

When reddit.com, quora.com, or similar domains are the primary citation source for a prompt, flag it. The action is authority building (engagement in those communities), not content creation.

---

## 7. Stability Tracking

### The change

Track whether each prompt's visibility is stable, improving, volatile, or declining across a 3-cycle rolling window.

| Pattern | Classification | Action |
|---|---|---|
| Consistent high mention rate + level for 3 cycles | **Locked in** | Protect |
| Trending upward (rate or level increasing) | **Gaining** | Continue current strategy |
| Trending downward (rate or level decreasing) | **Declining** | Investigate — competitor move, content staleness, model update |
| High variance in rate or level across cycles | **Volatile** | Highest-leverage optimization target |
| Consistent 0% mention rate for 3 cycles | **Absent** | Drop prompt or full GEO cycle |

### Why volatile matters most

A volatile prompt means the brand is on the edge of the model's consideration set — sometimes included, sometimes not. A targeted content or authority push can stabilize it permanently. These are the lowest-effort, highest-impact opportunities for the agency. No competitor tool surfaces this signal explicitly.

### Stability uses both metrics

A prompt could be stable in mention rate (80% every week) but volatile in mention level (fluctuating between passing mention and recommended). That's a quality instability — the brand is consistently present but inconsistently endorsed. The action is different from a frequency instability where the brand appears some weeks and disappears others.

---

## 8. Query Management System

### Why queries need management

Queries are the foundation of every downstream metric. If the query set changes silently, trend lines become meaningless. If queries aren't validated before inclusion, you track prompts with no commercial signal. If queries aren't organized by buyer journey stage, branded prompts inflate category visibility numbers.

### Query data model

Queries are a managed entity, not a flat array in client config.

| Field | Type | Description |
|---|---|---|
| id | uuid | Primary key |
| client_id | text | FK to clients |
| prompt_text | text | The full natural-language prompt |
| slug | text | Versioned identifier, e.g. "budgeting_med_student_v1" |
| bucket | text | awareness, consideration, or branded |
| set_type | text | core or discovery |
| status | text | pending_validation, active, retired |
| validation_result | jsonb | Output of validation pipeline |
| version | integer | Incremented on any text change |
| promoted_from_discovery_at | timestamp | Null unless promoted |
| retired_at | timestamp | Null unless retired |
| created_at | timestamp | |

### Three buckets (reported separately, never combined)

**Awareness (8-12)** — problem-focused, no brand names. "How to budget as a medical student in Canada." Tests category-level visibility.

**Consideration (8-12)** — solution-comparing. "Best budgeting tools for medical students." Highest commercial impact.

**Branded (4-6)** — includes client brand name. "Budget Your MD review." Almost always surfaces the brand. Tracked separately to avoid inflating category scores.

Category visibility = awareness + consideration averaged. Brand accuracy = branded bucket. These are distinct metrics, never merged.

### Core set vs discovery set

**Core (20-30 prompts):** Versioned. Any text edit creates a new version (`_v1` → `_v2`). Stability tracking and gap matrix operate on this set. Trend data stays comparable because the denominator doesn't change.

**Discovery (5-10, rotating):** Experimental. NOT included in the visibility score. Promoted to core if consistent gaps appear over 2-3 cycles. Retired if no signal.

### Query generation process

**Step 1 — Client onboarding call.** Ask:
- "What do customers ask before signing up?" → awareness prompts
- "Who are your competitors?" → consideration + branded prompts
- "What's the main reason someone doesn't sign up?" → objection-based awareness
- "Which products are priority?" → focuses consideration prompts

Walk away with 10-15 raw phrases.

**Step 2 — Expansion.** Convert raw phrases to natural first-person prompts. Add persona and location variants. Pull question-shaped queries from GSC if available (filter: how/what/why/best/should, 5+ words). Target: ~35 candidates.

**Step 3 — Automated validation pipeline.** The system runs each candidate 3-5 times across all 4 LLMs automatically. Reports per prompt:
- Total unique brands detected across all runs
- Whether the client appeared
- Whether any competitor appeared
- Whether responses were factual explainers (zero brands) or recommendation-style

Prompts with zero brands across all runs → flagged as "no commercial signal." Recommend dropping. This filter eliminates 30-40% of candidates.

**Step 4 — Organize and lock.** Surviving prompts assigned to buckets, set type, and versioned slug. Core set is locked.

**Step 5 — Ongoing: competitive gap mining.** After 2-3 cycles, the gap matrix surfaces prompts where competitors appear but the client doesn't. System flags these as "candidate for discovery set" in the dashboard with an "add to tracking" button. Discovery prompts showing consistent gaps over 2-3 cycles → system recommends promotion to core.

### Query sources ranked by quality

1. **Client sales/support knowledge** — real language from real users
2. **Competitive gap mining** — data-driven from tracker results
3. **Google Search Console** — real queries with real impressions, filtered to question format
4. **Reddit/forum mining** — how people actually phrase questions in the category
5. **LLM-generated** — lowest quality, introduces phrasing bias, use only to fill gaps

### Dashboard: query management view

Per-client list of all tracked prompts showing: prompt text, bucket, set type (core/discovery), mention rate, average mention level, stability class, version. Actions: add (triggers validation), retire, move between buckets, promote discovery → core.

---

## 9. Gap-Closing Workflow

The tracker and gap matrix identify WHERE gaps exist. This section defines HOW to close them.

### Step 1 — Gap identified from matrix

A prompt surfaces where competitor appears 80% @ recommended and client appears 0%.

### Step 2 — Diagnose why the competitor wins

The tracker captures full response text for every run. For the gap prompt, extract from the stored responses:
- What is the AI saying about the competitor?
- What source is being cited? (Perplexity shows URLs explicitly)
- Is the competitor winning because of a specific page, a Reddit thread, reviews, or general authority?

This determines gap type: content (they have a page, you don't), authority (they're mentioned across Reddit/review sites, you're not), or structural (their page has better schema/formatting).

### Step 3 — Check what the client has

The audit agent checks: does a relevant page exist on the client's site targeting this query topic? If yes, what are its pillar scores? If no, that's the gap — no page exists.

### Step 4 — Generate the action

Based on gap type:

**Content gap (no page exists):** Content recommendation agent generates a brief for Kaden — title, headings, key facts, sources to cite, schema type.

**Content quality gap (page exists, scores poorly):** Audit shows which pillars are weak. Agent generates specific fixes — "restructure intro to answer-first, add 3 statistics, convert H2s to questions."

**Schema gap (page exists, content fine, no schema):** Schema agent generates JSON-LD immediately. Fastest win — deployable same day.

**Authority gap (page and content fine, not mentioned enough across web):** Surfaced as manual action — "Budget Your MD is not mentioned in Reddit threads about medical student budgeting. Top 3 threads on r/personalfinancecanada mention MD Financial. Engage in these threads." Reddit scout surfaces the specific posts.

### Step 5 — Measure impact

Next cycle runs the same 5 runs for the same prompt. Did mention rate change? Did mention level upgrade from listed to recommended? Stability tracker classifies the trend.

This closes the loop: measure → diagnose → act → measure again.

---

## 10. Data Schema Changes

### Modified: tracker_results

New columns added to existing table:

| Column | Type | Description |
|---|---|---|
| run_number | integer | Which run (1-5) for this prompt × LLM pair |
| mention_level | integer | 0-4 (not_mentioned through primary_recommendation) |
| mention_level_label | text | Human-readable classification label |
| competitor_mentions | jsonb | Array of {name, mention_level} per competitor |
| non_configured_entities | text[] | Brands detected not in competitor list |
| source_urls_cited | text[] | URLs cited in response (primarily from Perplexity) |
| crowd_source_dominant | boolean | Whether Reddit/Quora/forums are primary citation |

### New: queries

Full schema defined in Section 8.

### New: prompt_scores (aggregated per prompt per cycle)

| Column | Type | Description |
|---|---|---|
| cycle_id | uuid | FK to cycles |
| query_id | uuid | FK to queries |
| client_id | text | FK to clients |
| llm | text | Which engine |
| mention_rate | numeric | Binary appearances / total runs × 100 |
| avg_mention_level | numeric | Average level across mentioned runs (0-4 scale) |
| citation_rate | numeric | Cited runs / mentioned runs × 100 |

### New: prompt_stability

| Column | Type | Description |
|---|---|---|
| client_id | text | FK to clients |
| query_id | uuid | FK to queries |
| current_mention_rate | numeric | Latest cycle |
| current_avg_level | numeric | Latest cycle |
| prev_1_mention_rate | numeric | Previous cycle |
| prev_1_avg_level | numeric | Previous cycle |
| prev_2_mention_rate | numeric | Two cycles ago |
| prev_2_avg_level | numeric | Two cycles ago |
| stability_class | text | locked_in, gaining, declining, volatile, absent |

### New: competitive_gaps

| Column | Type | Description |
|---|---|---|
| cycle_id | uuid | FK to cycles |
| client_id | text | FK to clients |
| query_id | uuid | FK to queries |
| client_mention_rate | numeric | Client appearance rate |
| client_avg_level | numeric | Client average mention level |
| competitor_data | jsonb | Array of {name, mention_rate, avg_mention_level} |
| gap_type | text | content, authority, schema, unknown |
| gap_priority | text | high, medium, low |

---

## 11. What the Client Report Looks Like

### Before (current)

```
Budget Your MD: Mentioned on ChatGPT — Yes. Cited on Perplexity — No.
```

### After

```
Budget Your MD — AI Visibility Report

Mention Rate: 60% → 72% (↑12%)
Average Mention Level: 1.5 → 2.8 (Listed → approaching Recommended)

STRONGEST POSITION
"How to budget as a medical student in Canada"
  Mention rate: 100% | Avg level: 3.8 (Primary recommendation / Recommended)
  Citation rate on Perplexity: 80%
  Status: Locked in (4 consecutive weeks)

BIGGEST OPPORTUNITY
"Best budgeting tools for medical students"
  Your visibility: 0% (absent)
  MD Financial: 80% @ avg 3.2 (recommended)
  Reddit: cited as primary source in 3/5 runs
  Gap type: Content — no page targets this query
  → Create comparison page

QUALITY UPGRADE NEEDED
"Financial planning for Canadian medical residents"
  Mention rate: 60% — you appear often
  But avg level: 1.5 — only as a passing mention
  → Improve content depth to move from "listed" to "recommended"

CLOSE TO BREAKING THROUGH
"Medical school debt repayment Canada"
  Mention rate: fluctuating 20%-80% over 3 cycles
  Status: Volatile
  → A targeted content push could lock this in permanently
```

---

## 12. Implementation Priority

| Priority | What | Depends On |
|---|---|---|
| 1 | Query data model + validation pipeline | Nothing |
| 2 | Multi-run execution (5 runs per prompt per LLM) | Queries table |
| 3 | Mention rate calculation | Multi-run data |
| 4 | Mention classification (4-level via Haiku) + avg mention level | Mention detection |
| 5 | Competitive gap matrix with mention rate + avg level | Multi-run data |
| 6 | Citation rate as separate per-LLM metric | Existing citation field |
| 7 | Mention × citation overlap diagnosis | Both fields + mention level |
| 8 | Stability tracking (3-cycle rolling window on rate + level) | 3 cycles of data |
| 9 | Gap-closing workflow (connects to audit + recommendation agents) | All above |
| 10 | Dashboard: query management + gap matrix + stability views | Data populated |

Items 1-5 can ship in the same build cycle. 6-7 are additive layers. 8 requires 3 weeks of weekly data. 9-10 are UI and integration.

---

## 13. Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Runs per prompt | 5 | Minimum defensible sample. Validated by SparkToro. |
| Scoring system | Mention rate + avg mention level (two metrics) | Clean, intuitive, no phantom penalties. Combined weighted scores were rejected — they produce demoralizing numbers and penalize for LLM platform behavior. |
| Citation handling | Separate per-LLM metric, NOT multiplied into score | Citation behavior varies by platform (Perplexity cites URLs, others rarely do). Baking it into the score punishes clients for something they can't control. |
| Classification | 4-level via Haiku | Distinguishes quality, not just quantity. ~$0.04/month cost. |
| Query versioning | Slug with version number, never silently edited | Trend lines meaningless if denominator changes. |
| Branded bucket | Never combined with awareness/consideration | Branded prompts inflate category scores. Industry standard (Conductor, Profound). |
| Validation | Automated 3-5 run filter before inclusion | Eliminates 30-40% of prompts with no commercial signal. |
| Discovery-to-core | 2-3 cycles of consistent gap required | Prevents premature locking of untested prompts. |
| Stability window | 3 cycles, tracking both rate and level | Catches both frequency instability and quality instability. |
| Query generation | Client knowledge first, data-driven expansion second | LLM-generated prompts are lowest quality source. |
