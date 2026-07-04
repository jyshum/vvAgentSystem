# Phase 2: Competitive Gap Matrix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich the tracker pipeline to compute per-prompt competitor mention rates and store gap analysis in a new `competitive_gaps` table, enabling prompt-level competitive comparison.

**Architecture:** After Phase 1's `compute_scores()` produces per-engine brand metrics, a new `compute_competitive_gaps()` function groups results by query and computes each configured competitor's mention rate per engine. Upload writes these to a new `competitive_gaps` table. The `tracker_runs` row gets a `discovered_competitors` JSONB column (populated as `[]` for now, schema-ready for future auto-discovery). No new API calls — all computation is local aggregation over existing result data.

**Tech Stack:** Python (existing tracker pipeline), Supabase (PostgreSQL), SQL migration

---

## File Structure

### Backend (modified)
- `agents/src/tracker.py` — add `compute_competitive_gaps()` function
- `agents/src/upload.py` — add `_build_competitive_gap_rows()`, update `upload_run()` to insert gaps
- `agents/src/graph/nodes.py` — update `run_tracker_node()` to insert gaps and discovered_competitors

### Backend (new)
- `agents/tests/test_competitive_gaps.py` — tests for gap computation

### Database (new)
- `supabase/migrations/006_competitive_gaps.sql` — new table + tracker_runs column

---

### Task 1: Database Migration

**Files:**
- Create: `supabase/migrations/006_competitive_gaps.sql`

- [ ] **Step 1: Write the migration SQL**

```sql
-- 006_competitive_gaps.sql
-- Phase 2: Competitive gap matrix

-- ══════════════════════════════════════════════
-- 1. Create competitive_gaps table
-- ══════════════════════════════════════════════

create table public.competitive_gaps (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.tracker_runs(id) on delete cascade,
  client_id uuid not null references public.clients(id) on delete cascade,
  query text not null,
  client_mention_rate numeric default 0,
  client_avg_mention_level numeric default 0,
  competitor_data jsonb default '[]',
  created_at timestamptz default now()
);

create index idx_competitive_gaps_run_id on public.competitive_gaps(run_id);
create index idx_competitive_gaps_client_id on public.competitive_gaps(client_id);

-- RLS
alter table public.competitive_gaps enable row level security;

create policy "Admins can manage competitive_gaps"
  on public.competitive_gaps for all
  using (public.is_admin())
  with check (public.is_admin());

create policy "Clients can view their own competitive_gaps"
  on public.competitive_gaps for select
  using (client_id = public.get_my_client_id());

-- ══════════════════════════════════════════════
-- 2. Add discovered_competitors to tracker_runs
-- ══════════════════════════════════════════════

alter table public.tracker_runs
  add column discovered_competitors jsonb default '[]';
```

- [ ] **Step 2: Commit**

```bash
git add supabase/migrations/006_competitive_gaps.sql
git commit -m "feat: add competitive_gaps table and discovered_competitors column"
```

---

### Task 2: Competitive Gap Computation

**Files:**
- Modify: `agents/src/tracker.py`
- Create: `agents/tests/test_competitive_gaps.py`

- [ ] **Step 1: Write the failing tests**

