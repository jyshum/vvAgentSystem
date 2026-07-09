# Intent-Based Visibility Tracking — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the tracker so the unit of measurement is a buyer *intent* fired as several *paraphrases*, aggregate all metrics at the intent level over one non-branded denominator, and record a per-run query-set signature so trend breaks are detectable — plus a minimal paste path to onboard clients on the intent model.

**Architecture:** Each `queries` row becomes an intent carrying a `paraphrases` list. The tracker (`agents/src/tracker.py`) fires `[canonical] + paraphrases` once each per engine, tags every result with the intent id + canonical text + bucket, and `compute_scores` aggregates at the intent level (equal weight per intent for mention rate, pooled-over-mentioned for level/citation, non-branded only, per-engine consistent). Persistence helpers (`agents/src/upload.py`) key `prompt_scores`/`competitive_gaps` by intent. A small `drift` module hashes the active set; the graph node writes the signature + a `changed` flag. Generation of intents/paraphrases stays manual (a rules doc already exists); a bulk-import endpoint + one paste textarea bring the JSON into the `queries` table.

**Tech Stack:** Python 3.14 + pytest in `agents/.venv`; LangGraph pipeline; Supabase (service-role); Next.js 16 + vitest in `dashboard/`.

**Spec:** `docs/superpowers/specs/2026-07-08-intent-paraphrase-tracking-design.md`. Rules doc (already delivered): `docs/superpowers/references/intent-generation-rules.md`.

---

## Conventions (read before every task)

