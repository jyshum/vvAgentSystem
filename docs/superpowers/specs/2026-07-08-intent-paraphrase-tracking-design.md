# Intent-Based Visibility Tracking with Paraphrase Sampling — Design Spec

**Date:** 2026-07-08
**Status:** Approved (brainstorm)
**Scope:** Backend only (Spec 1 of 2). The dashboard adapts in a follow-up frontend spec.

---

## Goal

Restructure the tracker so the unit of measurement is a buyer **intent** (fired as several **paraphrases**), fix the scoring so every number uses one honest **non-branded** denominator, preserve the 0–4 mention-level signal throughout, and record when the query set changes so trends stay interpretable. Generation of intents/paraphrases stays **manual** (an off-platform LLM chat), so nothing here builds a generation pipeline.

## Why (context)

Today the tracker fires **one prompt string 5× per engine**. Three problems, confirmed against GEO/AEO research and the code:

1. **Phrasing variance dominates run variance.** Rewording a query moves the result more than re-running the same words. Repeating one phrasing 5× samples the *weaker* noise source and leaves the dominant one — phrasing — unsampled. A single-phrasing mention rate "is not a proxy for the brand's wider visibility across the buyer's natural paraphrase distribution." This matters most for challenger brands (all four current clients), which appear under one phrasing and vanish under another.
2. **Inconsistent denominators.** `tracker.py` already excludes `branded` from the aggregate mention rate, but `per_engine` still includes branded — so per-engine numbers are inflated relative to the headline.
3. **Branded queries are recall, not discovery** and don't belong in a visibility metric at all.

## Decisions carried in from the brainstorm

- **Intent is the unit;** paraphrases supply sampling volume (fired once each) so cost stays near today's while capturing the dominant variance source.
- **Generation is manual** — an LLM chat fed the client's site + GSC top queries + a rules paragraph. No generation code.
- **Branded: deferred.** Not fired, clients aren't asked to define them; the `branded` enum value stays and the exclusion logic stays as dormant, correct infrastructure.
- **Comparison: deferred.** Folded into `consideration`; no comparison-aware card routing (you can't reliably identify a client's competitors without asking them).
- **Card-routing logic is unchanged** — it simply receives more accurate, intent-level gap data. Consideration queries keep getting website-edit cards.
- **Headline weighting: equal weight per intent** (mean of non-branded intent rates), not per bucket.
- **Frontend is a separate later spec** (Spec 2), designed against the real data this backend produces.

## Scope

**In scope:**
1. Data model: `queries.paraphrases`; `tracker_runs.query_set_signature` + `query_set_changed`.
2. Tracker: fire an intent's paraphrases; store per-wording results; aggregate at the intent level.
3. Measurement correctness: non-branded everywhere (per-engine included), mention-level preserved, citation conditional on mention.
4. Drift signal: per-run query-set signature + changed flag.
5. Generation rules doc (a markdown deliverable, not code).

**Out of scope (explicit):**
- All frontend/dashboard changes → Spec 2.
- Automated intent/paraphrase generation; embedding-based diversity selection.
- Comparison bucket and comparison-aware (off-page) card routing.
- Branded tracking / branded reputation monitoring (a separate product).
- Card-generation *routing* changes (logic unchanged; only its input data improves).

---

## Data model

### `queries` (add one column)

```sql
alter table public.queries add column if not exists paraphrases jsonb default '[]'::jsonb;
```

- Each `queries` row is now **one intent**.
- `prompt_text` = the **canonical wording** — the intent's label and one of the fired phrasings.
- `paraphrases` = a JSON array of additional wordings. The set fired per intent = `[prompt_text] + paraphrases`.
- `bucket` enum unchanged (`awareness` | `consideration` | `branded`). Only `awareness` and `consideration` are actively fired; `branded` still validates but the tracker skips it. Comparison prompts are filed as `consideration`.
- `version`, `status`, `retired_at` unchanged — they support the drift model (below).

### `tracker_runs` (add two columns)

