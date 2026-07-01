# Phase 1: Multi-Run Execution + New Scoring Model — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the tracker from a single-run binary detection system into a multi-run (5x), multi-signal measurement platform with 4-level mention classification and two clean primary metrics (mention rate + avg mention level).

**Architecture:** The existing LangGraph pipeline shape is unchanged — `run_tracker_node` still wraps `tracker.run_tracker()`. Inside that function, each prompt now fires 5 times per engine (parallel via asyncio.gather, sequential fallback on failure). After string-match detection, a Haiku API call classifies each mention into one of 4 levels. `compute_scores()` produces the new metric shape. Upload and frontend consume the richer data. Clean break — no old data migration.

**Tech Stack:** Python (FastAPI, LangGraph, asyncio), Anthropic API (Haiku for classification), Supabase (PostgreSQL), Next.js/React/TypeScript (dashboard)

---

## File Structure

### Backend (modified)
- `agents/src/detection.py` — add `classify_mention_level()` function, update `detect_brand()` return shape
- `agents/src/tracker.py` — rewrite `run_tracker()` for multi-run parallel execution, rewrite `compute_scores()` for new metrics
- `agents/src/upload.py` — update `upload_run()` for new columns + new `prompt_scores` table
- `agents/src/graph/nodes.py` — update `run_tracker_node()` for new score shape + prompt_scores insert
- `agents/src/graph/state.py` — no structural change needed (tracker_scores is already `dict`)
- `agents/src/output.py` — update all output formats for new metrics

### Backend (new)
- `agents/tests/test_mention_classification.py` — tests for the new Haiku classification
- `agents/tests/test_multi_run_tracker.py` — tests for multi-run execution and new score computation

### Database (new)
- `supabase/migrations/005_multi_run_scoring.sql` — add columns to tracker_results, modify tracker_runs, create prompt_scores table, update view

### Frontend (modified)
- `dashboard/lib/types.ts` — update TrackerRun, TrackerResult, TrackerResultClient interfaces + add PromptScore
- `dashboard/lib/utils.ts` — add mention level helpers, update score formatting
- `dashboard/__tests__/utils.test.ts` — tests for new helpers
- `dashboard/components/dashboard/VisibilityOverview.tsx` — Layout C: hero pair + engine grid
- `dashboard/components/dashboard/TrendChart.tsx` — dual Y-axis chart
- `dashboard/components/report/KPIGrid.tsx` — new metric cards + engine grid
- `dashboard/components/report/QueryResultsTable.tsx` — two-level drill-down with mention levels
- `dashboard/components/admin/RunDetail.tsx` — update KPI strip and engine breakdown for new metrics

---

### Task 1: Database Migration

**Files:**
- Create: `supabase/migrations/005_multi_run_scoring.sql`

- [ ] **Step 1: Write the migration SQL**

```sql
-- 005_multi_run_scoring.sql
-- Phase 1: Multi-run execution + new scoring model

-- ══════════════════════════════════════════════
-- 1. Add columns to tracker_results
-- ══════════════════════════════════════════════

alter table public.tracker_results
  add column run_number integer,
  add column mention_level integer default 0,
  add column mention_level_label text default 'not_mentioned';

-- ══════════════════════════════════════════════
-- 2. Add avg mention level to tracker_runs, drop aggregate_citation_rate
-- ══════════════════════════════════════════════

alter table public.tracker_runs
  add column aggregate_avg_mention_level float default 0;

-- Keep aggregate_citation_rate column for now (old rows use it),
-- but new code will not write to it.

-- ══════════════════════════════════════════════
-- 3. Create prompt_scores table
-- ══════════════════════════════════════════════

create table public.prompt_scores (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.tracker_runs(id) on delete cascade,
  client_id uuid not null references public.clients(id) on delete cascade,
  query text not null,
  llm text not null,
  mention_rate numeric default 0,
  avg_mention_level numeric default 0,
  citation_rate numeric default 0,
  created_at timestamptz default now()
);

create index idx_prompt_scores_run_id on public.prompt_scores(run_id);
create index idx_prompt_scores_client_id on public.prompt_scores(client_id);

-- RLS
alter table public.prompt_scores enable row level security;

create policy "Admins can manage prompt_scores"
  on public.prompt_scores for all
  using (public.is_admin())
  with check (public.is_admin());

create policy "Clients can view their own prompt_scores"
  on public.prompt_scores for select
  using (client_id = public.get_my_client_id());

-- ══════════════════════════════════════════════
-- 4. Update client view to include new columns
-- ══════════════════════════════════════════════

drop view if exists public.tracker_results_client;

create view public.tracker_results_client as
select
  id, run_id, query, engine, model,
  brand_mentioned, brand_cited, citation_url,
  competitor_mentions, queried_at,
  run_number, mention_level, mention_level_label
from public.tracker_results;

grant select on public.tracker_results_client to authenticated;
```

- [ ] **Step 2: Run the migration in Supabase SQL Editor**

Copy the SQL above and run it in Supabase Dashboard → SQL Editor → New query. Verify no errors.

- [ ] **Step 3: Commit**

```bash
git add supabase/migrations/005_multi_run_scoring.sql
git commit -m "feat: add multi-run scoring schema (run_number, mention_level, prompt_scores)"
```

---

### Task 2: Mention Level Classification

**Files:**
- Modify: `agents/src/detection.py`
- Create: `agents/tests/test_mention_classification.py`

- [ ] **Step 1: Write the failing tests**

```python
# agents/tests/test_mention_classification.py
from unittest.mock import patch
from src.detection import classify_mention_level, detect_brand


class TestClassifyMentionLevel:
    def test_returns_primary_recommendation(self):
        with patch("src.detection._call_haiku", return_value="primary_recommendation"):
            result = classify_mention_level("The best tool is BrandX.", "BrandX")
        assert result == {"mention_level": 4, "mention_level_label": "primary_recommendation"}

    def test_returns_recommended(self):
        with patch("src.detection._call_haiku", return_value="recommended"):
            result = classify_mention_level("I recommend BrandX for this.", "BrandX")
        assert result == {"mention_level": 3, "mention_level_label": "recommended"}

    def test_returns_listed_with_context(self):
        with patch("src.detection._call_haiku", return_value="listed_with_context"):
            result = classify_mention_level("BrandX offers a budget template.", "BrandX")
        assert result == {"mention_level": 2, "mention_level_label": "listed_with_context"}

    def test_returns_passing_mention(self):
        with patch("src.detection._call_haiku", return_value="passing_mention"):
            result = classify_mention_level("Resources include BrandX and others.", "BrandX")
        assert result == {"mention_level": 1, "mention_level_label": "passing_mention"}

    def test_unexpected_response_defaults_to_passing(self):
        with patch("src.detection._call_haiku", return_value="something_weird"):
            result = classify_mention_level("BrandX is here.", "BrandX")
        assert result == {"mention_level": 1, "mention_level_label": "passing_mention"}

    def test_haiku_failure_defaults_to_passing(self):
        with patch("src.detection._call_haiku", side_effect=Exception("API error")):
            result = classify_mention_level("BrandX is here.", "BrandX")
        assert result == {"mention_level": 1, "mention_level_label": "passing_mention"}


class TestDetectBrandWithLevel:
    def test_not_mentioned_returns_level_zero(self):
        result = detect_brand("No brands here.", ["BrandX"], "brandx.com")
        assert result["mention_level"] == 0
        assert result["mention_level_label"] == "not_mentioned"

    def test_mentioned_includes_level(self):
        with patch("src.detection.classify_mention_level",
                    return_value={"mention_level": 3, "mention_level_label": "recommended"}):
            result = detect_brand("BrandX is great.", ["BrandX"], "brandx.com")
        assert result["mention_level"] == 3
        assert result["mention_level_label"] == "recommended"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd agents && python -m pytest tests/test_mention_classification.py -v`
Expected: FAIL — `classify_mention_level` does not exist yet.

- [ ] **Step 3: Implement classify_mention_level and update detect_brand**