1. **Python tests:** `cd agents && .venv/bin/python -m pytest tests/ -q`. Baseline before this plan: **289 passed**. Run the whole suite after each Python task — several existing tests call `compute_scores` / `compute_competitive_gaps` and will need updating as behavior changes (that's expected; update them in the same task that changes behavior).
2. **Dashboard:** `cd dashboard && npm test && npx tsc --noEmit && npm run lint && npm run build`. Baseline: **62 tests, 0 lint errors** (3 pre-existing warnings OK).
3. **Result-row vocabulary (used throughout):** a tracker *sample* dict has these keys — `query` (the exact wording fired), `intent_prompt` (the intent's canonical text), `query_id` (intent id, may be `None`), `bucket` (`awareness`/`consideration`/`branded`), `engine`, `model`, `brand_mentioned` (bool), `brand_cited` (bool), `mention_level` (0–4 int), `mention_level_label`, `citation_url`, `competitor_mentions` (list[str]), `response_text`, `run_number`, `timestamp`.
4. **Denominator rule:** `awareness` + `consideration` are the only tracked buckets; `branded` is never fired and is excluded from every aggregate. The constant `NON_BRANDED_BUCKETS = ("awareness", "consideration")` lives in `tracker.py`.
5. **Weighting rule (exact):** `mention_rate` at bucket/overall/per-engine level = **mean of per-intent mention_rates** (equal weight per intent). `avg_mention_level` and `citation_rate` = **pooled over mentioned samples** ("when we appear, how prominently / how often cited"). Per-intent `citation_rate` is `cited / mentioned` (conditional).
6. **Commit at the end of every task.** Work on branch `intent-tracking` (create it in Task 1).
7. **Git:** never `reset`/`checkout <branch>`/`branch -f`. There is an unrelated uncommitted edit at `docs/superpowers/specs/2026-07-03-improvement-pipeline-design.md` and a modified `supabase/schema.sql` (the user pre-added bucket columns) — leave both as they are; stage only the files each task names.

## File structure

**Backend (`agents/`):**
- `src/tracker.py` — modify: fire paraphrases (`run_tracker`), thread `intent_prompt`, skip branded, rewrite `compute_scores`, re-key `compute_competitive_gaps` by intent.
- `src/drift.py` — **new**: `compute_query_set_signature`.
- `src/upload.py` — modify: `_compute_prompt_scores` keyed by intent; `run_row` already carries the new score keys.
- `src/graph/nodes.py` — modify: `load_config` selects `paraphrases`/`slug`/`version`; `run_tracker_node` writes `query_set_signature` + `query_set_changed`.
- `tests/test_intent_aggregation.py`, `tests/test_drift.py` — **new**; plus edits to existing `tests/test_multi_run_tracker.py` / `tests/test_competitive_gaps.py` as behavior changes.

**Database:** `supabase/migrations/011_intent_paraphrases.sql` (new) + `supabase/schema.sql` (fold in).

**Dashboard (`dashboard/`):**
- `app/api/admin/queries/[clientId]/route.ts` — modify: accept `paraphrases`; add bulk import.
- `app/api/admin/queries/query/[queryId]/route.ts` — modify: accept `paraphrases` on PATCH.
- `components/admin/QueryBucketManager.tsx` — modify: add bulk-paste box.
- `lib/types.ts` — modify: `Query.paraphrases`.

---

### Task 1: Migration + schema columns

**Files:**
- Create: `supabase/migrations/011_intent_paraphrases.sql`
- Modify: `supabase/schema.sql`

- [ ] **Step 1: Create the branch**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem
git checkout -b intent-tracking
```

- [ ] **Step 2: Write the migration** `supabase/migrations/011_intent_paraphrases.sql`

```sql
-- 011_intent_paraphrases.sql
-- Intent-based tracking: each queries row is an intent carrying its paraphrases;
-- tracker_runs records a signature of the active intent set so trend breaks show.

alter table public.queries
  add column if not exists paraphrases jsonb default '[]'::jsonb;

alter table public.tracker_runs
  add column if not exists query_set_signature text,
  add column if not exists query_set_changed boolean default false;
```

- [ ] **Step 3: Fold the same columns into `supabase/schema.sql`**

In `supabase/schema.sql`, add `paraphrases jsonb default '[]'::jsonb` to the `create table public.queries (...)` block (after `prompt_text`), and add `query_set_signature text` and `query_set_changed boolean default false` to the `create table public.tracker_runs (...)` block (after `thread_id`).

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/011_intent_paraphrases.sql supabase/schema.sql
git commit -m "feat: schema for intent paraphrases + query-set drift signature (migration 011)"
```

**Deploy note (record, don't run):** run migration 011 in the Supabase SQL editor before onboarding clients on the intent model.

---

### Task 2: Tracker fires an intent's paraphrases

**Files:**
- Modify: `agents/src/tracker.py`
- Test: `agents/tests/test_intent_aggregation.py` (new)

- [ ] **Step 1: Write the failing test** — create `agents/tests/test_intent_aggregation.py`:

```python
from unittest.mock import patch
from src.tracker import run_tracker


def _fake_engines():
    # Two engines; each returns a canned string containing the wording so we can
    # assert which wordings were fired.
    def make(name):
        return {"model": f"{name}-model", "query": lambda w, n=name: f"[{n}] answer to: {w}"}
    return {"chatgpt": make("chatgpt"), "claude": make("claude")}


def test_run_tracker_fires_canonical_plus_paraphrases_and_skips_branded():
    config = {
        "target_queries": [
            {"id": "i1", "prompt_text": "best daycare software", "bucket": "awareness",
             "paraphrases": ["top childcare apps", "daycare management tools"]},
            {"id": "i2", "prompt_text": "brightwheel reviews", "bucket": "branded",
             "paraphrases": ["is brightwheel good"]},
        ],
        "brand_variations": ["Acme"],
        "website_domain": "acme.com",
        "competitors": [],
        "runs_per_paraphrase": 1,
    }
    with patch("src.tracker.load_engines", return_value=_fake_engines()):
        results, scores = run_tracker(config)

    # Awareness intent: (1 canonical + 2 paraphrases) x 2 engines = 6 samples
    awareness = [r for r in results if r["query_id"] == "i1"]
    assert len(awareness) == 6
    fired_wordings = {r["query"] for r in awareness}
    assert fired_wordings == {"best daycare software", "top childcare apps", "daycare management tools"}
    # every awareness sample carries the canonical + bucket
    assert all(r["intent_prompt"] == "best daycare software" for r in awareness)
    assert all(r["bucket"] == "awareness" for r in awareness)
    # branded intent is NOT fired at all
    assert [r for r in results if r["query_id"] == "i2"] == []
```

- [ ] **Step 2: Run it — expect failure**

Run: `cd agents && .venv/bin/python -m pytest tests/test_intent_aggregation.py::test_run_tracker_fires_canonical_plus_paraphrases_and_skips_branded -v`
Expected: FAIL (results lack `intent_prompt`; branded currently fired; paraphrases not fired).

- [ ] **Step 3: Add helpers + thread `intent_prompt`** in `agents/src/tracker.py`. Add near the other `_query_*` helpers:

```python
def _query_paraphrases(query: str | dict) -> list[str]:
    if isinstance(query, str):
        return []
    return query.get("paraphrases") or []


RUNS_PER_PARAPHRASE = 1
NON_BRANDED_BUCKETS = ("awareness", "consideration")
```

In `_run_prompt_on_engine`, add an `intent_prompt: str` parameter (place it right after `query_id`) and include it in each appended result dict:

```python
        results.append({
            "query": query_text,
            "intent_prompt": intent_prompt,
            "query_id": query_id,
            "bucket": bucket,
            ...  # (rest unchanged)
        })
```

- [ ] **Step 4: Rewrite the `run_tracker` loop** to fire the fire-list and skip branded. Replace the body of the `for query in queries:` loop in `run_tracker`:

```python
    runs_per_paraphrase = config.get("runs_per_paraphrase", RUNS_PER_PARAPHRASE)
    total = 0
    count = 0

    for query in queries:
        bucket = _query_bucket(query)
        if bucket == "branded":
            continue  # branded is recall, not visibility — deferred, never fired
        canonical = _query_text(query)
        query_id = _query_id(query)
        wordings = [canonical] + _query_paraphrases(query)
        for engine_name, engine_info in engines.items():
            for wording in wordings:
                count += 1
                print(f"  [{engine_name}] intent={canonical[:40]!r} wording={wording[:40]!r}")
                try:
                    batch = asyncio.run(_run_prompt_on_engine(
                        wording, query_id, canonical, bucket, engine_name, engine_info,
                        brand_variations, website_domain, competitors, runs_per_paraphrase,
                    ))
                    results.extend(batch)
                except Exception as e:
                    print(f"         → ERROR: {e}")
```

Delete the now-unused `total`/`count` precomputation above the loop and the old per-query printing if present. Keep `runs_per_prompt`/`RUNS_PER_PROMPT` only if other code references them; otherwise remove.

Update the `_run_prompt_on_engine` call signature order to match the new `intent_prompt` parameter (canonical passed positionally right after `query_id`).

- [ ] **Step 5: Run the new test — expect pass**

Run: `cd agents && .venv/bin/python -m pytest tests/test_intent_aggregation.py -v`
Expected: PASS.

- [ ] **Step 6: Run the full suite; fix fallout**

Run: `cd agents && .venv/bin/python -m pytest tests/ -q`
Some existing tracker tests may reference the old firing/`runs_per_prompt` behavior. Update those tests to the intent model (pass `target_queries` as intent dicts, expect paraphrase firing). Do not weaken assertions — adjust them to the new, correct behavior.

- [ ] **Step 7: Commit**

```bash
git add agents/src/tracker.py agents/tests/
git commit -m "feat: tracker fires intent paraphrases, tags intent_prompt, skips branded"
```

---

### Task 3: Intent-level `compute_scores`

**Files:**
- Modify: `agents/src/tracker.py` (`compute_scores`)
- Test: `agents/tests/test_intent_aggregation.py`

- [ ] **Step 1: Write the failing tests** — append to `agents/tests/test_intent_aggregation.py`:

```python
from src.tracker import compute_scores


def _sample(query_id, bucket, engine, mentioned, level=0, cited=False, comps=None):
    return {
        "query_id": query_id, "intent_prompt": query_id, "query": query_id,
        "bucket": bucket, "engine": engine,
        "brand_mentioned": mentioned, "brand_cited": cited, "mention_level": level,
        "competitor_mentions": comps or [],
    }


def test_compute_scores_intent_level_and_non_branded():
    engines = {"chatgpt": {}, "claude": {}}
    results = [
        # intent A (awareness): 4 samples, 2 mentioned (levels 2 and 4), 1 of them cited
        _sample("A", "awareness", "chatgpt", True, level=2, cited=True),
        _sample("A", "awareness", "chatgpt", False),
        _sample("A", "awareness", "claude", True, level=4, cited=False),
        _sample("A", "awareness", "claude", False),
        # intent B (consideration): 2 samples, both mentioned (levels 1,3), none cited
        _sample("B", "consideration", "chatgpt", True, level=1),
        _sample("B", "consideration", "claude", True, level=3),
        # intent C (branded): must be ignored entirely
        _sample("C", "branded", "chatgpt", True, level=4, cited=True),
    ]
    s = compute_scores(results, engines, competitors=[])

    # A mention_rate = 2/4 = 0.5 ; B = 2/2 = 1.0 ; headline = mean(0.5, 1.0) = 0.75
    assert s["aggregate_mention_rate"] == 0.75
    assert s["non_branded_mention_rate"] == 0.75
    # avg level pooled over mentioned non-branded samples: levels [2,4,1,3] -> 2.5
    assert s["aggregate_avg_mention_level"] == 2.5
    # citation pooled: 1 cited of 4 mentioned = 0.25
    assert s["aggregate_citation_rate"] == 0.25
    # buckets
    assert s["bucket_scores"]["awareness"]["mention_rate"] == 0.5
    assert s["bucket_scores"]["consideration"]["mention_rate"] == 1.0
    assert s["bucket_scores"]["awareness"]["intent_count"] == 1
    # branded bucket present but contributes nothing to headline
    assert s["bucket_scores"]["branded"]["intent_count"] == 1
    # per-engine excludes branded; chatgpt sees A(1/2) and B(1/1) -> mean = 0.75
    assert s["per_engine"]["chatgpt"]["mention_rate"] == 0.75


def test_compute_scores_competitors_non_branded_only():
    engines = {"chatgpt": {}}
    results = [
        _sample("A", "awareness", "chatgpt", False, comps=["KinderCare"]),
        _sample("A", "awareness", "chatgpt", False, comps=[]),
        _sample("C", "branded", "chatgpt", True, comps=["KinderCare"]),  # ignored
    ]
    s = compute_scores(results, engines, competitors=["KinderCare"])
    # 1 of 2 non-branded samples mention KinderCare
    assert s["competitor_scores"]["KinderCare"]["mention_rate"] == 0.5


def test_compute_scores_empty():
    s = compute_scores([], {"chatgpt": {}}, competitors=[])
    assert s["aggregate_mention_rate"] == 0
    assert s["bucket_scores"]["awareness"]["intent_count"] == 0
```

- [ ] **Step 2: Run — expect failure**

Run: `cd agents && .venv/bin/python -m pytest tests/test_intent_aggregation.py -k compute_scores -v`
Expected: FAIL (current `compute_scores` groups per (query,engine), includes branded in per_engine, no intent-level equal weighting).

- [ ] **Step 3: Replace `compute_scores`** in `agents/src/tracker.py` with:

```python
def _rate_stats(samples: list[dict]) -> dict:
    """mention_rate + avg_mention_level (over mentioned) + citation_rate (conditional)."""
    total = len(samples)
    if total == 0:
        return {"mention_rate": 0.0, "avg_mention_level": 0.0, "citation_rate": 0.0, "count": 0}
    mentioned = [s for s in samples if s.get("brand_mentioned")]
    m = len(mentioned)
    cited = sum(1 for s in mentioned if s.get("brand_cited"))
    return {
        "mention_rate": m / total,
        "avg_mention_level": (sum(s.get("mention_level", 0) for s in mentioned) / m) if m else 0.0,
        "citation_rate": (cited / m) if m else 0.0,
        "count": total,
    }


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def compute_scores(results: list[dict], engines: dict, competitors: list[str] | None = None) -> dict:
    engine_names = set(engines)
    samples = [r for r in results if r["engine"] in engine_names]

    intents: dict = {}
    intent_bucket: dict = {}
    for s in samples:
        iid = s.get("query_id") or s.get("intent_prompt") or s["query"]
        intents.setdefault(iid, []).append(s)
        intent_bucket[iid] = s.get("bucket") or "consideration"

    intent_rate = {iid: _rate_stats(iss)["mention_rate"] for iid, iss in intents.items()}
    non_branded_ids = [iid for iid in intents if intent_bucket[iid] in NON_BRANDED_BUCKETS]
    non_branded_samples = [s for iid in non_branded_ids for s in intents[iid]]

    pooled = _rate_stats(non_branded_samples)
    aggregate_mention_rate = _mean([intent_rate[iid] for iid in non_branded_ids])

    bucket_scores = {}
    for bucket in ("awareness", "consideration", "branded"):
        ids = [iid for iid in intents if intent_bucket[iid] == bucket]
        b = _rate_stats([s for iid in ids for s in intents[iid]])
        bucket_scores[bucket] = {
            "mention_rate": _mean([intent_rate[iid] for iid in ids]),
            "avg_mention_level": b["avg_mention_level"],
            "citation_rate": b["citation_rate"],
            "intent_count": len(ids),
        }

    per_engine = {}
    for engine_name in engine_names:
        eng_intent_rates = []
        eng_samples = []
        for iid in non_branded_ids:
            iss = [s for s in intents[iid] if s["engine"] == engine_name]
            if not iss:
                continue
            eng_intent_rates.append(_rate_stats(iss)["mention_rate"])
            eng_samples.extend(iss)
        ep = _rate_stats(eng_samples)
        per_engine[engine_name] = {
            "mention_rate": _mean(eng_intent_rates),
            "avg_mention_level": ep["avg_mention_level"],
            "citation_rate": ep["citation_rate"],
        }

    competitor_scores = {}
    for comp in (competitors or []):
        c = sum(1 for s in non_branded_samples if comp in s.get("competitor_mentions", []))
        competitor_scores[comp] = {
            "mention_rate": c / len(non_branded_samples) if non_branded_samples else 0.0,
        }

    return {
        "per_engine": per_engine,
        "aggregate_mention_rate": aggregate_mention_rate,
        "non_branded_mention_rate": aggregate_mention_rate,
        "aggregate_avg_mention_level": pooled["avg_mention_level"],
        "aggregate_citation_rate": pooled["citation_rate"],
        "bucket_scores": bucket_scores,
        "competitor_scores": competitor_scores,
    }
```

- [ ] **Step 4: Run the new tests — expect pass**

Run: `cd agents && .venv/bin/python -m pytest tests/test_intent_aggregation.py -k compute_scores -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite; update existing score tests**

Run: `cd agents && .venv/bin/python -m pytest tests/ -q`
`tests/test_scorer.py` / `tests/test_multi_run_tracker.py` may assert the old `compute_scores` shape (e.g. `all_prompt_mention_rate`, per-engine including branded). Update them to the new keys/behavior. The returned dict no longer includes `all_prompt_mention_rate`; remove assertions on it.

- [ ] **Step 6: Commit**

```bash
git add agents/src/tracker.py agents/tests/
git commit -m "feat: intent-level, non-branded, equal-weight-per-intent scoring"
```

---

### Task 4: `prompt_scores` keyed by intent

**Files:**
- Modify: `agents/src/upload.py` (`_compute_prompt_scores`)
- Test: `agents/tests/test_intent_aggregation.py`

- [ ] **Step 1: Write the failing test** — append:

```python
from src.upload import _compute_prompt_scores


def test_prompt_scores_keyed_by_intent():
    results = [
        # one intent, two paraphrases, same engine -> ONE prompt_scores row
        {"query_id": "i1", "intent_prompt": "best daycare software", "query": "best daycare software",
         "bucket": "awareness", "engine": "chatgpt", "brand_mentioned": True, "brand_cited": True, "mention_level": 3},
        {"query_id": "i1", "intent_prompt": "best daycare software", "query": "top childcare apps",
         "bucket": "awareness", "engine": "chatgpt", "brand_mentioned": False, "brand_cited": False, "mention_level": 0},
    ]
    rows = _compute_prompt_scores("client-1", "run-1", results)
    assert len(rows) == 1
    row = rows[0]
    assert row["query_id"] == "i1"
    assert row["query"] == "best daycare software"   # canonical, not a paraphrase
    assert row["bucket"] == "awareness"
    assert row["llm"] == "chatgpt"
    assert row["mention_rate"] == 0.5                  # 1 of 2 wordings
    assert row["citation_rate"] == 1.0                 # 1 cited of 1 mentioned
```

- [ ] **Step 2: Run — expect failure**

Run: `cd agents && .venv/bin/python -m pytest tests/test_intent_aggregation.py -k prompt_scores -v`
Expected: FAIL (current grouping is by `(query, engine)`, so two paraphrases become two rows; `query` is a paraphrase).

- [ ] **Step 3: Re-key `_compute_prompt_scores`** in `agents/src/upload.py`. Replace the grouping key and the `query` field:

```python
def _compute_prompt_scores(client_id: str, run_id: str, results: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for r in results:
        intent_key = r.get("query_id") or r.get("intent_prompt") or r["query"]
        groups[(intent_key, r["engine"])].append(r)

    scores = []
    for (_intent_key, engine), runs in groups.items():
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
            "query_id": runs[0].get("query_id"),
            "query": runs[0].get("intent_prompt") or runs[0]["query"],
            "bucket": runs[0].get("bucket", "consideration"),
            "llm": engine,
            "mention_rate": mention_rate,
            "avg_mention_level": avg_level,
            "citation_rate": citation_rate,
        })
    return scores
```

- [ ] **Step 4: Run — expect pass, then full suite**

Run: `cd agents && .venv/bin/python -m pytest tests/test_intent_aggregation.py -k prompt_scores -v` → PASS.
Run: `cd agents && .venv/bin/python -m pytest tests/ -q` → all pass (update any existing `_compute_prompt_scores` test to the intent grouping).

- [ ] **Step 5: Commit**

```bash
git add agents/src/upload.py agents/tests/
git commit -m "feat: prompt_scores keyed by intent, query stores canonical text"
```

---

### Task 5: `competitive_gaps` keyed by intent

**Files:**
- Modify: `agents/src/tracker.py` (`compute_competitive_gaps`)
- Test: `agents/tests/test_intent_aggregation.py`

- [ ] **Step 1: Write the failing test** — append:

```python
from src.tracker import compute_competitive_gaps


def test_competitive_gaps_grouped_by_intent():
    results = [
        # one intent, two paraphrases; client mentioned in 1 of 2; competitor in 2 of 2
        {"query_id": "i1", "intent_prompt": "best daycare software", "query": "best daycare software",
         "bucket": "consideration", "engine": "chatgpt", "brand_mentioned": True, "mention_level": 2,
         "competitor_mentions": ["KinderCare"]},
        {"query_id": "i1", "intent_prompt": "best daycare software", "query": "top childcare apps",
         "bucket": "consideration", "engine": "chatgpt", "brand_mentioned": False, "mention_level": 0,
         "competitor_mentions": ["KinderCare"]},
    ]
    gaps = compute_competitive_gaps(results, ["KinderCare"])
    assert len(gaps) == 1                       # one intent -> one gap row (not two)
    g = gaps[0]
    assert g["query"] == "best daycare software"  # canonical
    assert g["query_id"] == "i1"
    assert g["bucket"] == "consideration"
    assert g["client_mention_rate"] == 0.5
    assert g["competitor_data"][0]["name"] == "KinderCare"
    assert g["competitor_data"][0]["mention_rate"] == 1.0
```

- [ ] **Step 2: Run — expect failure**

Run: `cd agents && .venv/bin/python -m pytest tests/test_intent_aggregation.py -k competitive_gaps -v`
Expected: FAIL (current grouping by `r["query"]` splits paraphrases into two gaps).

- [ ] **Step 3: Re-key `compute_competitive_gaps`** in `agents/src/tracker.py`. Change the grouping from unique `query` text to unique intent, and use the canonical for `query`:

```python
def compute_competitive_gaps(results: list[dict], competitors: list[str]) -> list[dict]:
    if not results:
        return []

    by_intent: dict = {}
    for r in results:
        iid = r.get("query_id") or r.get("intent_prompt") or r["query"]
        by_intent.setdefault(iid, []).append(r)

    gaps = []
    for _iid, query_results in by_intent.items():
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
            "query": query_results[0].get("intent_prompt") or query_results[0]["query"],
            "query_id": query_results[0].get("query_id"),
            "bucket": query_results[0].get("bucket") or "consideration",
            "client_mention_rate": client_mention_rate,
            "client_avg_mention_level": client_avg_level,
            "competitor_data": competitor_data,
        })

    return gaps