```sql
alter table public.tracker_runs add column if not exists query_set_signature text;
alter table public.tracker_runs add column if not exists query_set_changed boolean default false;
```

### Admin API

`POST/PATCH /api/admin/queries/[clientId]` accepts an optional `paraphrases: string[]` alongside `prompt_text`, `bucket`, `set_type`, and stores it. (This is the paste target for the manual generation chat's output. Validate it's an array of non-empty strings.)

### `schema.sql`

Fold both changes into the canonical `supabase/schema.sql` and ship a small incremental migration for the live database.

---

## Tracker firing

For each **active** (`awareness` | `consideration`) intent:

- Build `fire_list = [prompt_text] + paraphrases`.
- Fire each wording **once per engine** (same async fan-out as today; `runs_per_paraphrase = 1` default, configurable).
- Each `tracker_results` row carries: `run_id`, `query_id` (the intent), `query` (the specific wording), `bucket`, `engine`, `model`, `brand_mentioned`, `brand_cited`, `mention_level`, `mention_level_label`, `citation_url`, `competitor_mentions`, `response_text`, `run_number`, `queried_at`.

Branded intents are not fired (dormant). If `runs_per_paraphrase` > 1, each wording is fired that many times (all count as samples).

Example: an intent with 8 paraphrases + 1 canonical, across 4 engines, at 1 run each = **36 samples**.

---

## Aggregation (exact formulas)

**Sample** = one `(wording × engine × run)`. Yields `mentioned ∈ {0,1}`, `mention_level ∈ {0..4}`, `cited ∈ {0,1}` (only meaningful when `mentioned`).

**Intent** (`query_id`), over all its samples:
- `mention_rate = mentioned_samples / total_samples`
- `avg_mention_level = mean(mention_level over MENTIONED samples)` (absences are never counted as level 0 — that would conflate "invisible" with "mentioned weakly"); `0` when no mentions.
- `citation_rate = cited_samples / mentioned_samples` (conditional; `0` when no mentions).

**`prompt_scores`** — one row per **(intent × engine)** with the three metrics computed over that engine's samples for the intent. Grouping key changes from `(query_text, engine)` → `(query_id, engine)`. `query` stores the canonical `prompt_text`; `bucket` and `query_id` populated.

