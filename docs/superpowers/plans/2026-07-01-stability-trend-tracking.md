# Phase 3: Stability & Trend Tracking — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Classify each tracked query's visibility as locked_in, gaining, declining, volatile, or absent by comparing prompt_scores across the last 3 tracker runs, computed on-the-fly.

**Architecture:** A pure Python function aggregates prompt_scores per-query per-run and applies classification rules using mention_rate and avg_mention_level thresholds. A Next.js API endpoint fetches the data from Supabase, applies the same classification in TypeScript, and returns stability data. No new tables or pipeline changes — read-only analysis of existing data.

**Tech Stack:** Python (stability computation), Next.js API route (TypeScript), Supabase (data source)

---

## File Structure

### Backend (new)
- `agents/src/stability.py` — `aggregate_prompt_scores()` and `compute_prompt_stability()` functions
- `agents/tests/test_stability.py` — tests for aggregation and classification

### Dashboard (new)
- `dashboard/app/api/admin/stability/[clientId]/route.ts` — GET endpoint returning stability data
- `dashboard/lib/stability.ts` — shared classification logic (TypeScript)

### Dashboard (modified)
- `dashboard/lib/types.ts` — add `PromptStability` interface

---

### Task 1: Python Stability Computation

**Files:**
- Create: `agents/src/stability.py`
- Create: `agents/tests/test_stability.py`

- [ ] **Step 1: Write the failing tests**

Create `agents/tests/test_stability.py`:

```python
from src.stability import aggregate_prompt_scores, compute_prompt_stability


class TestAggregatePromptScores:
    def test_single_run_single_engine(self):
        prompt_scores = [
            {"run_id": "r1", "query": "best tools", "llm": "chatgpt", "mention_rate": 0.8, "avg_mention_level": 2.5},
        ]
        runs = [{"id": "r1", "ran_at": "2026-07-01T00:00:00Z"}]
        result = aggregate_prompt_scores(prompt_scores, runs)

        assert len(result) == 1
        assert result[0]["run_id"] == "r1"
        assert result[0]["queries"]["best tools"]["mention_rate"] == 0.8
        assert result[0]["queries"]["best tools"]["avg_mention_level"] == 2.5

    def test_multi_engine_averaging(self):
        prompt_scores = [
            {"run_id": "r1", "query": "best tools", "llm": "chatgpt", "mention_rate": 0.8, "avg_mention_level": 3.0},
            {"run_id": "r1", "query": "best tools", "llm": "perplexity", "mention_rate": 0.6, "avg_mention_level": 2.0},
            {"run_id": "r1", "query": "best tools", "llm": "claude", "mention_rate": 1.0, "avg_mention_level": 4.0},
            {"run_id": "r1", "query": "best tools", "llm": "gemini", "mention_rate": 0.4, "avg_mention_level": 1.0},
        ]
        runs = [{"id": "r1", "ran_at": "2026-07-01T00:00:00Z"}]
        result = aggregate_prompt_scores(prompt_scores, runs)

        assert len(result) == 1
        q = result[0]["queries"]["best tools"]
        assert q["mention_rate"] == (0.8 + 0.6 + 1.0 + 0.4) / 4
        # Weighted avg level: (3.0*0.8 + 2.0*0.6 + 4.0*1.0 + 1.0*0.4) / (0.8+0.6+1.0+0.4)
        expected_level = (3.0 * 0.8 + 2.0 * 0.6 + 4.0 * 1.0 + 1.0 * 0.4) / (0.8 + 0.6 + 1.0 + 0.4)
        assert abs(q["avg_mention_level"] - expected_level) < 0.001

    def test_multi_run_ordering(self):
        prompt_scores = [
            {"run_id": "r1", "query": "q1", "llm": "chatgpt", "mention_rate": 0.2, "avg_mention_level": 1.0},
            {"run_id": "r2", "query": "q1", "llm": "chatgpt", "mention_rate": 0.5, "avg_mention_level": 2.0},
            {"run_id": "r3", "query": "q1", "llm": "chatgpt", "mention_rate": 0.8, "avg_mention_level": 3.0},
        ]
        runs = [
            {"id": "r1", "ran_at": "2026-06-29T00:00:00Z"},
            {"id": "r2", "ran_at": "2026-06-30T00:00:00Z"},
            {"id": "r3", "ran_at": "2026-07-01T00:00:00Z"},
        ]
        result = aggregate_prompt_scores(prompt_scores, runs)

        assert len(result) == 3
        assert result[0]["run_id"] == "r1"
        assert result[2]["run_id"] == "r3"

    def test_zero_mention_rate_level_ignored(self):
        prompt_scores = [
            {"run_id": "r1", "query": "q1", "llm": "chatgpt", "mention_rate": 0.0, "avg_mention_level": 0.0},
            {"run_id": "r1", "query": "q1", "llm": "perplexity", "mention_rate": 0.8, "avg_mention_level": 3.0},
        ]
        runs = [{"id": "r1", "ran_at": "2026-07-01T00:00:00Z"}]
        result = aggregate_prompt_scores(prompt_scores, runs)

        q = result[0]["queries"]["q1"]
        assert q["mention_rate"] == (0.0 + 0.8) / 2
        # Weighted: only perplexity contributes (chatgpt has 0 rate)
        assert q["avg_mention_level"] == 3.0


class TestComputePromptStability:
    def test_absent(self):
        runs_data = [
            {"run_id": "r1", "ran_at": "t1", "queries": {"q1": {"mention_rate": 0, "avg_mention_level": 0}}},
            {"run_id": "r2", "ran_at": "t2", "queries": {"q1": {"mention_rate": 0, "avg_mention_level": 0}}},
            {"run_id": "r3", "ran_at": "t3", "queries": {"q1": {"mention_rate": 0, "avg_mention_level": 0}}},
        ]
        result = compute_prompt_stability(runs_data)
        assert len(result) == 1
        assert result[0]["query"] == "q1"
        assert result[0]["stability_class"] == "absent"

    def test_locked_in(self):
        runs_data = [
            {"run_id": "r1", "ran_at": "t1", "queries": {"q1": {"mention_rate": 0.8, "avg_mention_level": 2.5}}},
            {"run_id": "r2", "ran_at": "t2", "queries": {"q1": {"mention_rate": 0.75, "avg_mention_level": 2.7}}},
            {"run_id": "r3", "ran_at": "t3", "queries": {"q1": {"mention_rate": 0.9, "avg_mention_level": 2.8}}},
        ]
        result = compute_prompt_stability(runs_data)
        assert result[0]["stability_class"] == "locked_in"

    def test_gaining_by_rate(self):
        runs_data = [
            {"run_id": "r1", "ran_at": "t1", "queries": {"q1": {"mention_rate": 0.3, "avg_mention_level": 1.5}}},
            {"run_id": "r2", "ran_at": "t2", "queries": {"q1": {"mention_rate": 0.4, "avg_mention_level": 1.5}}},
            {"run_id": "r3", "ran_at": "t3", "queries": {"q1": {"mention_rate": 0.5, "avg_mention_level": 1.5}}},
        ]
        result = compute_prompt_stability(runs_data)
        assert result[0]["stability_class"] == "gaining"

    def test_gaining_by_level(self):
        runs_data = [
            {"run_id": "r1", "ran_at": "t1", "queries": {"q1": {"mention_rate": 0.6, "avg_mention_level": 1.5}}},
            {"run_id": "r2", "ran_at": "t2", "queries": {"q1": {"mention_rate": 0.6, "avg_mention_level": 2.0}}},
            {"run_id": "r3", "ran_at": "t3", "queries": {"q1": {"mention_rate": 0.6, "avg_mention_level": 2.5}}},
        ]
        result = compute_prompt_stability(runs_data)
        assert result[0]["stability_class"] == "gaining"

    def test_declining_by_rate(self):
        runs_data = [
            {"run_id": "r1", "ran_at": "t1", "queries": {"q1": {"mention_rate": 0.8, "avg_mention_level": 2.5}}},
            {"run_id": "r2", "ran_at": "t2", "queries": {"q1": {"mention_rate": 0.6, "avg_mention_level": 2.5}}},
            {"run_id": "r3", "ran_at": "t3", "queries": {"q1": {"mention_rate": 0.5, "avg_mention_level": 2.5}}},
        ]
        result = compute_prompt_stability(runs_data)
        assert result[0]["stability_class"] == "declining"

    def test_volatile(self):
        runs_data = [
            {"run_id": "r1", "ran_at": "t1", "queries": {"q1": {"mention_rate": 0.8, "avg_mention_level": 3.0}}},
            {"run_id": "r2", "ran_at": "t2", "queries": {"q1": {"mention_rate": 0.2, "avg_mention_level": 1.0}}},
            {"run_id": "r3", "ran_at": "t3", "queries": {"q1": {"mention_rate": 0.7, "avg_mention_level": 2.5}}},
        ]
        result = compute_prompt_stability(runs_data)
        assert result[0]["stability_class"] == "volatile"

    def test_rate_wins_tiebreak(self):
        # Rate gaining (+0.2), level declining (-0.6) -> gaining (rate wins)
        runs_data = [
            {"run_id": "r1", "ran_at": "t1", "queries": {"q1": {"mention_rate": 0.4, "avg_mention_level": 3.0}}},
            {"run_id": "r2", "ran_at": "t2", "queries": {"q1": {"mention_rate": 0.5, "avg_mention_level": 2.5}}},
            {"run_id": "r3", "ran_at": "t3", "queries": {"q1": {"mention_rate": 0.6, "avg_mention_level": 2.4}}},
        ]
        result = compute_prompt_stability(runs_data)
        assert result[0]["stability_class"] == "gaining"

    def test_single_run_absent(self):
        runs_data = [
            {"run_id": "r1", "ran_at": "t1", "queries": {"q1": {"mention_rate": 0, "avg_mention_level": 0}}},
        ]
        result = compute_prompt_stability(runs_data)
        assert result[0]["stability_class"] == "absent"

    def test_single_run_volatile(self):
        runs_data = [
            {"run_id": "r1", "ran_at": "t1", "queries": {"q1": {"mention_rate": 0.5, "avg_mention_level": 2.0}}},
        ]
        result = compute_prompt_stability(runs_data)
        assert result[0]["stability_class"] == "volatile"

    def test_multiple_queries(self):
        runs_data = [
            {"run_id": "r1", "ran_at": "t1", "queries": {
                "q1": {"mention_rate": 0.8, "avg_mention_level": 3.0},
                "q2": {"mention_rate": 0, "avg_mention_level": 0},
            }},
            {"run_id": "r2", "ran_at": "t2", "queries": {
                "q1": {"mention_rate": 0.85, "avg_mention_level": 3.1},
                "q2": {"mention_rate": 0, "avg_mention_level": 0},
            }},
            {"run_id": "r3", "ran_at": "t3", "queries": {
                "q1": {"mention_rate": 0.9, "avg_mention_level": 3.2},
                "q2": {"mention_rate": 0, "avg_mention_level": 0},
            }},
        ]
        result = compute_prompt_stability(runs_data)
        stability_map = {r["query"]: r["stability_class"] for r in result}
        assert stability_map["q1"] == "locked_in"
        assert stability_map["q2"] == "absent"

    def test_query_missing_from_earlier_run(self):
        runs_data = [
            {"run_id": "r1", "ran_at": "t1", "queries": {"q1": {"mention_rate": 0.5, "avg_mention_level": 2.0}}},
            {"run_id": "r2", "ran_at": "t2", "queries": {
                "q1": {"mention_rate": 0.6, "avg_mention_level": 2.5},
                "q2": {"mention_rate": 0.8, "avg_mention_level": 3.0},
            }},
            {"run_id": "r3", "ran_at": "t3", "queries": {
                "q1": {"mention_rate": 0.7, "avg_mention_level": 3.0},
                "q2": {"mention_rate": 0.9, "avg_mention_level": 3.5},
            }},
        ]
        result = compute_prompt_stability(runs_data)
        stability_map = {r["query"]: r for r in result}
        assert "q1" in stability_map
        assert "q2" in stability_map
        # q2 only has 2 runs of data — treat missing run as 0/0
        assert stability_map["q2"]["stability_class"] == "gaining"

    def test_output_shape(self):
        runs_data = [
            {"run_id": "r1", "ran_at": "t1", "queries": {"q1": {"mention_rate": 0.8, "avg_mention_level": 2.5}}},
            {"run_id": "r2", "ran_at": "t2", "queries": {"q1": {"mention_rate": 0.8, "avg_mention_level": 2.6}}},
            {"run_id": "r3", "ran_at": "t3", "queries": {"q1": {"mention_rate": 0.8, "avg_mention_level": 2.7}}},
        ]
        result = compute_prompt_stability(runs_data)
        item = result[0]
        assert "query" in item
        assert "stability_class" in item
        assert "current_mention_rate" in item
        assert "current_avg_level" in item
        assert "trend" in item
        assert len(item["trend"]) == 3
        assert "run_id" in item["trend"][0]
        assert "ran_at" in item["trend"][0]
        assert "mention_rate" in item["trend"][0]
        assert "avg_mention_level" in item["trend"][0]

    def test_empty_runs(self):
        result = compute_prompt_stability([])
        assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/jshum/Desktop/code-folders/vvAgentSystem/agents && python3 -m pytest tests/test_stability.py -v`