```

- [ ] **Step 4: Run — expect pass, then full suite**

Run: `cd agents && .venv/bin/python -m pytest tests/test_intent_aggregation.py -k competitive_gaps -v` → PASS.
Run: `cd agents && .venv/bin/python -m pytest tests/ -q` → all pass (update `tests/test_competitive_gaps.py` if it assumed per-query-text grouping).

- [ ] **Step 5: Commit**

```bash
git add agents/src/tracker.py agents/tests/
git commit -m "feat: competitive gaps grouped by intent across paraphrases"
```

---

### Task 6: Drift signature module

**Files:**
- Create: `agents/src/drift.py`
- Test: `agents/tests/test_drift.py` (new)

- [ ] **Step 1: Write the failing tests** — create `agents/tests/test_drift.py`:

```python
from src.drift import compute_query_set_signature


def _intent(slug, version=1, paraphrases=None, prompt="p"):
    return {"slug": slug, "version": version, "prompt_text": prompt, "paraphrases": paraphrases or []}


def test_signature_stable_for_same_set_regardless_of_order():
    a = [_intent("x", paraphrases=["a", "b"]), _intent("y")]
    b = [_intent("y"), _intent("x", paraphrases=["b", "a"])]  # reordered intents + paraphrases
    assert compute_query_set_signature(a) == compute_query_set_signature(b)