```python
# agents/src/detection.py
import os
import re


MENTION_LEVELS = {
    "passing_mention": 1,
    "listed_with_context": 2,
    "recommended": 3,
    "primary_recommendation": 4,
}


def _call_haiku(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=20,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip().lower()


def classify_mention_level(response_text: str, brand_name: str) -> dict:
    prompt = (
        f"How is {brand_name} positioned in this AI response? "
        f"Classify as one of: passing_mention, listed_with_context, recommended, primary_recommendation. "
        f"Respond with only the classification.\n\n"
        f"Response:\n{response_text}"
    )
    try:
        label = _call_haiku(prompt)
        label = label.strip().lower().replace(" ", "_")
        if label in MENTION_LEVELS:
            return {"mention_level": MENTION_LEVELS[label], "mention_level_label": label}
    except Exception:
        pass
    return {"mention_level": 1, "mention_level_label": "passing_mention"}


def detect_brand(
    response_text: str,
    brand_variations: list[str],
    website_domain: str,
) -> dict:
    text_lower = response_text.lower()
    domain_lower = website_domain.lower()

    brand_mentioned = any(v.lower() in text_lower for v in brand_variations)

    citation_url = None
    brand_cited = False

    if domain_lower in text_lower:
        brand_cited = True
        brand_mentioned = True
        urls = re.findall(r"https?://[^\s\)\]\"'>]+", response_text)
        for url in urls:
            if domain_lower in url.lower():
                citation_url = url
                break
        if citation_url is None:
            citation_url = f"https://{website_domain}"

    if brand_mentioned:
        matched_variation = next(
            (v for v in brand_variations if v.lower() in text_lower),
            brand_variations[0] if brand_variations else "brand",
        )
        level = classify_mention_level(response_text, matched_variation)
    else:
        level = {"mention_level": 0, "mention_level_label": "not_mentioned"}

    return {
        "brand_mentioned": brand_mentioned,
        "brand_cited": brand_cited,
        "citation_url": citation_url,
        "mention_level": level["mention_level"],
        "mention_level_label": level["mention_level_label"],
    }


def detect_competitors(
    response_text: str,
    competitors: list[str],
) -> list[str]:
    text_lower = response_text.lower()
    return [c for c in competitors if c.lower() in text_lower]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents && python -m pytest tests/test_mention_classification.py -v`
Expected: All 8 tests PASS.

- [ ] **Step 5: Run existing detection tests to verify no regression**

Run: `cd agents && python -m pytest tests/test_detection.py -v`
Expected: All existing tests PASS. Note: `detect_brand` now returns extra keys (`mention_level`, `mention_level_label`) — existing tests only assert on `brand_mentioned`, `brand_cited`, `citation_url`, so they still pass. But `detect_brand` now calls `classify_mention_level` when brand is found, so we need to mock it for existing tests.

If existing tests fail because `classify_mention_level` tries to call the Haiku API, add this fixture to `tests/test_detection.py`:

```python
import pytest
from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_classify(monkeypatch):
    monkeypatch.setattr(
        "src.detection.classify_mention_level",
        lambda text, brand: {"mention_level": 2, "mention_level_label": "listed_with_context"},
    )
```

- [ ] **Step 6: Commit**

```bash
git add agents/src/detection.py agents/tests/test_mention_classification.py agents/tests/test_detection.py
git commit -m "feat: add 4-level mention classification via Haiku"
```

---

### Task 3: Multi-Run Tracker Execution + New Score Computation

**Files:**
- Modify: `agents/src/tracker.py`
- Create: `agents/tests/test_multi_run_tracker.py`

- [ ] **Step 1: Write the failing tests for multi-run and new scores**

```python
# agents/tests/test_multi_run_tracker.py
from unittest.mock import patch, MagicMock
from src.tracker import compute_scores


def _make_result(engine, mentioned, cited, mention_level, run_number):
    return {
        "query": "test query",
        "engine": engine,
        "model": "test-model",
        "response_text": "response",
        "brand_mentioned": mentioned,
        "brand_cited": cited,
        "citation_url": "https://example.com" if cited else None,
        "mention_level": mention_level,
        "mention_level_label": {0: "not_mentioned", 1: "passing_mention", 2: "listed_with_context", 3: "recommended", 4: "primary_recommendation"}[mention_level],
        "competitor_mentions": [],
        "run_number": run_number,
        "timestamp": "2026-07-01T00:00:00Z",
    }


class TestComputeScoresNewFormat:
    def test_mention_rate_across_runs(self):
        results = [
            _make_result("chatgpt", True, False, 3, 1),
            _make_result("chatgpt", True, False, 1, 2),
            _make_result("chatgpt", False, False, 0, 3),
            _make_result("chatgpt", True, False, 2, 4),
            _make_result("chatgpt", True, False, 3, 5),
        ]
        engines = {"chatgpt": {"query": None, "model": "test"}}
        scores = compute_scores(results, engines)
        assert scores["aggregate_mention_rate"] == 4 / 5  # 80%

    def test_avg_mention_level_excludes_zeros(self):
        results = [
            _make_result("chatgpt", True, False, 3, 1),
            _make_result("chatgpt", True, False, 1, 2),
            _make_result("chatgpt", False, False, 0, 3),
            _make_result("chatgpt", True, False, 2, 4),
            _make_result("chatgpt", True, False, 3, 5),
        ]
        engines = {"chatgpt": {"query": None, "model": "test"}}
        scores = compute_scores(results, engines)
        # avg of (3, 1, 2, 3) = 2.25 — excludes the 0 (not mentioned)
        assert scores["aggregate_avg_mention_level"] == (3 + 1 + 2 + 3) / 4

    def test_per_engine_citation_rate_based_on_mentioned_runs(self):
        results = [
            _make_result("chatgpt", True, True, 3, 1),
            _make_result("chatgpt", True, False, 2, 2),
            _make_result("chatgpt", False, False, 0, 3),
            _make_result("chatgpt", True, False, 1, 4),
            _make_result("chatgpt", True, True, 3, 5),
        ]
        engines = {"chatgpt": {"query": None, "model": "test"}}
        scores = compute_scores(results, engines)
        # citation_rate = cited / mentioned = 2 / 4 = 0.5
        assert scores["per_engine"]["chatgpt"]["citation_rate"] == 2 / 4

    def test_per_engine_has_avg_mention_level(self):
        results = [
            _make_result("chatgpt", True, False, 3, 1),
            _make_result("chatgpt", True, False, 1, 2),
        ]
        engines = {"chatgpt": {"query": None, "model": "test"}}
        scores = compute_scores(results, engines)
        assert scores["per_engine"]["chatgpt"]["avg_mention_level"] == 2.0

    def test_no_mentions_produces_zero_avg_level(self):
        results = [
            _make_result("chatgpt", False, False, 0, 1),
            _make_result("chatgpt", False, False, 0, 2),
        ]
        engines = {"chatgpt": {"query": None, "model": "test"}}
        scores = compute_scores(results, engines)
        assert scores["aggregate_avg_mention_level"] == 0
        assert scores["per_engine"]["chatgpt"]["avg_mention_level"] == 0

    def test_competitor_scores_unchanged(self):
        results = [
            {**_make_result("chatgpt", True, False, 3, 1), "competitor_mentions": ["CompA"]},
            {**_make_result("chatgpt", False, False, 0, 2), "competitor_mentions": []},
        ]
        engines = {"chatgpt": {"query": None, "model": "test"}}
        scores = compute_scores(results, engines, competitors=["CompA"])
        assert scores["competitor_scores"]["CompA"]["mention_rate"] == 0.5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd agents && python -m pytest tests/test_multi_run_tracker.py -v`
Expected: FAIL — `compute_scores` doesn't return `aggregate_avg_mention_level` or per-engine `avg_mention_level`/`citation_rate` (based on mentioned runs).

- [ ] **Step 3: Rewrite tracker.py**