```python
# agents/tests/test_competitive_gaps.py
from src.tracker import compute_competitive_gaps


def _make_result(query, engine, competitor_mentions, brand_mentioned=False, mention_level=0, run_number=1):
    return {
        "query": query,
        "engine": engine,
        "model": "test-model",
        "response_text": "response",
        "brand_mentioned": brand_mentioned,
        "brand_cited": False,
        "citation_url": None,
        "mention_level": mention_level,
        "mention_level_label": {0: "not_mentioned", 1: "passing_mention", 2: "listed_with_context", 3: "recommended", 4: "primary_recommendation"}[mention_level],
        "competitor_mentions": competitor_mentions,
        "run_number": run_number,
        "timestamp": "2026-07-01T00:00:00Z",
    }


class TestComputeCompetitiveGaps:
    def test_single_query_single_engine(self):
        results = [
            _make_result("best tools", "chatgpt", ["CompA", "CompB"], brand_mentioned=True, mention_level=3, run_number=1),
            _make_result("best tools", "chatgpt", ["CompA"], brand_mentioned=True, mention_level=2, run_number=2),
            _make_result("best tools", "chatgpt", ["CompA", "CompB"], brand_mentioned=False, mention_level=0, run_number=3),
            _make_result("best tools", "chatgpt", [], brand_mentioned=True, mention_level=1, run_number=4),
            _make_result("best tools", "chatgpt", ["CompA"], brand_mentioned=True, mention_level=3, run_number=5),
        ]
        competitors = ["CompA", "CompB"]
        gaps = compute_competitive_gaps(results, competitors)

        assert len(gaps) == 1
        gap = gaps[0]
        assert gap["query"] == "best tools"
        assert gap["client_mention_rate"] == 4 / 5
        assert gap["client_avg_mention_level"] == (3 + 2 + 1 + 3) / 4

        comp_map = {c["name"]: c for c in gap["competitor_data"]}
        assert comp_map["CompA"]["mention_rate"] == 3 / 5
        assert comp_map["CompA"]["per_engine"]["chatgpt"] == 3 / 5
        assert comp_map["CompB"]["mention_rate"] == 2 / 5
        assert comp_map["CompB"]["per_engine"]["chatgpt"] == 2 / 5

    def test_multi_engine_aggregation(self):
        results = [
            # chatgpt: CompA in 2/2 runs
            _make_result("q1", "chatgpt", ["CompA"], brand_mentioned=True, mention_level=3, run_number=1),
            _make_result("q1", "chatgpt", ["CompA"], brand_mentioned=False, mention_level=0, run_number=2),
            # perplexity: CompA in 1/2 runs
            _make_result("q1", "perplexity", ["CompA"], brand_mentioned=True, mention_level=2, run_number=1),
            _make_result("q1", "perplexity", [], brand_mentioned=True, mention_level=1, run_number=2),
        ]
        competitors = ["CompA"]
        gaps = compute_competitive_gaps(results, competitors)

        assert len(gaps) == 1
        gap = gaps[0]
        # Client: mentioned in 3/4 total runs
        assert gap["client_mention_rate"] == 3 / 4
        # CompA: mentioned in 3/4 total runs
        comp = gap["competitor_data"][0]
        assert comp["name"] == "CompA"
        assert comp["mention_rate"] == 3 / 4
        assert comp["per_engine"]["chatgpt"] == 2 / 2
        assert comp["per_engine"]["perplexity"] == 1 / 2

    def test_competitor_absent_from_query(self):
        results = [
            _make_result("q1", "chatgpt", [], brand_mentioned=True, mention_level=3, run_number=1),
            _make_result("q1", "chatgpt", [], brand_mentioned=True, mention_level=2, run_number=2),
        ]
        competitors = ["CompA"]
        gaps = compute_competitive_gaps(results, competitors)

        assert len(gaps) == 1
        comp = gaps[0]["competitor_data"][0]
        assert comp["name"] == "CompA"
        assert comp["mention_rate"] == 0

    def test_multiple_queries(self):
        results = [
            _make_result("q1", "chatgpt", ["CompA"], brand_mentioned=True, mention_level=3, run_number=1),
            _make_result("q1", "chatgpt", [], brand_mentioned=False, mention_level=0, run_number=2),
            _make_result("q2", "chatgpt", [], brand_mentioned=True, mention_level=2, run_number=1),
            _make_result("q2", "chatgpt", ["CompA"], brand_mentioned=False, mention_level=0, run_number=2),
        ]
        competitors = ["CompA"]
        gaps = compute_competitive_gaps(results, competitors)

        assert len(gaps) == 2
        gap_map = {g["query"]: g for g in gaps}
        assert gap_map["q1"]["client_mention_rate"] == 1 / 2
        assert gap_map["q1"]["competitor_data"][0]["mention_rate"] == 1 / 2
        assert gap_map["q2"]["client_mention_rate"] == 1 / 2
        assert gap_map["q2"]["competitor_data"][0]["mention_rate"] == 1 / 2

    def test_empty_results(self):
        gaps = compute_competitive_gaps([], ["CompA"])
        assert gaps == []

    def test_no_competitors_configured(self):
        results = [
            _make_result("q1", "chatgpt", [], brand_mentioned=True, mention_level=3, run_number=1),
        ]
        gaps = compute_competitive_gaps(results, [])
        assert len(gaps) == 1
        assert gaps[0]["competitor_data"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd agents && python3 -m pytest tests/test_competitive_gaps.py -v`
