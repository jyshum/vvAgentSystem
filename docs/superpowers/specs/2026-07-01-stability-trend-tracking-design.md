# Phase 3: Stability & Trend Tracking — Backend Design Spec

> **Scope:** Backend only. Frontend deferred until all backend phases (2-5) are complete, then built in one unified pass.

## Goal

Classify each tracked query's visibility as locked_in, gaining, declining, volatile, or absent by comparing prompt_scores across the last 3 tracker runs. Computed on-the-fly — no new tables, no pipeline changes.

## Architecture

Stability is a read-only analysis layer on top of existing `prompt_scores` data. Two components:

1. **`agents/src/stability.py`** — Pure function `compute_prompt_stability()` that takes per-run per-query aggregated scores and returns stability classifications. No Supabase dependency — data in, classifications out. Testable in isolation.

2. **`dashboard/app/api/admin/stability/[clientId]/route.ts`** — API endpoint that fetches the last 3 runs + their prompt_scores from Supabase, aggregates per-query per-run (averaging across engines), applies classification logic (reimplemented in TypeScript — it's simple arithmetic), and returns stability data.

The classification logic is implemented in both Python (for potential use in the pipeline, reports, or CLI) and TypeScript (for the API endpoint). Both use the same algorithm and thresholds.

## What Changes

### 1. `agents/src/stability.py` — New file

**`compute_prompt_stability(runs_data: list[dict]) -> list[dict]`**

Input: a list of dicts, each representing one run's per-query aggregated scores:
```python
[
  {
    "run_id": "uuid",
    "ran_at": "2026-07-01T00:00:00Z",
    "queries": {
      "best budgeting tools for med students": {
        "mention_rate": 0.8,
        "avg_mention_level": 2.5,
      },
      "how to manage LOC as a resident": {
        "mention_rate": 0.4,
        "avg_mention_level": 1.0,
      },
    }
  },
  # ... up to 3 runs, ordered oldest to newest
]
```

Output: a list of stability classifications, one per query:
```python
[
  {
    "query": "best budgeting tools for med students",
    "stability_class": "locked_in",
    "current_mention_rate": 0.8,
    "current_avg_level": 2.5,
    "trend": [
      {"run_id": "uuid1", "ran_at": "...", "mention_rate": 0.75, "avg_mention_level": 2.3},
      {"run_id": "uuid2", "ran_at": "...", "mention_rate": 0.78, "avg_mention_level": 2.4},
      {"run_id": "uuid3", "ran_at": "...", "mention_rate": 0.80, "avg_mention_level": 2.5},
    ],
  },
  ...
]
```

**Helper: `aggregate_prompt_scores(prompt_scores: list[dict], run_ids: list[str]) -> list[dict]`**

Takes raw prompt_scores rows (with run_id, query, llm, mention_rate, avg_mention_level) and a list of run_ids (ordered oldest to newest). Returns the `runs_data` format above — per-run per-query scores aggregated across engines (simple average of mention_rate across engines, weighted average of avg_mention_level by mention_rate).

### 2. Classification Logic

For each query, examine its scores across the available runs (1-3 runs). With fewer than 3 runs, classification is limited:

- **1 run:** All queries classified as `volatile` (insufficient data) except those with 0% mention_rate (classified as `absent`).
- **2 runs:** Can detect `absent`, `gaining`, `declining`. Cannot reliably detect `locked_in` or `volatile`.
- **3 runs:** Full classification available.

**Classification rules (3-run window, evaluated in this order — first match wins):**

| Class | Rule |
|---|---|
| **absent** | mention_rate = 0 in all 3 runs |
| **locked_in** | mention_rate >= 0.7 in all 3 runs AND variance of avg_mention_level across runs <= 0.5 |
| **gaining** | Latest run's mention_rate > earliest run's mention_rate by >= 0.1 OR latest avg_level > earliest avg_level by >= 0.5 |
| **declining** | Latest run's mention_rate < earliest run's mention_rate by >= 0.1 OR latest avg_level < earliest avg_level by >= 0.5 |
| **volatile** | Default — doesn't match any above pattern |

**Variance calculation for locked_in:** `variance = max(levels) - min(levels)` across the 3 runs (range, not statistical variance — simpler and sufficient for 3 data points).

**Tie-breaking between gaining and declining:** If mention_rate is gaining but avg_level is declining (or vice versa), use mention_rate as the primary signal. Mention_rate trend wins because frequency is the more fundamental metric.

### 3. `dashboard/app/api/admin/stability/[clientId]/route.ts` — New file

GET endpoint. Auth-guarded (admin only, same pattern as existing admin API routes).

Steps:
1. Fetch last 3 `tracker_runs` for the client, ordered by `ran_at` desc
2. Fetch all `prompt_scores` for those run IDs
3. Aggregate prompt_scores per-query per-run (average across engines)
4. Apply classification logic (same rules as Python, reimplemented in TypeScript)
5. Return JSON array of stability classifications

Response shape:
```json
[
  {
    "query": "best budgeting tools for med students",
    "stability_class": "locked_in",
    "current_mention_rate": 0.8,
    "current_avg_level": 2.5,
    "trend": [
      {"run_id": "uuid1", "ran_at": "...", "mention_rate": 0.75, "avg_mention_level": 2.3},
      {"run_id": "uuid2", "ran_at": "...", "mention_rate": 0.78, "avg_mention_level": 2.4},
      {"run_id": "uuid3", "ran_at": "...", "mention_rate": 0.80, "avg_mention_level": 2.5}
    ]
  }
]
```

### 4. `dashboard/lib/types.ts` — Modified

Add `PromptStability` interface:
```typescript
export interface PromptStability {
  query: string;
  stability_class: "locked_in" | "gaining" | "declining" | "volatile" | "absent";
  current_mention_rate: number;
  current_avg_level: number;
  trend: {
    run_id: string;
    ran_at: string;
    mention_rate: number;
    avg_mention_level: number;
  }[];
}
```

## What's NOT Included

- **No new database tables or migrations** — stability is computed from existing prompt_scores
- **No frontend components** — deferred to unified frontend pass after all backend phases
- **No pipeline changes** — stability is read-only analysis, not part of the tracker execution
- **No mention x citation overlap diagnosis** — this is a Phase 5 feature (gap-closing workflow)

## Cost Impact

Zero. No additional API calls. All computation is local aggregation over existing data.

## Dependencies

- Phase 1 (multi-run scoring + prompt_scores table) must be complete — done
- Requires at least 1 tracker run with prompt_scores data to return results (3 runs for full classification)
- No dependency on Phase 2 (competitive gaps) or Phases 4-5