```python
# agents/src/tracker.py
import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from src.detection import detect_brand, detect_competitors
from src.engines import load_engines


RUNS_PER_PROMPT = 5


def load_client_config(config_path: str) -> dict:
    return json.loads(Path(config_path).read_text())


async def _query_engine_once(engine_query_fn, query_text: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, engine_query_fn, query_text)


async def _run_prompt_on_engine(
    query_text: str,
    engine_name: str,
    engine_info: dict,
    brand_variations: list[str],
    website_domain: str,
    competitors: list[str],
    runs_per_prompt: int,
) -> list[dict]:
    results = []

    try:
        tasks = [_query_engine_once(engine_info["query"], query_text) for _ in range(runs_per_prompt)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
    except Exception:
        responses = []
        for _ in range(runs_per_prompt):
            try:
                response_text = engine_info["query"](query_text)
                responses.append(response_text)
            except Exception as e:
                responses.append(e)
            time.sleep(0.5)

    for run_num, response in enumerate(responses, 1):
        if isinstance(response, Exception):
            print(f"         → Run {run_num} ERROR: {response}")
            continue

        brand = detect_brand(response, brand_variations, website_domain)
        comps = detect_competitors(response, competitors)

        results.append({
            "query": query_text,
            "engine": engine_name,
            "model": engine_info["model"],
            "response_text": response,
            "brand_mentioned": brand["brand_mentioned"],
            "brand_cited": brand["brand_cited"],
            "citation_url": brand["citation_url"],
            "mention_level": brand["mention_level"],
            "mention_level_label": brand["mention_level_label"],
            "competitor_mentions": comps,
            "run_number": run_num,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    return results


def run_tracker(config: dict) -> tuple[list[dict], dict]:
    engines = load_engines()
    if not engines:
        raise RuntimeError("No engines available. Check your API keys in .env")

    results = []
    queries = config["target_queries"]
    brand_variations = config["brand_variations"]
    website_domain = config["website_domain"]
    competitors = config.get("competitors", [])
    runs_per_prompt = config.get("runs_per_prompt", RUNS_PER_PROMPT)

    total = len(queries) * len(engines)
    count = 0

    for query_text in queries:
        for engine_name, engine_info in engines.items():
            count += 1
            print(f"  [{count}/{total}] {engine_name}: {query_text[:50]}... ({runs_per_prompt} runs)")

            try:
                batch = asyncio.run(_run_prompt_on_engine(
                    query_text, engine_name, engine_info,
                    brand_variations, website_domain, competitors, runs_per_prompt,
                ))
                results.extend(batch)

                mentioned = sum(1 for r in batch if r["brand_mentioned"])
                avg_lvl = sum(r["mention_level"] for r in batch if r["brand_mentioned"])
                avg_lvl = avg_lvl / mentioned if mentioned else 0
                print(f"         → {mentioned}/{len(batch)} mentioned, avg level {avg_lvl:.1f}")
            except Exception as e:
                print(f"         → ERROR: {e}")

    scores = compute_scores(results, engines, competitors)
    return results, scores


def compute_scores(results: list[dict], engines: dict, competitors: list[str] | None = None) -> dict:
    per_engine = {}
    for engine_name in engines:
        engine_results = [r for r in results if r["engine"] == engine_name]
        if not engine_results:
            continue
        total = len(engine_results)
        mentions = [r for r in engine_results if r["brand_mentioned"]]
        mention_count = len(mentions)
        citations = sum(1 for r in mentions if r["brand_cited"])

        avg_level = (
            sum(r["mention_level"] for r in mentions) / mention_count
            if mention_count > 0 else 0
        )
        citation_rate = citations / mention_count if mention_count > 0 else 0

        per_engine[engine_name] = {
            "mention_rate": mention_count / total,
            "avg_mention_level": avg_level,
            "citation_rate": citation_rate,
        }

    all_results = [r for r in results if r["engine"] in engines]
    total_all = len(all_results) if all_results else 1
    all_mentions = [r for r in all_results if r["brand_mentioned"]]
    total_mentions = len(all_mentions)

    aggregate_avg_level = (
        sum(r["mention_level"] for r in all_mentions) / total_mentions
        if total_mentions > 0 else 0
    )

    competitor_scores = {}
    for comp in (competitors or []):
        comp_mentions = sum(
            1 for r in all_results if comp in r.get("competitor_mentions", [])
        )
        competitor_scores[comp] = {
            "mention_rate": comp_mentions / total_all,
        }

    return {
        "per_engine": per_engine,
        "aggregate_mention_rate": total_mentions / total_all,
        "aggregate_avg_mention_level": aggregate_avg_level,
        "competitor_scores": competitor_scores,
    }
```

- [ ] **Step 4: Run new tests to verify they pass**

Run: `cd agents && python -m pytest tests/test_multi_run_tracker.py -v`
Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/src/tracker.py agents/tests/test_multi_run_tracker.py
git commit -m "feat: multi-run tracker execution (5 runs parallel) + new scoring model"
```

---

### Task 4: Upload Module + Graph Node Updates

**Files:**
- Modify: `agents/src/upload.py`
- Modify: `agents/src/graph/nodes.py`

- [ ] **Step 1: Update upload.py for new columns and prompt_scores**

```python
# agents/src/upload.py
import os
from datetime import datetime, timezone


def create_client():
    from supabase import create_client as sb_create

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY required")
    return sb_create(url, key)


def upload_run(
    client_id: str,
    results: list[dict],
    scores: dict,
) -> str | None:
    try:
        sb = create_client()
    except Exception as e:
        print(f"  Supabase upload skipped: {e}")
        return None

    try:
        run_row = {
            "client_id": client_id,
            "ran_at": datetime.now(timezone.utc).isoformat(),
            "aggregate_mention_rate": scores.get("aggregate_mention_rate", 0),
            "aggregate_avg_mention_level": scores.get("aggregate_avg_mention_level", 0),
            "per_engine_scores": scores.get("per_engine", {}),
            "competitor_scores": scores.get("competitor_scores", {}),
        }

        run_resp = sb.from_("tracker_runs").insert(run_row).execute()
        run_id = run_resp.data[0]["id"]

        result_rows = []
        for r in results:
            result_rows.append({
                "run_id": run_id,
                "query": r["query"],
                "engine": r["engine"],
                "model": r.get("model", ""),
                "brand_mentioned": r.get("brand_mentioned", False),
                "brand_cited": r.get("brand_cited", False),
                "citation_url": r.get("citation_url", ""),
                "competitor_mentions": r.get("competitor_mentions", []),
                "response_text": r.get("response_text", ""),
                "queried_at": r.get("timestamp", datetime.now(timezone.utc).isoformat()),
                "run_number": r.get("run_number"),
                "mention_level": r.get("mention_level", 0),
                "mention_level_label": r.get("mention_level_label", "not_mentioned"),
            })

        if result_rows:
            sb.from_("tracker_results").insert(result_rows).execute()

        prompt_scores = _compute_prompt_scores(client_id, run_id, results)
        if prompt_scores:
            sb.from_("prompt_scores").insert(prompt_scores).execute()

        print(f"  Uploaded to Supabase: run {run_id} ({len(result_rows)} results, {len(prompt_scores)} prompt scores)")
        return run_id

    except Exception as e:
        print(f"  Supabase upload failed: {e}")
        return None


def _compute_prompt_scores(client_id: str, run_id: str, results: list[dict]) -> list[dict]:
    from collections import defaultdict

    groups = defaultdict(list)
    for r in results:
        groups[(r["query"], r["engine"])].append(r)

    scores = []
    for (query, engine), runs in groups.items():
        total = len(runs)
        mentions = [r for r in runs if r.get("brand_mentioned")]
        mention_count = len(mentions)

        mention_rate = mention_count / total if total > 0 else 0
        avg_level = (
            sum(r.get("mention_level", 0) for r in mentions) / mention_count
            if mention_count > 0 else 0
        )
        citation_rate = (
            sum(1 for r in mentions if r.get("brand_cited")) / mention_count
            if mention_count > 0 else 0
        )

        scores.append({
            "run_id": run_id,
            "client_id": client_id,
            "query": query,
            "llm": engine,
            "mention_rate": mention_rate,
            "avg_mention_level": avg_level,
            "citation_rate": citation_rate,
        })

    return scores