Expected: FAIL — `compute_competitive_gaps` does not exist.

- [ ] **Step 3: Implement `compute_competitive_gaps` in tracker.py**

Add this function at the end of `agents/src/tracker.py`, after `compute_scores()`:

```python
def compute_competitive_gaps(results: list[dict], competitors: list[str]) -> list[dict]:
    if not results:
        return []

    queries = []
    seen = set()
    for r in results:
        if r["query"] not in seen:
            queries.append(r["query"])
            seen.add(r["query"])

    gaps = []
    for query in queries:
        query_results = [r for r in results if r["query"] == query]
        total = len(query_results)

        client_mentions = [r for r in query_results if r["brand_mentioned"]]
        client_mention_rate = len(client_mentions) / total if total > 0 else 0
        client_avg_level = (
            sum(r["mention_level"] for r in client_mentions) / len(client_mentions)
            if client_mentions else 0
        )

        engines = []
        engine_seen = set()
        for r in query_results:
            if r["engine"] not in engine_seen:
                engines.append(r["engine"])
                engine_seen.add(r["engine"])

        competitor_data = []
        for comp in competitors:
            comp_total = 0
            comp_mentioned = 0
            per_engine = {}

            for engine in engines:
                engine_results = [r for r in query_results if r["engine"] == engine]
                engine_total = len(engine_results)
                engine_mentioned = sum(
                    1 for r in engine_results if comp in r.get("competitor_mentions", [])
                )
                per_engine[engine] = engine_mentioned / engine_total if engine_total > 0 else 0
                comp_total += engine_total
                comp_mentioned += engine_mentioned

            competitor_data.append({
                "name": comp,
                "mention_rate": comp_mentioned / comp_total if comp_total > 0 else 0,
                "per_engine": per_engine,
            })

        gaps.append({
            "query": query,
            "client_mention_rate": client_mention_rate,
            "client_avg_mention_level": client_avg_level,
            "competitor_data": competitor_data,
        })

    return gaps
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents && python3 -m pytest tests/test_competitive_gaps.py -v`
Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/src/tracker.py agents/tests/test_competitive_gaps.py
git commit -m "feat: add compute_competitive_gaps for per-prompt competitor rates"
```

---

### Task 3: Upload Module — Insert Competitive Gaps

**Files:**
- Modify: `agents/src/upload.py`

- [ ] **Step 1: Add `_build_competitive_gap_rows()` function**

Add this function after `_compute_prompt_scores()` in `agents/src/upload.py`:

```python
def _build_competitive_gap_rows(client_id: str, run_id: str, gaps: list[dict]) -> list[dict]:
    rows = []
    for gap in gaps:
        rows.append({
            "run_id": run_id,
            "client_id": client_id,
            "query": gap["query"],
            "client_mention_rate": gap["client_mention_rate"],
            "client_avg_mention_level": gap["client_avg_mention_level"],
            "competitor_data": gap["competitor_data"],
        })
    return rows
```

- [ ] **Step 2: Update `upload_run()` to accept and insert gaps**

Change the signature of `upload_run()` from:

```python
def upload_run(
    client_id: str,
    results: list[dict],
    scores: dict,
) -> str | None:
```

To:

```python
def upload_run(
    client_id: str,
    results: list[dict],
    scores: dict,
    competitive_gaps: list[dict] | None = None,
) -> str | None:
```

Then add the following after the `prompt_scores` insert block (after line 63 `sb.from_("prompt_scores").insert(prompt_scores).execute()`), before the print statement:

```python
        gap_rows = _build_competitive_gap_rows(client_id, run_id, competitive_gaps or [])
        if gap_rows:
            sb.from_("competitive_gaps").insert(gap_rows).execute()
```

Update the print statement from:

```python
        print(f"  Uploaded to Supabase: run {run_id} ({len(result_rows)} results, {len(prompt_scores)} prompt scores)")
```

To:

```python
        print(f"  Uploaded to Supabase: run {run_id} ({len(result_rows)} results, {len(prompt_scores)} prompt scores, {len(gap_rows)} gaps)")