def test_signature_changes_when_paraphrase_edited():
    a = [_intent("x", paraphrases=["a", "b"])]
    b = [_intent("x", paraphrases=["a", "c"])]
    assert compute_query_set_signature(a) != compute_query_set_signature(b)


def test_signature_changes_when_intent_added_or_removed():
    a = [_intent("x")]
    b = [_intent("x"), _intent("y")]
    assert compute_query_set_signature(a) != compute_query_set_signature(b)


def test_signature_changes_on_version_bump():
    a = [_intent("x", version=1)]
    b = [_intent("x", version=2)]
    assert compute_query_set_signature(a) != compute_query_set_signature(b)


def test_empty_set_is_stable():
    assert compute_query_set_signature([]) == compute_query_set_signature([])
```

- [ ] **Step 2: Run — expect failure**

Run: `cd agents && .venv/bin/python -m pytest tests/test_drift.py -v`
Expected: FAIL (`src.drift` does not exist).

- [ ] **Step 3: Implement** `agents/src/drift.py`:

```python
import hashlib
import json


def compute_query_set_signature(intents: list[dict]) -> str:
    """A hash of the active intent set. Changes when an intent is added/removed,
    an intent's version bumps, or any paraphrase/canonical wording is edited —
    i.e. any change that breaks cycle-over-cycle comparability."""
    parts = []
    for q in intents:
        slug = q.get("slug") or q.get("prompt_text", "")
        version = q.get("version", 1)
        canonical = q.get("prompt_text", "")
        paraphrases = sorted(q.get("paraphrases") or [])
        inner = hashlib.sha256(
            json.dumps([canonical, paraphrases], sort_keys=True).encode()
        ).hexdigest()
        parts.append(f"{slug}:{version}:{inner}")
    joined = "\n".join(sorted(parts))
    return hashlib.sha256(joined.encode()).hexdigest()