```

- [ ] **Step 2: Update run_tracker_node in nodes.py**

Replace the `run_tracker_node` function in `agents/src/graph/nodes.py`:

```python
def run_tracker_node(state: GEOState) -> dict:
    from src.tracker import run_tracker
    try:
        results, scores = run_tracker(state["client_config"])

        sb = _get_supabase()
        run_row = sb.table("tracker_runs").insert({
            "client_id": state["client_id"],
            "aggregate_mention_rate": scores.get("aggregate_mention_rate", 0),
            "aggregate_avg_mention_level": scores.get("aggregate_avg_mention_level", 0),
            "per_engine_scores": scores.get("per_engine", {}),
            "competitor_scores": scores.get("competitor_scores", {}),
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

        # Compute and insert prompt-level aggregates
        from src.upload import _compute_prompt_scores
        prompt_scores = _compute_prompt_scores(state["client_id"], run_id, results)
        if prompt_scores:
            sb.table("prompt_scores").insert(prompt_scores).execute()

        return {"tracker_results": results, "tracker_scores": scores}
    except Exception as e:
        print(f"  Tracker failed: {e}")
        return {"tracker_results": [], "tracker_scores": {}, "error": str(e)}
```

- [ ] **Step 3: Run existing test suites to verify no regression**

Run: `cd agents && python -m pytest tests/ -v --ignore=tests/.venv`
Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add agents/src/upload.py agents/src/graph/nodes.py
git commit -m "feat: upload new scoring fields + prompt_scores aggregation"
```

---

### Task 5: Output Module Updates

**Files:**
- Modify: `agents/src/output.py`

- [ ] **Step 1: Update output.py for new metrics**

Replace the full contents of `agents/src/output.py`:

```python
# agents/src/output.py
import csv
import html
import json
from datetime import datetime, timezone
from pathlib import Path


CSV_FIELDS = [
    "query",
    "engine",
    "model",
    "run_number",
    "brand_mentioned",
    "brand_cited",
    "citation_url",
    "mention_level",
    "mention_level_label",
    "competitor_mentions",
    "response_text",
    "timestamp",
]


def write_csv(results: list[dict], output_path: Path) -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for r in results:
            row = {k: r.get(k, "") for k in CSV_FIELDS}
            if isinstance(row["competitor_mentions"], list):
                row["competitor_mentions"] = "; ".join(row["competitor_mentions"])
            writer.writerow(row)


def write_json(
    results: list[dict],
    scores: dict,
    client_name: str,
    output_path: Path,
) -> None:
    report = {
        "client_name": client_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "visibility_scores": scores,
        "results": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


LEVEL_LABELS = {
    0: "Not Mentioned",
    1: "Passing Mention",
    2: "Listed with Context",
    3: "Recommended",
    4: "Primary Recommendation",
}


def format_summary(scores: dict, client_name: str) -> str:
    lines = [
        f"\n{'='*60}",
        f"  GEO Visibility Report: {client_name}",
        f"{'='*60}",
    ]
    for engine, es in scores["per_engine"].items():
        mention = es["mention_rate"]
        avg_lvl = es.get("avg_mention_level", 0)
        citation = es.get("citation_rate", 0)
        lvl_label = LEVEL_LABELS.get(round(avg_lvl), "—")
        lines.append(
            f"  {engine:<15} mention: {mention:>6.0%}   "
            f"avg level: {avg_lvl:.1f} ({lvl_label})   "
            f"citation: {citation:>6.0%}"
        )
    lines.append(f"{'─'*60}")
    agg_mention = scores["aggregate_mention_rate"]
    agg_level = scores.get("aggregate_avg_mention_level", 0)
    lvl_label = LEVEL_LABELS.get(round(agg_level), "—")
    lines.append(
        f"  {'AGGREGATE':<15} mention: {agg_mention:>6.0%}   "
        f"avg level: {agg_level:.1f} ({lvl_label})"
    )
    lines.append(f"{'='*60}")

    comp_scores = scores.get("competitor_scores", {})
    if comp_scores:
        lines.append(f"\n  {'Competitor Comparison':^58}")
        lines.append(f"{'─'*60}")
        lines.append(f"  {'Brand/Competitor':<30} {'Mention Rate':>16}")
        lines.append(f"{'─'*60}")
        lines.append(f"  {client_name:<30} {agg_mention:>15.0%}")
        for comp, cs in comp_scores.items():
            lines.append(f"  {comp:<30} {cs['mention_rate']:>15.0%}")
        lines.append(f"{'='*60}")

    lines.append("")
    return "\n".join(lines)


def _score_color(rate: float) -> str:
    if rate == 0:
        return "#dc3545"
    if rate < 0.25:
        return "#fd7e14"
    if rate < 0.50:
        return "#ffc107"
    return "#28a745"


def _level_color(level: float) -> str:
    if level < 1:
        return "#dc3545"
    if level < 2:
        return "#fd7e14"
    if level < 3:
        return "#ffc107"
    return "#28a745"


def _level_badge(level: int, label: str) -> str:
    colors = {
        0: ("#f8d7da", "#721c24"),
        1: ("#fff3cd", "#856404"),
        2: ("#d4edda", "#155724"),
        3: ("#d1ecf1", "#0c5460"),
        4: ("#cce5ff", "#004085"),
    }
    bg, fg = colors.get(level, ("#e2e3e5", "#383d41"))
    display = label.replace("_", " ").title()
    return f'<span class="badge" style="background:{bg};color:{fg}">{display}</span>'


def write_html(
    results: list[dict],
    scores: dict,
    client_name: str,
    output_path: Path,
) -> None:
    agg_mention = scores["aggregate_mention_rate"]
    agg_level = scores.get("aggregate_avg_mention_level", 0)
    comp_scores = scores.get("competitor_scores", {})
    per_engine = scores["per_engine"]
    generated = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    queries = []
    seen = set()
    for r in results:
        if r["query"] not in seen:
            queries.append(r["query"])
            seen.add(r["query"])

    engine_cards = ""
    for eng, es in per_engine.items():
        m_color = _score_color(es["mention_rate"])
        l_color = _level_color(es.get("avg_mention_level", 0))
        c_rate = es.get("citation_rate", 0)
        engine_cards += f"""
        <div class="engine-card">
            <div class="engine-name">{html.escape(eng)}</div>
            <div class="engine-score" style="color:{m_color}">{es['mention_rate']:.0%}</div>
            <div class="engine-label">mention rate</div>
            <div style="font-size:18px;font-weight:600;color:{l_color};margin-top:4px">
                {es.get('avg_mention_level', 0):.1f}
            </div>
            <div class="engine-label">avg level</div>
            <div style="font-size:14px;color:#86868b;margin-top:4px">{c_rate:.0%} citation</div>
        </div>"""

    comp_rows = ""
    if comp_scores:
        brand_color = _score_color(agg_mention)
        comp_rows += f"""
            <tr class="brand-row">
                <td><strong>{html.escape(client_name)}</strong></td>
                <td><span style="color:{brand_color};font-weight:700">{agg_mention:.0%}</span></td>
            </tr>"""
        for comp, cs in sorted(comp_scores.items(), key=lambda x: -x[1]["mention_rate"]):
            c_color = _score_color(cs["mention_rate"])
            comp_rows += f"""
            <tr>
                <td>{html.escape(comp)}</td>
                <td><span style="color:{c_color};font-weight:700">{cs['mention_rate']:.0%}</span></td>
            </tr>"""

    query_sections = ""
    for query in queries:
        query_results = [r for r in results if r["query"] == query]
        engine_blocks = ""
        for r in query_results:
            level_badge = _level_badge(r.get("mention_level", 0), r.get("mention_level_label", "not_mentioned"))
            comps = ", ".join(r["competitor_mentions"]) if r["competitor_mentions"] else "none"
            resp = html.escape(r["response_text"])
            run_num = r.get("run_number", "")
            engine_blocks += f"""
                <details>
                    <summary>
                        <span class="engine-tag">{html.escape(r['engine'])}</span>
                        <span style="font-size:11px;color:#86868b">Run {run_num}</span>
                        {level_badge}
                        <span class="competitors-tag">competitors: {html.escape(comps)}</span>
                    </summary>
                    <div class="response-text">{resp}</div>
                </details>"""

        query_sections += f"""
        <div class="query-section">
            <h3>{html.escape(query)}</h3>
            {engine_blocks}
        </div>"""

    lvl_label = LEVEL_LABELS.get(round(agg_level), "—")

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GEO Report: {html.escape(client_name)}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       max-width: 1100px; margin: 0 auto; padding: 24px; background: #f5f5f7; color: #1d1d1f; }}
h1 {{ font-size: 28px; margin-bottom: 4px; }}
.subtitle {{ color: #86868b; font-size: 14px; margin-bottom: 24px; }}
.dashboard {{ display: flex; gap: 20px; margin-bottom: 32px; flex-wrap: wrap; }}
.score-card {{ background: #fff; border-radius: 12px; padding: 24px; flex: 1; min-width: 200px;
               box-shadow: 0 1px 3px rgba(0,0,0,0.08); text-align: center; }}
.score-card .label {{ font-size: 13px; color: #86868b; text-transform: uppercase; letter-spacing: 0.5px; }}
.score-card .value {{ font-size: 48px; font-weight: 700; margin: 8px 0; }}
.score-card .detail {{ font-size: 13px; color: #86868b; }}
.engines-row {{ display: flex; gap: 12px; margin-bottom: 32px; flex-wrap: wrap; }}
.engine-card {{ background: #fff; border-radius: 10px; padding: 16px; flex: 1; min-width: 140px;
               box-shadow: 0 1px 3px rgba(0,0,0,0.08); text-align: center; }}
.engine-name {{ font-size: 13px; color: #86868b; text-transform: uppercase; letter-spacing: 0.5px; }}
.engine-score {{ font-size: 32px; font-weight: 700; margin: 4px 0; }}
.engine-label {{ font-size: 11px; color: #aeaeb2; }}
.comp-section {{ background: #fff; border-radius: 12px; padding: 24px; margin-bottom: 32px;
                 box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
.comp-section h2 {{ font-size: 18px; margin-bottom: 16px; }}
.comp-table {{ width: 100%; border-collapse: collapse; }}
.comp-table th {{ text-align: left; padding: 8px 12px; font-size: 12px; color: #86868b;
                  text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid #f0f0f0; }}
.comp-table td {{ padding: 10px 12px; border-bottom: 1px solid #f5f5f7; font-size: 15px; }}
.comp-table .brand-row td {{ background: #f0f7ff; }}
.query-section {{ background: #fff; border-radius: 12px; padding: 24px; margin-bottom: 16px;
                  box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
.query-section h3 {{ font-size: 16px; margin-bottom: 12px; color: #1d1d1f; }}
details {{ border: 1px solid #e5e5ea; border-radius: 8px; margin: 8px 0; }}
summary {{ padding: 10px 14px; cursor: pointer; display: flex; align-items: center; gap: 10px;
           font-size: 14px; background: #fafafa; border-radius: 8px; }}
summary:hover {{ background: #f0f0f0; }}
details[open] summary {{ border-bottom: 1px solid #e5e5ea; border-radius: 8px 8px 0 0; }}
.engine-tag {{ font-weight: 600; min-width: 90px; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px;
          font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; }}
.competitors-tag {{ font-size: 12px; color: #86868b; margin-left: auto; }}
.response-text {{ padding: 16px; font-size: 14px; line-height: 1.7; white-space: pre-wrap;
                  word-wrap: break-word; max-height: 500px; overflow-y: auto; color: #333; }}
</style>
</head>
<body>

<h1>GEO Visibility Report: {html.escape(client_name)}</h1>
<div class="subtitle">Generated {generated}</div>

<div class="dashboard">
    <div class="score-card">
        <div class="label">Mention Rate</div>
        <div class="value" style="color:{_score_color(agg_mention)}">{agg_mention:.0%}</div>
        <div class="detail">across all engines &amp; queries</div>
    </div>
    <div class="score-card">
        <div class="label">Avg Mention Level</div>
        <div class="value" style="color:{_level_color(agg_level)}">{agg_level:.1f}</div>
        <div class="detail">{lvl_label}</div>
    </div>
    <div class="score-card">
        <div class="label">Queries Tracked</div>
        <div class="value" style="color:#1d1d1f">{len(queries)}</div>
        <div class="detail">across {len(per_engine)} engines &middot; 5 runs each</div>
    </div>
</div>

<div class="engines-row">{engine_cards}
</div>

{"" if not comp_scores else f'''
<div class="comp-section">
    <h2>Competitor Comparison</h2>
    <table class="comp-table">
        <thead><tr><th>Brand / Competitor</th><th>Mention Rate</th></tr></thead>
        <tbody>{comp_rows}
        </tbody>
    </table>
</div>
'''}

<h2 style="font-size:20px; margin-bottom:16px;">Query Results</h2>
{query_sections}

</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(page)
```

- [ ] **Step 2: Run existing output tests if any**

Run: `cd agents && python -m pytest tests/test_output.py -v`
Expected: PASS (or skip if no output tests exist).

- [ ] **Step 3: Commit**

```bash
git add agents/src/output.py
git commit -m "feat: update output formats for multi-run scoring (CSV, JSON, HTML)"
```

---

### Task 6: Frontend Types + Utils

**Files:**
- Modify: `dashboard/lib/types.ts`
- Modify: `dashboard/lib/utils.ts`
- Modify: `dashboard/__tests__/utils.test.ts`

- [ ] **Step 1: Write failing tests for new utils**

Add to `dashboard/__tests__/utils.test.ts`:

```typescript
import {
  getMentionLevelLabel,
  getMentionLevelColor,
  formatMentionLevel,
} from "@/lib/utils";

describe("getMentionLevelLabel", () => {
  it("returns Not Mentioned for 0", () => {
    expect(getMentionLevelLabel(0)).toBe("Not Mentioned");
  });
  it("returns Passing Mention for 1", () => {
    expect(getMentionLevelLabel(1)).toBe("Passing Mention");
  });
  it("returns Listed with Context for 2", () => {
    expect(getMentionLevelLabel(2)).toBe("Listed with Context");
  });
  it("returns Recommended for 3", () => {
    expect(getMentionLevelLabel(3)).toBe("Recommended");
  });
  it("returns Primary Recommendation for 4", () => {
    expect(getMentionLevelLabel(4)).toBe("Primary Recommendation");
  });
});

describe("getMentionLevelColor", () => {
  it("returns red for 0", () => {
    expect(getMentionLevelColor(0)).toBe("var(--neg)");
  });
  it("returns orange for 1", () => {
    expect(getMentionLevelColor(1)).toBe("#fd7e14");
  });
  it("returns yellow for 2", () => {
    expect(getMentionLevelColor(2)).toBe("#ffc107");
  });
  it("returns pos for 3+", () => {
    expect(getMentionLevelColor(3)).toBe("var(--pos)");
    expect(getMentionLevelColor(4)).toBe("var(--pos)");
  });
});

describe("formatMentionLevel", () => {
  it("formats level with label", () => {
    expect(formatMentionLevel(2.8)).toBe("2.8");
  });
  it("formats zero", () => {
    expect(formatMentionLevel(0)).toBe("0.0");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd dashboard && npx vitest run __tests__/utils.test.ts`
Expected: FAIL — functions don't exist yet.

- [ ] **Step 3: Update types.ts**

```typescript
// dashboard/lib/types.ts
export interface Client {
  id: string;
  name: string;
  brand_name: string;
  website_domain: string;
  brand_variations: string[];
  target_queries: string[];
  competitors: string[];
  cms_type: string;
  cms_config: Record<string, string>;
  gsc_site_url: string;
  cycle_frequency: string;
  cycle_day: number;
  created_at: string;
}

export interface ClientUser {
  id: string;
  user_id: string;
  client_id: string | null;
  role: "admin" | "client";
  created_at: string;
}

export interface TrackerRun {
  id: string;
  client_id: string;
  ran_at: string;
  aggregate_mention_rate: number;
  aggregate_avg_mention_level: number;
  per_engine_scores: Record<
    string,
    { mention_rate: number; avg_mention_level: number; citation_rate: number }
  >;
  competitor_scores: Record<string, { mention_rate: number }>;
  gsc_clicks: number;
  gsc_impressions: number;
  gsc_ctr: number;
  gsc_position: number;
  gsc_top_queries: { query: string; clicks: number; impressions: number; ctr: number; position: number }[];
}

export interface TrackerResult {
  id: string;
  run_id: string;
  query: string;
  engine: string;
  model: string;
  brand_mentioned: boolean;
  brand_cited: boolean;
  citation_url: string | null;
  competitor_mentions: string[];
  response_text: string;
  queried_at: string;
  run_number: number;
  mention_level: number;
  mention_level_label: string;
}

export interface TrackerResultClient {
  id: string;
  run_id: string;
  query: string;
  engine: string;
  model: string;
  brand_mentioned: boolean;
  brand_cited: boolean;
  citation_url: string | null;
  competitor_mentions: string[];
  response_text?: string;
  queried_at: string;
  run_number: number;
  mention_level: number;
  mention_level_label: string;
}

export interface PromptScore {
  id: string;
  run_id: string;
  client_id: string;
  query: string;
  llm: string;
  mention_rate: number;
  avg_mention_level: number;
  citation_rate: number;
  created_at: string;
}

export interface Report {
  id: string;
  client_id: string;
  run_id: string | null;
  week_start: string;
  status: "draft" | "published";
  exec_summary: string;
  work_completed: { text: string; done: boolean }[];
  priorities: { text: string }[];
  highlights: { text: string }[];
  blockers: { text: string }[];
  notes: string;
  search_console: SearchConsoleMetrics | null;
  published_at: string | null;
  created_at: string;
}

export interface SearchConsoleMetrics {
  impressions: { week: number | null; baseline: number | null };
  clicks: { week: number | null; baseline: number | null };
  ctr: { week: number | null; baseline: number | null };
  position: { week: number | null; baseline: number | null };
}

export interface ReportWithRun extends Report {
  tracker_run: TrackerRun | null;
}
```

- [ ] **Step 4: Update utils.ts — add new helpers**

Add these functions to the end of `dashboard/lib/utils.ts`:

```typescript
const MENTION_LEVEL_LABELS: Record<number, string> = {
  0: "Not Mentioned",
  1: "Passing Mention",
  2: "Listed with Context",
  3: "Recommended",
  4: "Primary Recommendation",
};

export function getMentionLevelLabel(level: number): string {
  return MENTION_LEVEL_LABELS[Math.round(level)] ?? "Unknown";
}

export function getMentionLevelColor(level: number, paper?: boolean): string {
  if (paper) {
    if (level < 1) return "var(--neg-paper)";
    if (level < 2) return "#c45c00";
    if (level < 3) return "#8a6a00";
    return "var(--pos-paper)";
  }
  if (level < 1) return "var(--neg)";
  if (level < 2) return "#fd7e14";
  if (level < 3) return "#ffc107";
  return "var(--pos)";
}

export function formatMentionLevel(level: number): string {
  return level.toFixed(1);
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd dashboard && npx vitest run __tests__/utils.test.ts`
Expected: All tests PASS (old and new).

- [ ] **Step 6: Commit**

```bash
git add dashboard/lib/types.ts dashboard/lib/utils.ts dashboard/__tests__/utils.test.ts
git commit -m "feat: update frontend types and utils for multi-run scoring"
```

---

### Task 7: VisibilityOverview — Layout C (Hero Pair + Engine Grid)

**Files:**
- Modify: `dashboard/components/dashboard/VisibilityOverview.tsx`

- [ ] **Step 1: Rewrite VisibilityOverview for Layout C**

```tsx
import { Card } from "@/components/ui/Card";
import {
  scoreColor,
  formatRate,
  formatDelta,
  getMentionLevelLabel,
  getMentionLevelColor,
  formatMentionLevel,
} from "@/lib/utils";
import type { TrackerRun } from "@/lib/types";

interface VisibilityOverviewProps {
  latestRun: TrackerRun | null;
  previousRun: TrackerRun | null;
  totalReports: number;
}

export function VisibilityOverview({
  latestRun,
  previousRun,
}: VisibilityOverviewProps) {
  const mentionRate = latestRun?.aggregate_mention_rate ?? 0;
  const avgLevel = latestRun?.aggregate_avg_mention_level ?? 0;
  const engines = latestRun
    ? Object.entries(latestRun.per_engine_scores)
    : [];

  const mentionDelta = formatDelta(
    mentionRate,
    previousRun?.aggregate_mention_rate ?? null
  );

  const levelDelta =
    previousRun?.aggregate_avg_mention_level != null
      ? {
          text:
            avgLevel - previousRun.aggregate_avg_mention_level > 0
              ? `+${(avgLevel - previousRun.aggregate_avg_mention_level).toFixed(1)}`
              : (avgLevel - previousRun.aggregate_avg_mention_level).toFixed(1),
          direction:
            avgLevel > previousRun.aggregate_avg_mention_level
              ? ("up" as const)
              : avgLevel < previousRun.aggregate_avg_mention_level
                ? ("down" as const)
                : ("flat" as const),
        }
      : null;

  return (
    <div className="mb-10">
      {/* Hero pair */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <Card elevated className="p-6 text-center">
          <div
            className="font-mono text-[10.5px] tracking-[0.2em] uppercase mb-2"
            style={{ color: "var(--mute)" }}
          >
            Mention Rate
          </div>
          <div
            className="font-serif text-[56px] leading-none my-2"
            style={{ color: scoreColor(mentionRate) }}
          >
            {formatRate(mentionRate)}
          </div>
          {mentionDelta && (
            <div
              className="font-mono text-[10px] tracking-[0.04em]"
              style={{
                color:
                  mentionDelta.direction === "up"
                    ? "var(--pos)"
                    : mentionDelta.direction === "down"
                      ? "var(--neg)"
                      : "var(--mute)",
              }}
            >
              {mentionDelta.direction === "up"
                ? "▲"
                : mentionDelta.direction === "down"
                  ? "▼"
                  : "■"}{" "}
              {mentionDelta.text} vs last cycle
            </div>
          )}
        </Card>

        <Card elevated className="p-6 text-center">
          <div
            className="font-mono text-[10.5px] tracking-[0.2em] uppercase mb-2"
            style={{ color: "var(--mute)" }}
          >
            Avg Mention Level
          </div>
          <div
            className="font-serif text-[56px] leading-none my-2"
            style={{ color: getMentionLevelColor(avgLevel) }}
          >
            {formatMentionLevel(avgLevel)}
          </div>
          <div
            className="font-mono text-[9px] tracking-[0.04em] mb-1"
            style={{ color: getMentionLevelColor(avgLevel) }}
          >
            {getMentionLevelLabel(Math.round(avgLevel))}
          </div>
          {levelDelta && (
            <div
              className="font-mono text-[10px] tracking-[0.04em]"
              style={{
                color:
                  levelDelta.direction === "up"
                    ? "var(--pos)"
                    : levelDelta.direction === "down"
                      ? "var(--neg)"
                      : "var(--mute)",
              }}
            >
              {levelDelta.direction === "up"
                ? "▲"
                : levelDelta.direction === "down"
                  ? "▼"
                  : "■"}{" "}
              {levelDelta.text} vs last cycle
            </div>
          )}
        </Card>
      </div>

      {/* Engine grid */}
      {engines.length > 0 && (
        <div
          className="grid gap-3"
          style={{ gridTemplateColumns: `repeat(${engines.length}, 1fr)` }}
        >
          {engines.map(([engine, scores]) => (
            <Card key={engine} elevated className="p-4">
              <div
                className="font-mono text-[10px] tracking-[0.12em] uppercase mb-3 font-medium"
                style={{ color: "var(--mute)" }}
              >
                {engine}
              </div>
              <div className="flex flex-col gap-1.5">
                <div className="flex justify-between items-center">
                  <span
                    className="font-mono text-[9px] tracking-[0.06em]"
                    style={{ color: "var(--faint)" }}
                  >
                    Mention
                  </span>
                  <span
                    className="font-mono text-[13px] font-medium"
                    style={{ color: scoreColor(scores.mention_rate) }}
                  >
                    {formatRate(scores.mention_rate)}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span
                    className="font-mono text-[9px] tracking-[0.06em]"
                    style={{ color: "var(--faint)" }}
                  >
                    Level
                  </span>
                  <span
                    className="font-mono text-[13px] font-medium"
                    style={{
                      color: getMentionLevelColor(scores.avg_mention_level),
                    }}
                  >
                    {formatMentionLevel(scores.avg_mention_level)}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span
                    className="font-mono text-[9px] tracking-[0.06em]"
                    style={{ color: "var(--faint)" }}
                  >
                    Citation
                  </span>
                  <span
                    className="font-mono text-[13px]"
                    style={{ color: "var(--white)" }}
                  >
                    {formatRate(scores.citation_rate)}
                  </span>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify the dashboard page still compiles**

Run: `cd dashboard && npx next build 2>&1 | head -30`
Expected: No TypeScript errors related to VisibilityOverview.

- [ ] **Step 3: Commit**

```bash
git add dashboard/components/dashboard/VisibilityOverview.tsx
git commit -m "feat: VisibilityOverview — Layout C hero pair + engine grid"
```

---

### Task 8: TrendChart — Dual Y-Axis

**Files:**
- Modify: `dashboard/components/dashboard/TrendChart.tsx`

- [ ] **Step 1: Rewrite TrendChart for dual Y-axis**

```tsx
import { Card } from "@/components/ui/Card";
import { formatRate, formatMentionLevel } from "@/lib/utils";
import type { TrackerRun } from "@/lib/types";

interface TrendChartProps {
  runs: TrackerRun[];
}

export function TrendChart({ runs }: TrendChartProps) {
  if (runs.length < 2) return null;

  const sorted = [...runs]
    .filter((r) => r.aggregate_avg_mention_level != null)
    .sort((a, b) => new Date(a.ran_at).getTime() - new Date(b.ran_at).getTime());

  if (sorted.length < 2) return null;

  const mentionValues = sorted.map((r) => r.aggregate_mention_rate);
  const levelValues = sorted.map((r) => r.aggregate_avg_mention_level);

  const mMin = Math.min(...mentionValues);
  const mMax = Math.max(...mentionValues);
  const mRange = mMax - mMin || 0.01;

  const lMin = Math.min(...levelValues);
  const lMax = Math.max(...levelValues);
  const lRange = lMax - lMin || 0.1;

  const W = 800;
  const H = 200;
  const padL = 40;
  const padR = 40;
  const padT = 20;
  const padB = 30;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;
  const stepX = plotW / (sorted.length - 1);

  const mentionCoords = mentionValues.map((v, i) => {
    const t = (v - mMin) / mRange;
    return [padL + i * stepX, padT + (1 - t) * plotH] as const;
  });

  const levelCoords = levelValues.map((v, i) => {
    const t = (v - lMin) / lRange;
    return [padL + i * stepX, padT + (1 - t) * plotH] as const;
  });

  const mentionLine = mentionCoords
    .map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`)
    .join(" ");

  const levelLine = levelCoords
    .map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`)
    .join(" ");

  const lastM = mentionCoords[mentionCoords.length - 1];
  const lastL = levelCoords[levelCoords.length - 1];

  return (
    <Card elevated className="p-6 mb-10">
      <div className="flex items-center justify-between mb-4">
        <div
          className="font-mono text-[11px] tracking-[0.12em] uppercase"
          style={{ color: "var(--mute)" }}
        >
          Visibility Trend
        </div>
        <div className="flex gap-4">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-[2px]" style={{ background: "var(--pos)" }} />
            <span className="font-mono text-[8px] tracking-[0.06em]" style={{ color: "var(--faint)" }}>
              Mention Rate
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-[2px]" style={{ background: "#60a5fa" }} />
            <span className="font-mono text-[8px] tracking-[0.06em]" style={{ color: "var(--faint)" }}>
              Avg Level
            </span>
          </div>
        </div>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 200 }}>
        {/* Left axis grid (mention rate 0-100%) */}
        {[0, 0.25, 0.5, 0.75, 1].map((t) => {
          const y = padT + (1 - t) * plotH;
          const val = mMin + t * mRange;
          return (
            <g key={`m-${t}`}>
              <line x1={padL} x2={W - padR} y1={y} y2={y} stroke="var(--hair)" strokeWidth={1} />
              <text x={padL - 8} y={y + 3} textAnchor="end" className="font-mono" style={{ fontSize: 9, fill: "var(--pos)" }}>
                {formatRate(val)}
              </text>
            </g>
          );
        })}

        {/* Right axis labels (avg level 0-4) */}
        {[0, 0.25, 0.5, 0.75, 1].map((t) => {
          const y = padT + (1 - t) * plotH;
          const val = lMin + t * lRange;
          return (
            <text key={`l-${t}`} x={W - padR + 8} y={y + 3} textAnchor="start" className="font-mono" style={{ fontSize: 9, fill: "#60a5fa" }}>
              {formatMentionLevel(val)}
            </text>
          );
        })}

        {/* Mention rate line (green) */}
        <path d={mentionLine} fill="none" stroke="var(--pos)" strokeWidth={2} vectorEffect="non-scaling-stroke" />
        <circle cx={lastM[0]} cy={lastM[1]} r={4} fill="var(--pos)" vectorEffect="non-scaling-stroke" />

        {/* Avg level line (blue) */}
        <path d={levelLine} fill="none" stroke="#60a5fa" strokeWidth={2} vectorEffect="non-scaling-stroke" strokeDasharray="6 3" />
        <circle cx={lastL[0]} cy={lastL[1]} r={4} fill="#60a5fa" vectorEffect="non-scaling-stroke" />

        {/* X-axis labels */}
        {sorted.map((r, i) => {
          const x = padL + i * stepX;
          const date = new Date(r.ran_at);
          const label = date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
          return (
            <text key={r.id} x={x} y={H - 5} textAnchor="middle" className="font-mono" style={{ fontSize: 9, fill: "var(--faint)" }}>
              {label}
            </text>
          );
        })}
      </svg>
    </Card>
  );
}
```

- [ ] **Step 2: Verify build**

Run: `cd dashboard && npx next build 2>&1 | head -30`
Expected: No TypeScript errors.

- [ ] **Step 3: Commit**

```bash
git add dashboard/components/dashboard/TrendChart.tsx
git commit -m "feat: TrendChart — dual Y-axis (mention rate + avg level)"
```

---

### Task 9: KPIGrid (Report View)

**Files:**
- Modify: `dashboard/components/report/KPIGrid.tsx`

- [ ] **Step 1: Rewrite KPIGrid for new metrics**

```tsx
import { scoreColor, formatRate, getMentionLevelColor, formatMentionLevel, getMentionLevelLabel } from "@/lib/utils";
import { SparklineChart } from "@/components/charts/SparklineChart";
import type { TrackerRun } from "@/lib/types";