Expected: FAIL — `cannot import name 'aggregate_prompt_scores' from 'src.stability'`

- [ ] **Step 3: Implement stability.py**

Create `agents/src/stability.py`:

```python
def aggregate_prompt_scores(prompt_scores: list[dict], runs: list[dict]) -> list[dict]:
    run_order = {r["id"]: i for i, r in enumerate(runs)}
    run_meta = {r["id"]: r for r in runs}

    by_run_query: dict[str, dict[str, list[dict]]] = {}
    for ps in prompt_scores:
        rid = ps["run_id"]
        q = ps["query"]
        by_run_query.setdefault(rid, {}).setdefault(q, []).append(ps)

    result = []
    for run in runs:
        rid = run["id"]
        queries = {}
        for query, scores in by_run_query.get(rid, {}).items():
            n = len(scores)
            avg_rate = sum(s["mention_rate"] for s in scores) / n if n > 0 else 0

            total_weight = sum(s["mention_rate"] for s in scores)
            if total_weight > 0:
                avg_level = sum(s["avg_mention_level"] * s["mention_rate"] for s in scores) / total_weight
            else:
                avg_level = 0

            queries[query] = {
                "mention_rate": avg_rate,
                "avg_mention_level": avg_level,
            }

        result.append({
            "run_id": rid,
            "ran_at": run["ran_at"],
            "queries": queries,
        })

    return result


def _classify(rates: list[float], levels: list[float]) -> str:
    n = len(rates)

    if all(r == 0 for r in rates):
        return "absent"

    if n >= 3 and all(r >= 0.7 for r in rates):
        level_range = max(levels) - min(levels)
        if level_range <= 0.5:
            return "locked_in"

    if n >= 2:
        rate_delta = rates[-1] - rates[0]
        level_delta = levels[-1] - levels[0]

        rate_gaining = rate_delta >= 0.1
        rate_declining = rate_delta <= -0.1
        level_gaining = level_delta >= 0.5
        level_declining = level_delta <= -0.5

        if rate_gaining or (not rate_declining and level_gaining):
            return "gaining"

        if rate_declining or (not rate_gaining and level_declining):
            return "declining"

    return "volatile"


def compute_prompt_stability(runs_data: list[dict]) -> list[dict]:
    if not runs_data:
        return []

    all_queries: set[str] = set()
    for run in runs_data:
        all_queries.update(run["queries"].keys())

    result = []
    for query in sorted(all_queries):
        rates = []
        levels = []
        trend = []

        for run in runs_data:
            q_data = run["queries"].get(query, {"mention_rate": 0, "avg_mention_level": 0})
            rates.append(q_data["mention_rate"])
            levels.append(q_data["avg_mention_level"])
            trend.append({
                "run_id": run["run_id"],
                "ran_at": run["ran_at"],
                "mention_rate": q_data["mention_rate"],
                "avg_mention_level": q_data["avg_mention_level"],
            })

        stability_class = _classify(rates, levels)

        result.append({
            "query": query,
            "stability_class": stability_class,
            "current_mention_rate": rates[-1],
            "current_avg_level": levels[-1],
            "trend": trend,
        })

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/jshum/Desktop/code-folders/vvAgentSystem/agents && python3 -m pytest tests/test_stability.py -v`
Expected: All 14 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/src/stability.py agents/tests/test_stability.py
git commit -m "feat: add prompt stability computation with TDD tests"
```

---

### Task 2: TypeScript Stability Classification

**Files:**
- Create: `dashboard/lib/stability.ts`

- [ ] **Step 1: Create the stability classification module**

Create `dashboard/lib/stability.ts`:

```typescript
export type StabilityClass = "locked_in" | "gaining" | "declining" | "volatile" | "absent";