```

- [ ] **Step 4: Run — expect pass**

Run: `cd agents && .venv/bin/python -m pytest tests/test_drift.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/src/drift.py agents/tests/test_drift.py
git commit -m "feat: query-set drift signature"
```

---

### Task 7: Wire drift + paraphrases into the graph node

**Files:**
- Modify: `agents/src/graph/nodes.py` (`load_config` and `run_tracker_node`)
- Test: `agents/tests/test_graph_nodes.py`

- [ ] **Step 1: Write the failing test** — add to `agents/tests/test_graph_nodes.py` (match the file's existing mock-Supabase pattern; this asserts the `tracker_runs` insert payload):

```python
def test_run_tracker_node_writes_drift_signature(...existing fixtures...):
    # Arrange state["client_config"]["target_queries"] with two intents (with slug/version/paraphrases).
    # Mock run_tracker to return ([], {...scores...}); mock the previous-run query returning a
    # DIFFERENT prior signature.
    # Act: run_tracker_node(state)
    # Assert the tracker_runs insert dict contains a non-null "query_set_signature"
    # and "query_set_changed" == True (prior signature differed).
```

(If the existing test file's mock shape makes asserting the insert payload hard, add a smaller focused test that calls `src.drift.compute_query_set_signature` on the config's `target_queries` and asserts it matches what the node computes — the node must use the same helper.)

- [ ] **Step 2: Run — expect failure**

Run: `cd agents && .venv/bin/python -m pytest tests/test_graph_nodes.py -k drift -v`

- [ ] **Step 3: Extend `load_config`** in `agents/src/graph/nodes.py` — add `paraphrases,slug,version` to the queries select so the signature and firing have what they need:

```python
    queries_resp = (
        sb.table("queries")
        .select("id,prompt_text,paraphrases,bucket,set_type,slug,version")
        .eq("client_id", state["client_id"])
        .eq("status", "active")
        .order("bucket")
        .order("created_at")
        .execute()
    )
