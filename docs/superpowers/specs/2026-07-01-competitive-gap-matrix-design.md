# Phase 2: Competitive Gap Matrix — Backend Design Spec

> **Scope:** Backend only. Frontend deferred until all backend phases (2-5) are complete, then built in one unified pass.

## Goal

Enrich the tracker pipeline to compute per-prompt competitor mention rates, store gap analysis data in a new `competitive_gaps` table, and auto-discover non-configured competitors that appear across 3+ distinct prompts.

## Architecture

The existing multi-run pipeline (Phase 1) already detects competitors via binary string matching (`detect_competitors()`) and stores `competitor_mentions` as a flat list of names per result. Phase 2 adds a scoring layer on top: after all runs complete, `compute_scores()` produces per-prompt competitor mention rates and identifies non-configured brands. Upload writes this to a new table. No new API calls — all computation is local over existing result data.

## What Changes

### 1. `agents/src/tracker.py` — `compute_scores()`

Add two new keys to the returned scores dict:

**`competitor_prompt_scores`** — Per-query, per-engine competitor mention rates:
```python
[
  {
    "query": "best budgeting tools for med students",
    "engine": "chatgpt",
    "competitors": {
      "MD Financial": {"mention_rate": 0.8, "mentioned_count": 4, "total_runs": 5},
      "Wealthsimple": {"mention_rate": 0.4, "mentioned_count": 2, "total_runs": 5},
    }
  },
  ...
]
```

Computed by grouping results by `(query, engine)` and counting how many of the 5 runs each competitor name appears in.

**`discovered_competitors`** — Non-configured brands appearing in 3+ distinct prompts:
```python
[
  {"name": "NerdWallet", "prompt_count": 5, "total_mentions": 12},
  {"name": "YNAB", "prompt_count": 3, "total_mentions": 7},
]
```

Detection: after scoring, collect all names from `competitor_mentions` across all results. Filter out configured competitors. Group remaining names by distinct query text. Any name appearing in 3+ distinct queries qualifies.

Note: `competitor_mentions` currently contains only configured competitors (from `detect_competitors()`). True auto-discovery of non-configured brands would require NLP entity extraction or cross-client brand scanning, both of which add complexity disproportionate to their value at this stage.

**Decision:** Defer auto-discovery to a future enhancement. The `discovered_competitors` column is added to the schema now (so no migration needed later) but is populated as `[]` for now. The gap matrix still delivers its primary value — per-prompt competitive comparison against configured competitors.

### 2. `agents/src/upload.py`

**New function `_compute_competitive_gaps()`:**

Takes `client_id`, `run_id`, results, and `competitor_prompt_scores` from compute_scores. Produces rows for the `competitive_gaps` table:

For each distinct query:
- Compute client's aggregate mention rate and avg mention level across all engines for that query (from the results)
- Collect competitor data from `competitor_prompt_scores` entries for that query, aggregated across engines
- Include per-engine breakdown in the JSONB `competitor_data` field

**Updated `upload_run()`:**
- Call `_compute_competitive_gaps()` and insert into `competitive_gaps` table
- Write `discovered_competitors` to the `tracker_runs` row

### 3. `agents/src/graph/nodes.py`

**Updated `run_tracker_node()`:**
- Same gap computation and upload as `upload.py`
- Write `discovered_competitors` to the tracker_runs row after insert

### 4. Database Schema

**New table: `competitive_gaps`**

```sql
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
```

`competitor_data` JSONB shape:
```json
[
  {
    "name": "MD Financial",
    "mention_rate": 0.75,
    "per_engine": {
      "chatgpt": 0.8,
      "perplexity": 1.0,
      "claude": 0.6,
      "gemini": 0.6
    }
  }
]
```

Indexes: `run_id`, `client_id`.

RLS: admin full access, client read own (same pattern as `prompt_scores`).

**Modified: `tracker_runs`**

```sql
alter table public.tracker_runs
  add column discovered_competitors jsonb default '[]';
```

Shape: `[{"name": "NerdWallet", "prompt_count": 5, "total_mentions": 12}]`

## What's NOT Included

- **No frontend components** — deferred to unified frontend pass after all backend phases complete
- **No competitor mention level classification** — competitors tracked as binary mention rate only (saves ~1200 Haiku calls/cycle)
- **No crowd-source detection** — deferred to Phase 5 (Gap-Closing Workflow)
- **No gap priority/type diagnosis** — deferred to Phase 5
- **No `detect_competitors()` changes** — existing binary detection is sufficient
- **Auto-discovery deferred** — schema column added but populated as `[]`; real entity detection is a future enhancement

## Cost Impact

Zero additional API calls. All computation is local aggregation over existing result data.

## Dependencies

- Phase 1 (multi-run scoring) must be complete — ✅ done
- No dependency on Phases 3-5