```

- [ ] **Step 3: Commit**

```bash
git add agents/src/upload.py
git commit -m "feat: upload competitive gap rows to Supabase"
```

---

### Task 4: Graph Node — Insert Gaps + Discovered Competitors

**Files:**
- Modify: `agents/src/graph/nodes.py`

- [ ] **Step 1: Update `run_tracker_node()` to compute and insert gaps**

Replace the `run_tracker_node` function (lines 29-69 of `agents/src/graph/nodes.py`) with:

```python
def run_tracker_node(state: GEOState) -> dict:
    from src.tracker import run_tracker, compute_competitive_gaps
    try:
        results, scores = run_tracker(state["client_config"])
        competitors = state["client_config"].get("competitors", [])
        gaps = compute_competitive_gaps(results, competitors)

        sb = _get_supabase()
        run_row = sb.table("tracker_runs").insert({
            "client_id": state["client_id"],
            "aggregate_mention_rate": scores.get("aggregate_mention_rate", 0),
            "aggregate_avg_mention_level": scores.get("aggregate_avg_mention_level", 0),
            "per_engine_scores": scores.get("per_engine", {}),
            "competitor_scores": scores.get("competitor_scores", {}),
            "discovered_competitors": [],
        }).execute()

        run_id = run_row.data[0]["id"]

        result_rows = [{
            "run_id": run_id,
            "query": r["query"],
            "engine": r["engine"],
            "model": r.get("model", ""),
            "brand_mentioned": r["brand_mentioned"],
            "brand_cited": r["brand_cited"],
            "citation_url": r.get("citation_url"),
            "competitor_mentions": r.get("competitor_mentions", []),
            "response_text": r.get("response_text", ""),
            "run_number": r.get("run_number"),
            "mention_level": r.get("mention_level", 0),
            "mention_level_label": r.get("mention_level_label", "not_mentioned"),
        } for r in results]
        sb.table("tracker_results").insert(result_rows).execute()

        from src.upload import _compute_prompt_scores, _build_competitive_gap_rows
        prompt_scores = _compute_prompt_scores(state["client_id"], run_id, results)
        if prompt_scores:
            sb.table("prompt_scores").insert(prompt_scores).execute()

        gap_rows = _build_competitive_gap_rows(state["client_id"], run_id, gaps)
        if gap_rows:
            sb.table("competitive_gaps").insert(gap_rows).execute()

        return {"tracker_results": results, "tracker_scores": scores, "competitive_gaps": gaps}
    except Exception as e:
        print(f"  Tracker failed: {e}")
        return {"tracker_results": [], "tracker_scores": {}, "competitive_gaps": [], "error": str(e)}
```

- [ ] **Step 2: Commit**

```bash
git add agents/src/graph/nodes.py
git commit -m "feat: graph node inserts competitive gaps + discovered_competitors"
```

---

### Task 5: Frontend Types Update

**Files:**
- Modify: `dashboard/lib/types.ts`

- [ ] **Step 1: Add CompetitiveGap and update TrackerRun types**

Add the `CompetitiveGap` interface after `PromptScore` in `dashboard/lib/types.ts`:

```typescript
export interface CompetitiveGap {
  id: string;
  run_id: string;
  client_id: string;
  query: string;
  client_mention_rate: number;
  client_avg_mention_level: number;
  competitor_data: {
    name: string;
    mention_rate: number;
    per_engine: Record<string, number>;
  }[];
  created_at: string;
}
```

Add `discovered_competitors` to the `TrackerRun` interface, after `gsc_top_queries`:

```typescript
  discovered_competitors: { name: string; prompt_count: number; total_mentions: number }[];
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/lib/types.ts
git commit -m "feat: add CompetitiveGap type and discovered_competitors to TrackerRun"
```

---

### Task 6: Integration Verification

**Files:** None (verification only)

- [ ] **Step 1: Run backend tests**

Run: `cd agents && python3 -m pytest tests/test_competitive_gaps.py tests/test_multi_run_tracker.py -v`
Expected: All tests PASS.

- [ ] **Step 2: Build frontend**

Run: `cd /Users/jshum/Desktop/code-folders/vvAgentSystem/dashboard && npx next build`
Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 3: Verify no remaining issues**

Run: `grep -rn "competitive_gap\|CompetitiveGap\|discovered_competitors" --include="*.py" --include="*.ts" --include="*.tsx" --include="*.sql" . | grep -v node_modules | grep -v .next`
Expected: References only in the files modified/created by this plan.

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: integration fixes from Phase 2 verification"
```