```

- [ ] **Step 4: Write the signature in `run_tracker_node`.** At the top of the function add the import and compute the signature from the config's intents; include the two new fields in the `tracker_runs` insert dict:

```python
from src.drift import compute_query_set_signature
...
        intents = state["client_config"].get("target_queries", [])
        signature = compute_query_set_signature(intents)
        prev = (
            sb.table("tracker_runs")
            .select("query_set_signature")
            .eq("client_id", state["client_id"])
            .order("ran_at", desc=True)
            .limit(1)
            .execute()
        )
        prev_sig = prev.data[0]["query_set_signature"] if prev.data else None
        query_set_changed = prev_sig is not None and prev_sig != signature

        run_row = sb.table("tracker_runs").insert({
            "client_id": state["client_id"],
            "aggregate_mention_rate": scores.get("aggregate_mention_rate", 0),
            "non_branded_mention_rate": scores.get("non_branded_mention_rate", scores.get("aggregate_mention_rate", 0)),
            "aggregate_avg_mention_level": scores.get("aggregate_avg_mention_level", 0),
            "bucket_scores": scores.get("bucket_scores", {}),
            "per_engine_scores": scores.get("per_engine", {}),
            "competitor_scores": scores.get("competitor_scores", {}),
            "discovered_competitors": [],
            "thread_id": state.get("thread_id"),
            "query_set_signature": signature,
            "query_set_changed": query_set_changed,
        }).execute()