interface QueryScores {
  mention_rate: number;
  avg_mention_level: number;
}

interface RunData {
  run_id: string;
  ran_at: string;
  queries: Record<string, QueryScores>;
}

export interface PromptStabilityResult {
  query: string;
  stability_class: StabilityClass;
  current_mention_rate: number;
  current_avg_level: number;
  trend: {
    run_id: string;
    ran_at: string;
    mention_rate: number;
    avg_mention_level: number;
  }[];
}

function classify(rates: number[], levels: number[]): StabilityClass {
  const n = rates.length;

  if (rates.every((r) => r === 0)) {
    return "absent";
  }

  if (n >= 3 && rates.every((r) => r >= 0.7)) {
    const levelRange = Math.max(...levels) - Math.min(...levels);
    if (levelRange <= 0.5) {
      return "locked_in";
    }
  }

  if (n >= 2) {
    const rateDelta = rates[n - 1] - rates[0];
    const levelDelta = levels[n - 1] - levels[0];

    const rateGaining = rateDelta >= 0.1;
    const rateDeclining = rateDelta <= -0.1;
    const levelGaining = levelDelta >= 0.5;
    const levelDeclining = levelDelta <= -0.5;

    if (rateGaining || (!rateDeclining && levelGaining)) {
      return "gaining";
    }

    if (rateDeclining || (!rateGaining && levelDeclining)) {
      return "declining";
    }
  }

  return "volatile";
}