**`tracker_runs` (run-level, non-branded only):**
- `aggregate_mention_rate` (= headline = `non_branded_mention_rate`): **mean of intent `mention_rate` over all non-branded intents** (equal weight per intent).
- `aggregate_avg_mention_level`: mean of `mention_level` **pooled over all mentioned non-branded samples** ("when we show up, how prominently").
- `bucket_scores`: `{ awareness: {...}, consideration: {...} }`, each `{ mention_rate: mean of intent rates in the bucket, avg_mention_level: pooled over the bucket's mentioned samples, citation_rate: pooled cited/mentioned over the bucket, intent_count: n }`.
- `per_engine_scores`: per engine `{ mention_rate, avg_mention_level, citation_rate }` computed **over non-branded intents only** (fixes today's inconsistency; branded currently absent, but the exclusion is explicit).
- `competitor_scores`: competitor mention rates over non-branded samples.

**`competitive_gaps`** — one row per intent, computed across the intent's paraphrases, non-branded. Competitor detection runs on every paraphrase response, so gaps get more accurate. Feeds card generation unchanged.

**What is preserved:** `mention_level` at every level (over mentioned samples), conditional `citation_rate`, per-engine breakdown, `discovered_competitors`, GSC metrics. Their *values* now reflect the non-branded, intent-averaged basis.

---

## Drift signal

At run time, compute a **query-set signature**:

```
signature = sha256( join sorted over active intents of:  f"{slug}:{version}:{sha256(sorted paraphrases + prompt_text)}" ) )
```

- Store `query_set_signature` on the run.
- Set `query_set_changed = (signature != previous run's signature for this client)`.
- The signature changes on **either** an intent-level change (add/remove/retire an intent) **or** a phrasing-level change (edit any paraphrase or the canonical) — both break comparability, both flag.

**Semantics — no metric resets.**
- Each cycle's headline is computed over whatever intents were active that cycle. Removing an intent just makes next cycle's average span a smaller set; nothing is zeroed.
- Per-intent history is preserved via `prompt_scores` keyed by `query_id`; retiring an intent (`status='retired'`, `retired_at`) freezes its past points and stops new ones. Re-adding continues it.
- The flag exists to catch survivorship: dropping an intent you scored badly on makes the overall rate jump for bookkeeping reasons, not performance. The flag marks that cycle so the jump isn't misread.
- Because per-intent rows are stored every run, the frontend (Spec 2) can later offer a "same-intents-only" trend (compare only intents present in both cycles). The backend just stores the signature + per-intent scores; it computes nothing beyond the flag.

---

## Generation rules doc (deliverable)

Write `docs/superpowers/references/intent-generation-rules.md`: a reusable prompt the team pastes into ChatGPT/Claude, together with the client's website and GSC top queries. It must instruct the model to output:

- A set of **awareness** and **consideration** intents, **grounded in the provided GSC queries** (real human searches), the client's category, and named competitors — not invented demand.
- Each intent tagged with its bucket and given ~8 **diverse, natural-language paraphrases** (varied surface form, same intent).
- A paste-ready format matching the queries insert (e.g., a JSON array of `{ prompt_text, bucket, paraphrases }`).

Guardrails written into the prompt: ground every intent in the supplied real searches; **no branded/about-the-client intents**; natural human phrasing, not LLM-ese; paraphrases must preserve the intent (no meaning drift). This is documentation, used at onboarding — no code.

---

## Implementation notes

- **Production path is the graph node** `agents/src/graph/nodes.py::run_tracker_node`. The shared scoring lives in `agents/src/tracker.py` (`run_tracker`, `compute_scores`, `compute_competitive_gaps`) and the persistence helpers in `agents/src/upload.py` (`_compute_prompt_scores`, `_build_competitive_gap_rows`). Update all three so both the graph node and the legacy `run.py`/`upload.py` path stay consistent; the graph node is primary.
- `run_tracker` iterates intents and their `fire_list`; `compute_scores` implements the aggregation formulas above; `nodes.py` computes and writes the drift signature.
- Keep `runs_per_paraphrase` and the paraphrase count as config knobs (defaults: 1 run per paraphrase; paraphrase count is whatever the intent carries).

## Testing

- **Aggregation unit tests** against fixture results with multi-paraphrase intents across engines: intent `mention_rate` / `citation_rate` (conditional) / `avg_mention_level` (over mentioned only); equal-weight-per-intent headline; `bucket_scores`; `per_engine` excludes branded; competitor scores over non-branded.
- **Competitive-gap test:** one gap row per intent, aggregated across paraphrases.
- **Drift-signature tests:** identical set → same signature / `query_set_changed=false`; edit a paraphrase → changes; add/remove an intent → changes; retire an intent → changes.
- **Persistence test:** `tracker_results` rows carry `query_id`/`bucket`/wording; `prompt_scores` keyed by `(query_id, engine)`.
- No card-routing tests (logic unchanged); a regression test confirms card generation still receives intent-level gaps.

## Rollout

The database is freshly reset and clients are not yet re-onboarded, so there is no data migration: add the columns, and re-onboard each client directly on the intent model (canonical + paraphrases per intent, awareness/consideration only). Ship the `schema.sql` update + incremental migration together.

## Deferred to later specs

- **Spec 2 (frontend):** intent-level heat table + per-engine expansion, awareness/consideration bucket breakdown, honest labeling of the headline ("non-branded mention rate across your defined intents"), drift markers on the timeline, and the optional same-intents-only trend view.
- **Comparison bucket + off-page routing** for comparison queries (needs client-supplied competitor identification).
- **Branded reputation/sentiment monitoring** (distinct product).
- **Sampling tuning:** paraphrase count, explicit temperature, optional light repeats per paraphrase.