```

Also confirm the `result_rows` built in `run_tracker_node` already include `query_id` and `bucket` (they do); no change needed there — the wording stays in `query`.

- [ ] **Step 5: Run the focused test, then full suite**

Run: `cd agents && .venv/bin/python -m pytest tests/test_graph_nodes.py -q` → pass.
Run: `cd agents && .venv/bin/python -m pytest tests/ -q` → **all pass**.

- [ ] **Step 6: Commit**

```bash
git add agents/src/graph/nodes.py agents/tests/test_graph_nodes.py
git commit -m "feat: graph node loads paraphrases and records query-set drift signature"
```

---

### Task 8: Admin API — paraphrases + bulk import

**Files:**
- Modify: `dashboard/app/api/admin/queries/[clientId]/route.ts`, `dashboard/app/api/admin/queries/query/[queryId]/route.ts`, `dashboard/lib/types.ts`

- [ ] **Step 1: Add `paraphrases` to the `Query` type** in `dashboard/lib/types.ts` (in the `Query` interface, after `prompt_text`):

```ts
  paraphrases: string[];
```

- [ ] **Step 2: Accept `paraphrases` + add bulk import** in `dashboard/app/api/admin/queries/[clientId]/route.ts`. Add a validation helper and extend `POST` so it handles both a single intent and a `{ intents: [...] }` bulk payload:

```ts
function validParaphrases(p: unknown): string[] {
  if (p === undefined || p === null) return [];
  if (!Array.isArray(p) || p.some((x) => typeof x !== "string" || !x.trim())) {
    throw new Error("paraphrases must be an array of non-empty strings");
  }
  return (p as string[]).map((x) => x.trim());
}
```

In `POST`, before the single-intent path, handle bulk:

```ts
  const body = await request.json();

  // Bulk import: { intents: [{ prompt_text, bucket, paraphrases }] }
  if (Array.isArray(body?.intents)) {
    const admin = createAdminClient();
    const rows = [];
    for (const it of body.intents) {
      if (!it?.prompt_text || typeof it.prompt_text !== "string" || !it.prompt_text.trim()) {
        return Response.json({ error: "each intent needs prompt_text" }, { status: 400 });
      }
      if (it.bucket !== undefined && !BUCKETS.has(it.bucket)) {
        return Response.json({ error: `invalid bucket: ${it.bucket}` }, { status: 400 });
      }
      let paraphrases: string[];
      try { paraphrases = validParaphrases(it.paraphrases); }
      catch (e) { return Response.json({ error: (e as Error).message }, { status: 400 }); }
      rows.push({
        client_id: clientId,
        prompt_text: it.prompt_text.trim(),
        slug: generateSlug(it.prompt_text),
        bucket: it.bucket || "consideration",
        set_type: "core",
        paraphrases,
      });
    }
    const { data, error } = await admin.from("queries").insert(rows).select();
    if (error) return Response.json({ error: error.message }, { status: 500 });
    return Response.json(data, { status: 201 });
  }
```

Then in the existing single-intent path, parse and store `paraphrases`:

```ts
  const { prompt_text, bucket, set_type } = body;
  // ...existing validation...
  let paraphrases: string[];
  try { paraphrases = validParaphrases(body.paraphrases); }
  catch (e) { return Response.json({ error: (e as Error).message }, { status: 400 }); }
  // ...in the .insert({...}) add:  paraphrases,