export function aggregatePromptScores(
  promptScores: { run_id: string; query: string; llm: string; mention_rate: number; avg_mention_level: number }[],
  runs: { id: string; ran_at: string }[]
): RunData[] {
  const byRunQuery: Record<string, Record<string, typeof promptScores>> = {};

  for (const ps of promptScores) {
    if (!byRunQuery[ps.run_id]) byRunQuery[ps.run_id] = {};
    if (!byRunQuery[ps.run_id][ps.query]) byRunQuery[ps.run_id][ps.query] = [];
    byRunQuery[ps.run_id][ps.query].push(ps);
  }

  return runs.map((run) => {
    const queries: Record<string, QueryScores> = {};
    const runScores = byRunQuery[run.id] || {};

    for (const [query, scores] of Object.entries(runScores)) {
      const n = scores.length;
      const avgRate = scores.reduce((s, x) => s + x.mention_rate, 0) / n;

      const totalWeight = scores.reduce((s, x) => s + x.mention_rate, 0);
      const avgLevel =
        totalWeight > 0
          ? scores.reduce((s, x) => s + x.avg_mention_level * x.mention_rate, 0) / totalWeight
          : 0;

      queries[query] = { mention_rate: avgRate, avg_mention_level: avgLevel };
    }

    return { run_id: run.id, ran_at: run.ran_at, queries };
  });
}