interface KPIGridProps {
  run: TrackerRun;
  previousRuns?: TrackerRun[];
}

export function KPIGrid({ run, previousRuns = [] }: KPIGridProps) {
  const engines = Object.entries(run.per_engine_scores);
  const prev = previousRuns.length > 0 ? previousRuns[previousRuns.length - 1] : null;

  const mentionHistory = previousRuns.map((r) => r.aggregate_mention_rate);
  const levelHistory = previousRuns.map((r) => r.aggregate_avg_mention_level);

  const mentionDelta = prev
    ? Math.round((run.aggregate_mention_rate - prev.aggregate_mention_rate) * 100)
    : null;
  const levelDelta = prev
    ? +(run.aggregate_avg_mention_level - prev.aggregate_avg_mention_level).toFixed(1)
    : null;

  return (
    <div className="mt-[50px]">
      <h2
        className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] mb-6"
        style={{
          color: "var(--p-mute)",
          borderBottom: "1px solid var(--p-hair)",
        }}
      >
        AI Visibility Scores
      </h2>

      {/* Hero pair */}
      <div
        className="grid grid-cols-2 gap-px mb-6"
        style={{ background: "var(--p-hair)", border: "1px solid var(--p-hair)" }}
      >
        <div className="p-5 flex flex-col" style={{ background: "var(--paper)", minHeight: "132px" }}>
          <div className="font-mono text-[11px] tracking-[0.12em] uppercase mb-3" style={{ color: "var(--p-mute)" }}>
            Mention Rate
          </div>
          <div className="font-serif font-light text-[48px] leading-none mb-2" style={{ color: scoreColor(run.aggregate_mention_rate, true) }}>
            {formatRate(run.aggregate_mention_rate)}
          </div>
          {mentionDelta !== null && (
            <div className="font-mono text-[10px] tracking-[0.04em]" style={{ color: "var(--p-mute)" }}>
              <span className="font-bold" style={{ color: mentionDelta > 0 ? "var(--pos-paper)" : mentionDelta < 0 ? "var(--neg-paper)" : "var(--p-mute)" }}>
                {mentionDelta > 0 ? "+" : ""}
              </span>
              <span>{Math.abs(mentionDelta)}pp vs last week</span>
            </div>
          )}
          <div className="mt-auto pt-3">
            <SparklineChart
              values={[...mentionHistory, run.aggregate_mention_rate]}
              direction={mentionDelta === null ? "none" : mentionDelta > 0 ? "up" : mentionDelta < 0 ? "down" : "flat"}
              paper
            />
          </div>
        </div>

        <div className="p-5 flex flex-col" style={{ background: "var(--paper)", minHeight: "132px" }}>
          <div className="font-mono text-[11px] tracking-[0.12em] uppercase mb-3" style={{ color: "var(--p-mute)" }}>
            Avg Mention Level
          </div>
          <div className="font-serif font-light text-[48px] leading-none mb-1" style={{ color: getMentionLevelColor(run.aggregate_avg_mention_level, true) }}>
            {formatMentionLevel(run.aggregate_avg_mention_level)}
          </div>
          <div className="font-mono text-[9px] tracking-[0.08em] mb-2" style={{ color: getMentionLevelColor(run.aggregate_avg_mention_level, true) }}>
            {getMentionLevelLabel(Math.round(run.aggregate_avg_mention_level))}
          </div>
          {levelDelta !== null && (
            <div className="font-mono text-[10px] tracking-[0.04em]" style={{ color: "var(--p-mute)" }}>
              <span className="font-bold" style={{ color: levelDelta > 0 ? "var(--pos-paper)" : levelDelta < 0 ? "var(--neg-paper)" : "var(--p-mute)" }}>
                {levelDelta > 0 ? "+" : ""}
              </span>
              <span>{Math.abs(levelDelta)} vs last week</span>
            </div>
          )}
          <div className="mt-auto pt-3">
            <SparklineChart
              values={[...levelHistory, run.aggregate_avg_mention_level]}
              direction={levelDelta === null ? "none" : levelDelta > 0 ? "up" : levelDelta < 0 ? "down" : "flat"}
              paper
            />
          </div>
        </div>
      </div>

      {/* Engine grid */}
      <div
        className="grid gap-px"
        style={{
          gridTemplateColumns: `repeat(${engines.length}, 1fr)`,
          background: "var(--p-hair)",
          border: "1px solid var(--p-hair)",
        }}
      >
        {engines.map(([engine, scores]) => (
          <div
            key={engine}
            className="p-5 flex flex-col gap-2"
            style={{ background: "var(--paper)", minHeight: "120px" }}
          >
            <div className="font-mono text-[11px] tracking-[0.12em] uppercase mb-2" style={{ color: "var(--p-mute)" }}>
              {engine}
            </div>
            <div className="flex justify-between items-center">
              <span className="font-mono text-[9px] tracking-[0.06em]" style={{ color: "var(--p-faint)" }}>Mention</span>
              <span className="font-serif font-light text-[24px] leading-none" style={{ color: scoreColor(scores.mention_rate, true) }}>
                {formatRate(scores.mention_rate)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="font-mono text-[9px] tracking-[0.06em]" style={{ color: "var(--p-faint)" }}>Level</span>
              <span className="font-serif font-light text-[24px] leading-none" style={{ color: getMentionLevelColor(scores.avg_mention_level, true) }}>
                {formatMentionLevel(scores.avg_mention_level)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="font-mono text-[9px] tracking-[0.06em]" style={{ color: "var(--p-faint)" }}>Citation</span>
              <span className="font-mono text-[14px]" style={{ color: "var(--paper-ink)" }}>
                {formatRate(scores.citation_rate)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

Run: `cd dashboard && npx next build 2>&1 | head -30`
Expected: No TypeScript errors.

- [ ] **Step 3: Commit**

```bash
git add dashboard/components/report/KPIGrid.tsx
git commit -m "feat: KPIGrid — hero pair + engine grid with new metrics"
```

---

### Task 10: QueryResultsTable — Two-Level Drill-Down

**Files:**
- Modify: `dashboard/components/report/QueryResultsTable.tsx`

- [ ] **Step 1: Update QueryResultsTable for mention levels**

The component currently shows binary "Mentioned"/"Cited" badges per engine. Update to show the mention level label instead. Replace the `Badge` usage in `EngineRow` with mention level display.

In `dashboard/components/report/QueryResultsTable.tsx`, replace the `EngineRow` component's badge logic:

Change this block in the `EngineRow` function (around line 199-205):

```tsx
  const variant = result.brand_cited
    ? "cited-paper"
    : result.brand_mentioned
      ? "mentioned-paper"
      : "not-found-paper";

  const label = result.brand_cited ? "Cited" : "Mentioned";
```

To:

```tsx
  const variant = result.brand_cited
    ? "cited-paper"
    : result.brand_mentioned
      ? "mentioned-paper"
      : "not-found-paper";

  const levelLabel = result.mention_level_label
    ? result.mention_level_label.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())
    : result.brand_cited
      ? "Cited"
      : result.brand_mentioned
        ? "Mentioned"
        : "Not Found";

  const label = result.brand_mentioned ? levelLabel : "Not Found";
```

Also update the `Badge` usage on line ~222 to display the new label:

```tsx
<Badge variant={variant}>{label}</Badge>
```

This is unchanged in JSX — only the `label` variable is different. The badge now says "Recommended" or "Primary Recommendation" instead of just "Mentioned".

- [ ] **Step 2: Verify build**

Run: `cd dashboard && npx next build 2>&1 | head -30`
Expected: No TypeScript errors.

- [ ] **Step 3: Commit**

```bash
git add dashboard/components/report/QueryResultsTable.tsx
git commit -m "feat: QueryResultsTable — show mention level labels instead of binary badges"
```

---

### Task 11: Admin RunDetail — New Metrics

**Files:**
- Modify: `dashboard/components/admin/RunDetail.tsx`

- [ ] **Step 1: Update RunDetail KPI strip**

In `dashboard/components/admin/RunDetail.tsx`, update the KPI strip (around line 136-156). Replace the 4-card KPI computation inside the IIFE:

```tsx
{(() => {
  const mentionedCount = results.filter((r) => r.brand_mentioned || r.brand_cited).length;
  const avgLevel = run.aggregate_avg_mention_level ?? 0;
  const topComp = Object.entries(compCounts).sort((a, b) => b[1] - a[1])[0];
  const topCompRate = topComp ? Math.round((topComp[1] / results.length) * 100) + "%" : "-";
  const topCompLabel = topComp ? `${topComp[0]}` : "none detected";
  return [
    { n: formatRate(run.aggregate_mention_rate), l: "Mention Rate", d: `${mentionedCount} of ${results.length}`, color: scoreColor(run.aggregate_mention_rate) },
    { n: avgLevel.toFixed(1), l: "Avg Mention Level", d: getMentionLevelLabel(Math.round(avgLevel)), color: getMentionLevelColor(avgLevel) },
    { n: topCompRate, l: "Top Competitor Rate", d: topCompLabel, color: "var(--mute)" },
    { n: String(Object.keys(run.per_engine_scores).length), l: "Engines", d: "tracked", color: "var(--faint)" },
  ];
})()}
```

Add imports at the top of the file:

```tsx
import { scoreColor, formatRate, getMentionLevelLabel, getMentionLevelColor } from "@/lib/utils";
```

(Remove the existing `import { scoreColor, formatRate } from "@/lib/utils"` line.)

- [ ] **Step 2: Update per-engine breakdown**

In the per-engine breakdown section (around line 166-198), update the `engineStats` computation to use the new per-engine scores:

```tsx
const engineStats = ENGINES.map((eng) => {
  const scores = run.per_engine_scores[eng];
  const engineResults = results.filter((r) => r.engine === eng);
  const total = engineResults.length;
  if (!scores) return { engine: eng, mentionRate: 0, avgLevel: 0, citationRate: 0, total };
  return {
    engine: eng,
    mentionRate: scores.mention_rate,
    avgLevel: scores.avg_mention_level,
    citationRate: scores.citation_rate,
    total,
  };
});
```

And update the engine card rendering to show all three metrics:

```tsx
{engineStats.map(({ engine, mentionRate, avgLevel, citationRate, total }) => (
  <div key={engine} className="p-4 border" style={{ borderColor: "var(--hair)" }}>
    <div className="font-mono text-[10px] tracking-[0.12em] mb-3 font-medium" style={{ color: "var(--white)" }}>
      {ENGINE_LABELS[engine]}
    </div>
    <div className="flex flex-col gap-1.5">
      <div className="flex justify-between items-center">
        <span className="font-mono text-[7px] tracking-[0.08em]" style={{ color: "var(--faint)" }}>MENTION</span>
        <span className="font-mono text-[13px] font-medium" style={{ color: scoreColor(mentionRate) }}>
          {formatRate(mentionRate)}
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span className="font-mono text-[7px] tracking-[0.08em]" style={{ color: "var(--faint)" }}>LEVEL</span>
        <span className="font-mono text-[13px] font-medium" style={{ color: getMentionLevelColor(avgLevel) }}>
          {avgLevel.toFixed(1)}
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span className="font-mono text-[7px] tracking-[0.08em]" style={{ color: "var(--faint)" }}>CITATION</span>
        <span className="font-mono text-[11px]" style={{ color: "var(--faint)" }}>
          {formatRate(citationRate)}
        </span>
      </div>
    </div>
  </div>
))}
```

- [ ] **Step 3: Update StatusBadge to show mention level**

Replace the `StatusBadge` function:

```tsx
function StatusBadge({ result }: { result: TrackerResult }) {
  if (!result.brand_mentioned && !result.brand_cited) {
    return <span className="font-mono text-[8px] shrink-0" style={{ color: "var(--faint)" }}>not found</span>;
  }

  const label = result.mention_level_label
    ? result.mention_level_label.replace(/_/g, " ").toUpperCase()
    : result.brand_cited
      ? "CITED"
      : "MENTIONED";

  const isCited = result.brand_cited;

  return (
    <span
      className="font-mono text-[8px] tracking-[0.1em] py-0.5 px-2 shrink-0"
      style={{
        color: "var(--pos)",
        border: `1px solid rgba(132,216,171,${isCited ? "0.3" : "0.2"})`,
        background: `rgba(132,216,171,${isCited ? "0.08" : "0.05"})`,
      }}
    >
      {label}
    </span>
  );
}
```

Update all usages of `StatusBadge` in the file to pass the full `result` object instead of `mentioned`/`cited` booleans:

Old: `<StatusBadge mentioned={result.brand_mentioned} cited={result.brand_cited} />`
New: `<StatusBadge result={result} />`

- [ ] **Step 4: Update query matrix cells**

In the query matrix table, update `cellFor` to show mention level instead of just M/C/-:

```tsx
const cellFor = (eng: string) => {
  const r = qResults.find((r) => r.engine === eng);
  if (!r) return (
    <td key={eng} style={{ padding: "11px 12px", textAlign: "center", color: "var(--faint)", fontSize: 7 }}>N/A</td>
  );
  if (!r.brand_mentioned && !r.brand_cited) return (
    <td key={eng} style={{ padding: "11px 12px", textAlign: "center", color: "var(--faint)" }}>-</td>
  );
  const levelShort = r.mention_level === 4 ? "P" : r.mention_level === 3 ? "R" : r.mention_level === 2 ? "L" : "m";
  const color = r.brand_cited ? "var(--pos)" : "rgba(132,216,171,0.8)";
  return (
    <td key={eng} style={{ padding: "11px 12px", textAlign: "center", color, fontWeight: r.mention_level >= 3 ? 600 : 500, fontSize: 10 }}>
      {levelShort}{r.brand_cited ? "·C" : ""}
    </td>
  );
};
```

Update the legend at the bottom:

```tsx
<div className="font-mono mt-2" style={{ fontSize: 8, color: "var(--faint)", letterSpacing: "0.06em" }}>
  P = primary &nbsp;·&nbsp; R = recommended &nbsp;·&nbsp; L = listed &nbsp;·&nbsp; m = passing &nbsp;·&nbsp; C = cited &nbsp;·&nbsp; - = not found
</div>
```

- [ ] **Step 5: Verify build**

Run: `cd dashboard && npx next build 2>&1 | head -30`
Expected: No TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add dashboard/components/admin/RunDetail.tsx
git commit -m "feat: RunDetail — show mention levels, per-engine scoring, updated badges"
```

---

### Task 12: Dashboard Page Query Filter

**Files:**
- Modify: `dashboard/app/dashboard/page.tsx`

- [ ] **Step 1: Filter runs to only show new-format data**

In `dashboard/app/dashboard/page.tsx`, update the runs query to filter by `run_number IS NOT NULL` on the results side. Since the dashboard page queries `tracker_runs` directly (not `tracker_results`), filter by the presence of `aggregate_avg_mention_level`:

```tsx
const allRuns = (runs as TrackerRun[])?.filter(
  (r) => r.aggregate_avg_mention_level != null
) || [];
```

This ensures old runs (which don't have `aggregate_avg_mention_level`) are excluded from the dashboard.

- [ ] **Step 2: Verify build**

Run: `cd dashboard && npx next build 2>&1 | head -30`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add dashboard/app/dashboard/page.tsx
git commit -m "feat: filter dashboard to only show multi-run format data"
```

---

### Task 13: Integration Smoke Test

**Files:** None (verification only)

- [ ] **Step 1: Run all backend tests**

Run: `cd agents && python -m pytest tests/ -v --ignore=tests/.venv`
Expected: All tests PASS.

- [ ] **Step 2: Run all frontend tests**

Run: `cd dashboard && npx vitest run`
Expected: All tests PASS.

- [ ] **Step 3: Build frontend**

Run: `cd dashboard && npx next build`
Expected: Build succeeds with no errors.

- [ ] **Step 4: Verify end-to-end locally (optional)**

Start the FastAPI server locally and trigger a tracker run for a test client. Verify:
- 5 runs are executed per prompt per engine
- `mention_level` and `mention_level_label` appear in results
- `prompt_scores` table is populated
- `aggregate_avg_mention_level` appears in `tracker_runs`
- Dashboard shows the new KPI layout

- [ ] **Step 5: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: integration fixes from smoke testing"
```