```

- [ ] **Step 3: Accept `paraphrases` on PATCH** in `dashboard/app/api/admin/queries/query/[queryId]/route.ts`. In the PATCH handler, when `body.paraphrases !== undefined`, validate (array of non-empty strings) and include it in the update object. (Match the file's existing update-building pattern; reject invalid with 400.)

- [ ] **Step 4: Verify**

Run: `cd dashboard && npx tsc --noEmit` → clean.
Run: `cd dashboard && npm run build` → succeeds (both query routes compile).

- [ ] **Step 5: Commit**

```bash
git add dashboard/app/api/admin/queries dashboard/lib/types.ts
git commit -m "feat: queries API accepts paraphrases + bulk intent import"
```

---

### Task 9: Config paste box for bulk intent import

**Files:**
- Modify: `dashboard/components/admin/QueryBucketManager.tsx`

- [ ] **Step 1: Add bulk-import state + handler.** In `QueryBucketManager`, add:

```tsx
  const [bulkText, setBulkText] = useState("");
  const [bulkBusy, setBulkBusy] = useState(false);

  async function bulkImport() {
    setError(null);
    let intents: unknown;
    try { intents = JSON.parse(bulkText); }
    catch { setError("Paste must be a valid JSON array of intents"); return; }
    if (!Array.isArray(intents)) { setError("Expected a JSON array"); return; }
    setBulkBusy(true);
    const res = await fetch(`/api/admin/queries/${clientId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ intents }),
    });
    setBulkBusy(false);
    if (!res.ok) {
      const b = await res.json().catch(() => ({}));
      setError(b.error || "Bulk import failed");
      return;
    }
    const created = (await res.json()) as Query[];
    setQueries((cur) => [...cur, ...created]);
    setBulkText("");
    router.refresh();
  }
```

- [ ] **Step 2: Add the paste UI** above the bucket grid (after the error line, before `<div className="grid ...">`):

```tsx
      <details className="mb-5">
        <summary className="font-mono text-[9px] tracking-[0.14em] uppercase cursor-pointer" style={{ color: "var(--faint)" }}>
          Bulk import intents (paste JSON)
        </summary>
        <textarea
          value={bulkText}
          onChange={(e) => setBulkText(e.target.value)}
          placeholder='[{"prompt_text":"best daycare software","bucket":"awareness","paraphrases":["top childcare apps"]}]'
          className="w-full min-h-[120px] mt-3 resize-y bg-transparent font-mono text-[11px] leading-snug outline-none placeholder:opacity-40"
          style={{ color: "var(--white)", border: "1px solid var(--hair)", padding: "10px" }}
        />
        <button
          type="button"
          disabled={bulkBusy || !bulkText.trim()}
          onClick={bulkImport}
          className="mt-2 font-mono text-[9px] tracking-[0.14em] uppercase py-2.5 px-5 transition-opacity disabled:opacity-40"
          style={{ background: "var(--white)", color: "var(--ink)" }}
        >
          {bulkBusy ? "Importing" : "Import Intents"}
        </button>
      </details>
```

- [ ] **Step 3: Verify**

Run: `cd dashboard && npx tsc --noEmit && npm run lint && npm run build` → clean (0 errors), build succeeds.
Run: `cd dashboard && npm test` → 62 pass (unchanged).

- [ ] **Step 4: Commit**

```bash
git add dashboard/components/admin/QueryBucketManager.tsx
git commit -m "feat: bulk intent/paraphrase paste box in query config"
```

---

### Task 10: Final verification

- [ ] **Step 1: Full suites**

Run: `cd agents && .venv/bin/python -m pytest tests/ -q` → all pass.
Run: `cd dashboard && npm test && npx tsc --noEmit && npm run lint && npm run build` → 62 tests, 0 lint errors, build ok.

- [ ] **Step 2: Spec walk.** Open the spec and confirm each requirement maps to shipped code: `queries.paraphrases` (Task 1/8), tracker fires paraphrases + skips branded (Task 2), intent-level aggregation with the exact formulas + per-engine non-branded (Task 3), `prompt_scores` per intent (Task 4), `competitive_gaps` per intent (Task 5), drift signature + `query_set_changed` (Task 6/7), bulk import + paste box (Task 8/9), rules doc (already delivered). Card-routing logic unchanged (confirm no card files were touched).

- [ ] **Step 3: Deploy checklist (report, don't run):** run migration `011` in Supabase; redeploy the Railway agent server; then onboard clients via the rules-doc → paste-box flow. Branded intents are not fired; comparison folds into consideration.

---

## Self-review notes (applied)

- **Spec coverage:** every in-scope item (data model, firing, aggregation formulas, prompt_scores/gaps re-keying, per-engine fix, drift signal, bulk-entry path, rules doc) maps to a task. Frontend display, comparison bucket, branded tracking, and automated generation are explicitly deferred and have no tasks (correct).
- **Type consistency:** the sample-dict keys (`intent_prompt`, `query_id`, `bucket`) are introduced in Task 2 and used identically in Tasks 3/4/5; `compute_scores` return keys match what `nodes.py`/`upload.py` read; `_rate_stats`/`_mean`/`NON_BRANDED_BUCKETS`/`compute_query_set_signature` names are stable across tasks.
- **No placeholders:** every code step shows the actual code; Task 7's test is described against the file's existing mock pattern with a concrete fallback assertion.