export function computePromptStability(runsData: RunData[]): PromptStabilityResult[] {
  if (runsData.length === 0) return [];

  const allQueries = new Set<string>();
  for (const run of runsData) {
    for (const q of Object.keys(run.queries)) {
      allQueries.add(q);
    }
  }

  const results: PromptStabilityResult[] = [];

  for (const query of [...allQueries].sort()) {
    const rates: number[] = [];
    const levels: number[] = [];
    const trend: PromptStabilityResult["trend"] = [];

    for (const run of runsData) {
      const qData = run.queries[query] || { mention_rate: 0, avg_mention_level: 0 };
      rates.push(qData.mention_rate);
      levels.push(qData.avg_mention_level);
      trend.push({
        run_id: run.run_id,
        ran_at: run.ran_at,
        mention_rate: qData.mention_rate,
        avg_mention_level: qData.avg_mention_level,
      });
    }

    results.push({
      query,
      stability_class: classify(rates, levels),
      current_mention_rate: rates[rates.length - 1],
      current_avg_level: levels[levels.length - 1],
      trend,
    });
  }

  return results;
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/lib/stability.ts
git commit -m "feat: add TypeScript stability classification module"
```

---

### Task 3: API Endpoint

**Files:**
- Create: `dashboard/app/api/admin/stability/[clientId]/route.ts`

- [ ] **Step 1: Create the stability API endpoint**

Create `dashboard/app/api/admin/stability/[clientId]/route.ts`:

```typescript
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { aggregatePromptScores, computePromptStability } from "@/lib/stability";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ clientId: string }> }
) {
  const { clientId } = await params;

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { data: clientUser } = await supabase
    .from("client_users")
    .select("role")
    .eq("user_id", user.id)
    .single();

  if (clientUser?.role !== "admin") {
    return Response.json({ error: "Forbidden" }, { status: 403 });
  }

  const admin = createAdminClient();

  const { data: runs, error: runsError } = await admin
    .from("tracker_runs")
    .select("id, ran_at")
    .eq("client_id", clientId)
    .order("ran_at", { ascending: false })
    .limit(3);

  if (runsError) {
    return Response.json({ error: runsError.message }, { status: 500 });
  }

  if (!runs || runs.length === 0) {
    return Response.json([]);
  }

  const runIds = runs.map((r) => r.id);

  const { data: scores, error: scoresError } = await admin
    .from("prompt_scores")
    .select("run_id, query, llm, mention_rate, avg_mention_level")
    .in("run_id", runIds);

  if (scoresError) {
    return Response.json({ error: scoresError.message }, { status: 500 });
  }

  const orderedRuns = [...runs].reverse();
  const runsData = aggregatePromptScores(scores || [], orderedRuns);
  const stability = computePromptStability(runsData);

  return Response.json(stability);
}
```

- [ ] **Step 2: Commit**

```bash
git add "dashboard/app/api/admin/stability/[clientId]/route.ts"
git commit -m "feat: add stability API endpoint for admin"
```

---

### Task 4: Frontend Types

**Files:**
- Modify: `dashboard/lib/types.ts`

- [ ] **Step 1: Add PromptStability interface**

Add this interface after `CompetitiveGap` in `dashboard/lib/types.ts`:

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

- [ ] **Step 2: Commit**

```bash
git add dashboard/lib/types.ts
git commit -m "feat: add PromptStability type"
```

---

### Task 5: Integration Verification

**Files:** None (verification only)

- [ ] **Step 1: Run backend tests**

Run: `cd /Users/jshum/Desktop/code-folders/vvAgentSystem/agents && python3 -m pytest tests/test_stability.py tests/test_competitive_gaps.py -v`
Expected: All tests PASS.

- [ ] **Step 2: Build frontend**

Run: `cd /Users/jshum/Desktop/code-folders/vvAgentSystem/dashboard && npx next build`
Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 3: Verify all stability references**

Run: `grep -rn "stability\|StabilityClass\|PromptStability\|locked_in\|gaining\|declining\|volatile" --include="*.py" --include="*.ts" --include="*.tsx" /Users/jshum/Desktop/code-folders/vvAgentSystem/agents /Users/jshum/Desktop/code-folders/vvAgentSystem/dashboard/lib /Users/jshum/Desktop/code-folders/vvAgentSystem/dashboard/app | grep -v node_modules | grep -v .next`
Expected: References only in the files created by this plan.

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: integration fixes from Phase 3 verification"
```
