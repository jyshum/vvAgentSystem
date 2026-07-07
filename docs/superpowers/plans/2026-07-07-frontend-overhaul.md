# Admin Frontend Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the admin dashboard around AI-visibility metrics — Visibility Board home, client drilldown with 6 tabs, grouped approvals inbox, retrospective run detail — plus four small backend changes (thread linking, community-check cards, preview_url persistence, rejected-ids in approve).

**Architecture:** Next.js 16 server components query Supabase directly (existing pattern via `createAdminClient()`); pure derivation helpers live in `dashboard/lib/` and are unit-tested with vitest. Interactive pieces (heat-table expansion, approval decisions) are client components fed by admin API routes. Backend: LangGraph pipeline on FastAPI (`agents/`), pytest-tested.

**Tech Stack:** Next.js 16.2.9 (App Router, async `params`), React 19, Tailwind v4 + CSS variables theme, Supabase (service-role client), vitest 4 (+ jsdom/@testing-library/react added in Task 8), Python 3.14 + pytest in `agents/.venv`.

**Spec:** `docs/superpowers/specs/2026-07-07-frontend-overhaul-design.md` (decisions in `2026-07-06-frontend-brainstorm-decisions.md`). Mockups (hierarchy/content only, polish = existing theme): `docs/superpowers/mockups/visibility-board-v2.html`, `client-drilldown-v4.html`, `pages-tab-v2.html`, `approvals-inbox.html`, `run-detail.html`.

---

## Conventions (read before every task)

1. **Next.js 16 warning:** `dashboard/AGENTS.md` says this Next version may differ from your training data. If unsure about an API, read the relevant guide in `dashboard/node_modules/next/dist/docs/01-app/`. Known: route `params` is a `Promise` — `const { id } = await params;`.
2. **Theme:** dark ink theme via CSS vars in `dashboard/app/globals.css`: `--ink --ink-soft --ink-2 --white --mute --faint --ghost --hair --pos --neg`. Typography classes: `font-display` (large numbers/headlines), `font-mono text-[8px..10px] tracking-[0.1em..0.18em] uppercase` (labels), `font-serif italic` (prose/empty states). Copy the idiom from `dashboard/app/admin/page.tsx` and `app/admin/clients/[id]/layout.tsx`. **Do NOT use `var(--surface)`** (it appears in old ApprovalCard.tsx but is not defined — use `var(--ink-2)` for code-block backgrounds).
3. **Color discipline (spec):** green/red (`--pos`/`--neg`) = metric direction ONLY. Amber `#d4a017` = needs-you (waiting badges). Grey (`--mute`/`--faint`) = neutral/ops.
4. **Data access:** server components call `createAdminClient()` from `@/lib/supabase/admin` directly. API routes authenticate like `dashboard/app/api/admin/stability/[clientId]/route.ts` (session user → `client_users.role === "admin"` → then `createAdminClient()`).
5. **Tests:** dashboard: `cd dashboard && npm test` (vitest, alias `@` → dashboard root, tests in `dashboard/__tests__/`). Python: `cd agents && .venv/bin/python -m pytest tests/ -q`.
6. **Commits:** commit at the end of every task (steps say when). Work happens on branch `frontend-overhaul`.
7. **Rates** are stored 0–1 floats. Display via `formatRate()` / `formatDelta()` from `@/lib/utils` (deltas render as percentage points, e.g. `+6pp`).
8. **Decision (IA):** the app keeps the existing top nav (not a literal sidebar): BOARD (`/admin`) · CLIENTS (`/admin/clients`) · APPROVALS (`/admin/approvals`). Reports stay untouched and reachable via a REPORTS tab appended to the client drilldown tabs (routes `admin/clients/[id]/reports/*` unchanged).
9. **Decision (run identity):** a "run" in the RUNS tab / run detail = a `pipeline_runs` row. `tracker_runs` and `improvement_runs` link to it via a new `thread_id` column (Task 1). Rows created before migration 010 have `thread_id = null`; every join must tolerate that (show "—" / omit tiles).

## File structure

**Backend (modify):** `supabase/migrations/010_thread_links.sql` (new), `agents/src/graph/nodes.py`, `agents/src/graph/state.py`, `agents/src/improvement/pipeline.py`, `agents/src/improvement/card_generator.py`, `agents/server.py`. **Delete:** `agents/src/improvement/reddit_scout.py`, `agents/tests/test_reddit_scout.py`, `agents/tests/test_reddit_scout_v2.py`.

**Dashboard lib (new):** `lib/derive.ts` (delta/competitor/rank/movers/badge/citation-rate derivations), `lib/mention.ts` (sentence extraction), `lib/schedules.ts` (FastAPI schedules fetch), `lib/improvement-types.ts` (types for improvement tables).

**Dashboard pages:** `/admin` → Visibility Board (rewrite); `/admin/clients` → old clients table (new location); drilldown gets `overview/ queries/ pages/ cards/` tab routes, rewritten `runs/` + `runs/[runId]`; `/admin/approvals` rewritten. **Delete:** the whole `audit/` subtree, `export/[runId]`, `TriggerAuditButton.tsx`, old `ApprovalCard.tsx`/`ApprovalsClient.tsx`, `RunDetail.tsx`, `RunRow.tsx`.

**Components (new):** `components/board/BoardRow.tsx`, `components/charts/TimelineChart.tsx`, `components/admin/HeatTable.tsx`, `components/admin/QueryExpansion.tsx`, `components/pages-tab/PagesTable.tsx`, `components/approvals/` (Inbox, RunGroup, cards: AutomatedCard, BriefCard, CommunityCheckCard, CrawlabilityCard), `components/runs/RunRail.tsx`.

---

### Task 1: Migration 010 — link tracker/improvement runs to pipeline threads

**Files:**
- Create: `supabase/migrations/010_thread_links.sql`
- Modify: `agents/src/graph/nodes.py` (~line 42, tracker_runs insert), `agents/src/improvement/pipeline.py` (~line 46, improvement_runs insert)
- Test: `agents/tests/test_graph_nodes.py`, `agents/tests/test_improvement_pipeline.py`

- [ ] **Step 1: Write the migration**

```sql
-- 010_thread_links.sql
-- Link tracker_runs and improvement_runs to their pipeline_runs thread so the
-- approvals inbox can resume the correct thread and run detail can join all
-- three tables. Old rows keep null thread_id; UI joins must tolerate that.

alter table public.tracker_runs
  add column if not exists thread_id text;

alter table public.improvement_runs
  add column if not exists thread_id text;

create index if not exists idx_tracker_runs_thread_id
  on public.tracker_runs(thread_id);

create index if not exists idx_improvement_runs_thread_id
  on public.improvement_runs(thread_id);
```

- [ ] **Step 2: Write failing tests**

Read the existing mock-supabase pattern in `agents/tests/test_graph_nodes.py` and `agents/tests/test_improvement_pipeline.py` first, then add (adapting mock names to what's actually there):

```python
def test_tracker_run_insert_includes_thread_id(...existing fixture args...):
    # invoke run_tracker_node with state containing "thread_id": "client-20260707-000000"
    # capture the dict passed to sb.table("tracker_runs").insert(...)
    assert inserted["thread_id"] == "client-20260707-000000"

def test_improvement_run_insert_includes_thread_id(...):
    # invoke run_improvement_pipeline with state["thread_id"] set
    assert improvement_insert["thread_id"] == "client-20260707-000000"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd agents && .venv/bin/python -m pytest tests/test_graph_nodes.py tests/test_improvement_pipeline.py -q`
Expected: the two new tests FAIL (KeyError `thread_id`).

- [ ] **Step 4: Implement**

In `nodes.py` `run_tracker_node`, add to the `tracker_runs` insert dict:

```python
            "thread_id": state.get("thread_id"),
```

In `pipeline.py` `run_improvement_pipeline`, change the insert to:

```python
    run_resp = sb.table("improvement_runs").insert({
        "client_id": client_id,
        "status": "running",
        "thread_id": state.get("thread_id"),
    }).execute()
```

- [ ] **Step 5: Run the full Python suite**

Run: `cd agents && .venv/bin/python -m pytest tests/ -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add supabase/migrations/010_thread_links.sql agents/src/graph/nodes.py agents/src/improvement/pipeline.py agents/tests/
git commit -m "feat: link tracker/improvement runs to pipeline thread_id (migration 010)"
```

**Deploy note (record, don't run):** migration 010 must be pasted into the Supabase SQL editor before the new UI ships.

---

### Task 2: Community-check cards replace the Reddit scout (D5)

**Files:**
- Delete: `agents/src/improvement/reddit_scout.py`, `agents/tests/test_reddit_scout.py`, `agents/tests/test_reddit_scout_v2.py`
- Modify: `agents/src/improvement/card_generator.py` (replace `build_reddit_card`), `agents/src/improvement/pipeline.py` (Step 5b + card loop + return dict), `agents/src/graph/state.py` (drop `reddit_scout_data`), `agents/src/graph/nodes.py` (error-fallback dict), `agents/server.py` (two invoke dicts)
- Test: Create `agents/tests/test_community_check.py`; update `agents/tests/test_improvement_pipeline.py`

Scope note: only the improvement-pipeline scout dies here. Legacy `agents/src/reddit_scout.py` / `agents/scout.py` (old CLI era) are untouched.

- [ ] **Step 1: Write failing tests** in `agents/tests/test_community_check.py`:

```python
from src.improvement.card_generator import build_community_check_card


def _gap(**over):
    gap = {
        "query": "best daycare software",
        "query_id": "q-1",
        "competitive_gap": 0.4,
        "top_competitor": "KinderCare",
        "client_mention_rate": 0.2,
        "competitor_mention_rate": 0.6,
    }
    gap.update(over)
    return gap


def test_card_shape():
    card = build_community_check_card(_gap())
    assert card["action_type"] == "community_check"
    assert card["track"] == "manual"
    assert card["priority"] == 2
    assert card["query_id"] == "q-1"
    assert card["status"] == "pending"
    assert card["cms_action"] == "none"
    assert card["page_url"] is None


def test_search_links_are_prebuilt():
    card = build_community_check_card(_gap())
    links = card["reddit_data"]["search_links"]
    assert links["reddit"] == "https://www.reddit.com/search/?q=best+daycare+software"
    assert "site%3Areddit.com+best+daycare+software" in links["google"]


def test_issue_names_competitor_and_gap():
    card = build_community_check_card(_gap())
    assert "KinderCare" in card["issue"]
    assert "40%" in card["issue"]


def test_issue_without_competitor():
    card = build_community_check_card(_gap(top_competitor=None, competitive_gap=0.0))
    assert "KinderCare" not in card["issue"]


def test_guidance_and_thread_url_field():
    card = build_community_check_card(_gap())
    assert card["reddit_data"]["thread_url"] is None
    assert "drip" in card["reddit_data"]["guidance"].lower() or "genuinely" in card["reddit_data"]["guidance"].lower()
```

- [ ] **Step 2: Run to verify failure**

Run: `cd agents && .venv/bin/python -m pytest tests/test_community_check.py -q`
Expected: ImportError (`build_community_check_card` not defined).

- [ ] **Step 3: Implement `build_community_check_card`** in `card_generator.py`, replacing `build_reddit_card` entirely:

```python
def build_community_check_card(gap: dict) -> dict:
    """Manual community-check card for a losing query (D5 — no automated
    Reddit data; humans do the searching and engagement)."""
    from urllib.parse import quote_plus

    query = gap["query"]
    top = gap.get("top_competitor")
    gap_value = gap.get("competitive_gap") or 0.0

    issue = f"Check community discussion for '{query}'"
    if top:
        issue += f" — {top} leads by {gap_value:.0%} on this query"

    return {
        "page_url": None,
        "query_id": gap.get("query_id"),
        "action_type": "community_check",
        "track": "manual",
        "priority": 2,
        "competitive_gap": gap_value,
        "issue": issue,
        "reddit_data": {
            "search_links": {
                "reddit": f"https://www.reddit.com/search/?q={quote_plus(query)}",
                "google": f"https://www.google.com/search?q={quote_plus('site:reddit.com ' + query)}",
            },
            "guidance": (
                "Search for recent threads asking this question. Note whether "
                "competitors are recommended and whether we appear. Engage only "
                "where a genuinely helpful answer fits — drip pace, never mass "
                "promotional commenting."
            ),
            "thread_url": None,
        },
        "status": "pending",
        "cms_action": "none",
    }
```

- [ ] **Step 4: Rewire `pipeline.py`**
  - Remove `from src.improvement.reddit_scout import run_reddit_scout` and remove `build_reddit_card` from the card_generator import (add `build_community_check_card`).
  - Replace Step 5b (lines ~136-138) with just:

```python
        gap_queries = [g for g in gap_results if g["competitive_gap"] > 0]
```

  - Replace the reddit card loop (lines ~258-272) with:

```python
        for gap in gap_queries:
            card = build_community_check_card(gap)
            card["run_id"] = run_id
            card["client_id"] = client_id
            card["pillar"] = "community_check"
            card["score"] = 0
            card["before_text"] = ""
            card["after_text"] = ""
            card["code_block"] = ""
            card["validation_passed"] = True
            all_cards.append(card)
```

  - Remove `"reddit_scout_data": reddit_data,` from the success return dict.

- [ ] **Step 5: Purge the state key everywhere**
  - `agents/src/graph/state.py`: delete the `reddit_scout_data: list[dict]` line.
  - `agents/src/graph/nodes.py`: delete `"reddit_scout_data": [],` from the improvement-node error fallback.
  - `agents/server.py`: delete `"reddit_scout_data": [],` from BOTH invoke dicts (in `trigger_scheduled_run` and `_run_graph_background`).
  - Delete `agents/src/improvement/reddit_scout.py`, `agents/tests/test_reddit_scout.py`, `agents/tests/test_reddit_scout_v2.py`.
  - `grep -rn "reddit_scout\|build_reddit_card" agents/src agents/tests agents/server.py` — fix any remaining references (test_improvement_pipeline.py mocks likely mention it; update those to expect community_check cards instead).

- [ ] **Step 6: Run the full Python suite**

Run: `cd agents && .venv/bin/python -m pytest tests/ -q`
Expected: all pass, reddit tests gone, community tests green.

- [ ] **Step 7: Commit**

```bash
git add -A agents/
git commit -m "feat: replace dead Reddit scout with manual community-check cards (D5)"
```

---

### Task 3: Persist preview_url in run_implementation_node

**Files:**
- Modify: `agents/src/graph/nodes.py:170-219` (`run_implementation_node`)
- Test: `agents/tests/test_graph_nodes.py`

- [ ] **Step 1: Write failing tests** (adapt to the file's existing mock pattern):

```python
def test_implementation_persists_pr_url(...):
    # route_card mocked to return {"status": "implemented", "pr_url": "https://github.com/x/y/pull/1"}
    # assert the action_cards update payload contains preview_url == that URL

def test_implementation_persists_webflow_preview_url(...):
    # route_card returns {"status": "implemented", "preview_url": "https://site.webflow.io/page"}
    # assert update payload preview_url == that URL

def test_no_preview_url_key_when_absent(...):
    # route_card returns {"status": "implemented"} → update payload has NO preview_url key
```

- [ ] **Step 2: Run to verify failure**

Run: `cd agents && .venv/bin/python -m pytest tests/test_graph_nodes.py -q` — new tests FAIL.

- [ ] **Step 3: Implement.** In `run_implementation_node`, right after `update_fields = {"status": new_status}`:

```python
            preview = result.get("preview_url") or result.get("pr_url")
            if preview:
                update_fields["preview_url"] = preview
```

- [ ] **Step 4: Run full suite** — `cd agents && .venv/bin/python -m pytest tests/ -q` — all pass.

- [ ] **Step 5: Commit**

```bash
git add agents/src/graph/nodes.py agents/tests/test_graph_nodes.py
git commit -m "feat: persist PR/staging preview_url on implemented cards"
```

---

### Task 4: Approve APIs accept rejected ids (FastAPI + Next route)

**Files:**
- Modify: `agents/server.py:181-184, 263-290`, `dashboard/app/api/admin/approve/route.ts`
- Test: `agents/tests/test_server.py`

- [ ] **Step 1: Write failing test** in `agents/tests/test_server.py` (match its existing TestClient/mocking style):

```python
def test_approve_marks_rejected_cards(...):
    # POST /api/approve with {"thread_id": "t", "approved_card_ids": ["a"], "rejected_card_ids": ["r1", "r2"]}
    # assert action_cards update {"status": "rejected"} was issued for r1 and r2
    # and graph resume was called with ["a"] only

def test_approve_rejected_ids_default_empty(...):
    # POST without rejected_card_ids still works (backward compatible)
```

- [ ] **Step 2: Run to verify failure** — `cd agents && .venv/bin/python -m pytest tests/test_server.py -q`.

- [ ] **Step 3: Implement in `agents/server.py`.** Model:

```python
class ApproveRequest(BaseModel):
    thread_id: str
    approved_card_ids: list[str]
    rejected_card_ids: list[str] = []
```

In `approve_cards`, after `sb = _get_supabase()` and before the pipeline_runs status update:

```python
    for card_id in req.rejected_card_ids:
        sb.table("action_cards").update({"status": "rejected"}).eq("id", card_id).execute()
```

- [ ] **Step 4: Update the Next.js route** `dashboard/app/api/admin/approve/route.ts`:

```ts
  const { threadId, approvedCardIds, rejectedCardIds } = await req.json();
  const approved: string[] = approvedCardIds || [];
  const rejected: string[] = rejectedCardIds || [];

  for (const cardId of approved) {
    await admin.from("action_cards").update({ status: "approved" }).eq("id", cardId);
  }
  for (const cardId of rejected) {
    await admin.from("action_cards").update({ status: "rejected" }).eq("id", cardId);
  }
```

and forward both in the LangGraph body:

```ts
        body: JSON.stringify({ thread_id: threadId, approved_card_ids: approved, rejected_card_ids: rejected }),
```

- [ ] **Step 5: Run suites** — `cd agents && .venv/bin/python -m pytest tests/ -q` and `cd dashboard && npx tsc --noEmit`. All pass.

- [ ] **Step 6: Commit**

```bash
git add agents/server.py agents/tests/test_server.py dashboard/app/api/admin/approve/route.ts
git commit -m "feat: approve flow records rejected card ids"
```

---

### Task 5: Derivation helpers — `dashboard/lib/derive.ts`

**Files:**
- Create: `dashboard/lib/derive.ts`
- Test: `dashboard/__tests__/derive.test.ts`

Pure functions only — no Supabase imports. These are the single source of truth for board/drilldown numbers.

- [ ] **Step 1: Write the failing tests** in `dashboard/__tests__/derive.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import {
  topCompetitor,
  rankAndGap,
  engineAverageByQuery,
  biggestMovers,
  opsBadge,
  aggregateCitationRate,
  measuringCount,
} from "@/lib/derive";

const scores = {
  KinderCare: { mention_rate: 0.61 },
  Brightwheel: { mention_rate: 0.3 },
  Procare: { mention_rate: 0.42 },
};

describe("topCompetitor", () => {
  it("picks the highest aggregate rate", () => {
    expect(topCompetitor(scores)).toEqual({ name: "KinderCare", rate: 0.61 });
  });
  it("returns null when empty", () => {
    expect(topCompetitor({})).toBeNull();
    expect(topCompetitor(null)).toBeNull();
  });
});

describe("rankAndGap", () => {
  it("ranks client among competitors (1 = leader)", () => {
    // client 0.42 vs 0.61/0.3/0.42 → one strictly higher → rank 2 of 4
    expect(rankAndGap(0.42, scores)).toEqual({ rank: 2, total: 4, gapToLeader: 0.19 });
  });
  it("client leading → rank 1, zero gap", () => {
    expect(rankAndGap(0.9, scores)).toEqual({ rank: 1, total: 4, gapToLeader: 0 });
  });
  it("no competitors → rank 1 of 1", () => {
    expect(rankAndGap(0.5, {})).toEqual({ rank: 1, total: 1, gapToLeader: 0 });
  });
});

const ps = (query: string, llm: string, mention_rate: number, citation_rate = 0) =>
  ({ query, llm, mention_rate, citation_rate });

describe("engineAverageByQuery", () => {
  it("averages across engines per query", () => {
    const m = engineAverageByQuery([ps("q1", "chatgpt", 0.8, 0.5), ps("q1", "claude", 0.4, 0.25), ps("q2", "chatgpt", 0.2)]);
    expect(m.get("q1")).toEqual({ mention_rate: 0.6, citation_rate: 0.375 });
    expect(m.get("q2")).toEqual({ mention_rate: 0.2, citation_rate: 0 });
  });
});

describe("biggestMovers", () => {
  it("returns the 2 largest absolute engine-averaged changes with before/after", () => {
    const latest = [ps("up", "chatgpt", 0.9), ps("down", "chatgpt", 0.1), ps("flat", "chatgpt", 0.5)];
    const previous = [ps("up", "chatgpt", 0.4), ps("down", "chatgpt", 0.7), ps("flat", "chatgpt", 0.5)];
    const movers = biggestMovers(latest, previous);
    expect(movers).toHaveLength(2);
    expect(movers[0]).toEqual({ query: "down", before: 0.7, after: 0.1, change: -0.6 });
    expect(movers[1]).toEqual({ query: "up", before: 0.4, after: 0.9, change: 0.5 });
  });
  it("treats queries missing from previous as before=0", () => {
    const movers = biggestMovers([ps("new", "chatgpt", 0.3)], []);
    expect(movers[0]).toEqual({ query: "new", before: 0, after: 0.3, change: 0.3 });
  });
  it("empty when no previous run", () => {
    expect(biggestMovers([ps("q", "chatgpt", 0.3)], null)).toEqual([]);
  });
});

describe("opsBadge", () => {
  it("error wins over everything", () => {
    expect(opsBadge({ latestPipelineStatus: "error", pendingCount: 3, oldestPendingDays: 2, measuring: 1 }).kind).toBe("error");
  });
  it("waiting with age beats measuring", () => {
    const b = opsBadge({ latestPipelineStatus: "completed", pendingCount: 3, oldestPendingDays: 2, measuring: 1 });
    expect(b.kind).toBe("waiting");
    expect(b.label).toBe("3 CARDS · 2D");
  });
  it("measuring when implemented cards await next run", () => {
    const b = opsBadge({ latestPipelineStatus: "completed", pendingCount: 0, oldestPendingDays: null, measuring: 4 });
    expect(b.kind).toBe("measuring");
  });
  it("healthy otherwise", () => {
    expect(opsBadge({ latestPipelineStatus: "completed", pendingCount: 0, oldestPendingDays: null, measuring: 0 }).kind).toBe("healthy");
  });
});

describe("aggregateCitationRate", () => {
  it("averages citation_rate over queries with mentions only (conditional on mention)", () => {
    const m = aggregateCitationRate([ps("q1", "chatgpt", 0.6, 0.5), ps("q2", "chatgpt", 0, 0), ps("q3", "chatgpt", 0.4, 0.25)]);
    expect(m).toBeCloseTo(0.375);
  });
  it("null when nothing mentioned", () => {
    expect(aggregateCitationRate([ps("q", "chatgpt", 0, 0)])).toBeNull();
  });
});

describe("measuringCount", () => {
  it("counts implemented cards created after the latest tracker run", () => {
    const cards = [
      { status: "implemented", created_at: "2026-07-05T10:00:00Z" },
      { status: "implemented", created_at: "2026-07-01T10:00:00Z" },
      { status: "pending", created_at: "2026-07-05T10:00:00Z" },
    ];
    expect(measuringCount(cards, "2026-07-03T00:00:00Z")).toBe(1);
  });
  it("0 with no tracker run", () => {
    expect(measuringCount([{ status: "implemented", created_at: "2026-07-05T10:00:00Z" }], null)).toBe(0);
  });
});
```

- [ ] **Step 2: Run to verify failure** — `cd dashboard && npm test` → derive.test.ts fails (module missing).

- [ ] **Step 3: Implement `dashboard/lib/derive.ts`:**

```ts
export interface CompetitorPick { name: string; rate: number }
export interface RankResult { rank: number; total: number; gapToLeader: number }
export interface QueryMove { query: string; before: number; after: number; change: number }
export interface EngineAvg { mention_rate: number; citation_rate: number }
export type OpsBadgeKind = "error" | "waiting" | "measuring" | "healthy";
export interface OpsBadgeResult { kind: OpsBadgeKind; label: string }

type CompetitorScores = Record<string, { mention_rate: number }> | null | undefined;
interface ScoreRow { query: string; llm: string; mention_rate: number; citation_rate: number }

export function topCompetitor(scores: CompetitorScores): CompetitorPick | null {
  const entries = Object.entries(scores ?? {});
  if (entries.length === 0) return null;
  const [name, s] = entries.reduce((a, b) => (b[1].mention_rate > a[1].mention_rate ? b : a));
  return { name, rate: s.mention_rate };
}

export function rankAndGap(clientRate: number, scores: CompetitorScores): RankResult {
  const rates = Object.values(scores ?? {}).map((s) => s.mention_rate);
  const rank = 1 + rates.filter((r) => r > clientRate).length;
  const maxRate = rates.length ? Math.max(...rates) : 0;
  const gapToLeader = Math.round(Math.max(0, maxRate - clientRate) * 10000) / 10000;
  return { rank, total: rates.length + 1, gapToLeader };
}

export function engineAverageByQuery(rows: ScoreRow[]): Map<string, EngineAvg> {
  const grouped = new Map<string, ScoreRow[]>();
  for (const r of rows) {
    const list = grouped.get(r.query) ?? [];
    list.push(r);
    grouped.set(r.query, list);
  }
  const out = new Map<string, EngineAvg>();
  for (const [query, list] of grouped) {
    out.set(query, {
      mention_rate: list.reduce((s, x) => s + x.mention_rate, 0) / list.length,
      citation_rate: list.reduce((s, x) => s + x.citation_rate, 0) / list.length,
    });
  }
  return out;
}

export function biggestMovers(latest: ScoreRow[], previous: ScoreRow[] | null, n = 2): QueryMove[] {
  if (!previous) return [];
  const latestAvg = engineAverageByQuery(latest);
  const prevAvg = engineAverageByQuery(previous);
  const moves: QueryMove[] = [];
  for (const [query, cur] of latestAvg) {
    const before = prevAvg.get(query)?.mention_rate ?? 0;
    const change = Math.round((cur.mention_rate - before) * 10000) / 10000;
    moves.push({ query, before, after: cur.mention_rate, change });
  }
  moves.sort((a, b) => Math.abs(b.change) - Math.abs(a.change));
  return moves.slice(0, n).filter((m) => m.change !== 0);
}

export function opsBadge(input: {
  latestPipelineStatus: string | null;
  pendingCount: number;
  oldestPendingDays: number | null;
  measuring: number;
}): OpsBadgeResult {
  if (input.latestPipelineStatus === "error") return { kind: "error", label: "RUN ERROR" };
  if (input.pendingCount > 0) {
    const age = input.oldestPendingDays != null ? ` · ${input.oldestPendingDays}D` : "";
    return { kind: "waiting", label: `${input.pendingCount} CARDS${age}` };
  }
  if (input.measuring > 0) return { kind: "measuring", label: "MEASURING" };
  return { kind: "healthy", label: "HEALTHY" };
}

export function aggregateCitationRate(rows: ScoreRow[]): number | null {
  const mentioned = rows.filter((r) => r.mention_rate > 0);
  if (mentioned.length === 0) return null;
  return mentioned.reduce((s, r) => s + r.citation_rate, 0) / mentioned.length;
}

export function measuringCount(
  cards: { status: string; created_at: string }[],
  latestTrackerRanAt: string | null
): number {
  if (!latestTrackerRanAt) return 0;
  const cutoff = new Date(latestTrackerRanAt).getTime();
  return cards.filter(
    (c) => c.status === "implemented" && new Date(c.created_at).getTime() > cutoff
  ).length;
}
```

- [ ] **Step 4: Run tests** — `cd dashboard && npm test` — all pass.

- [ ] **Step 5: Commit**

```bash
git add dashboard/lib/derive.ts dashboard/__tests__/derive.test.ts
git commit -m "feat: board/drilldown derivation helpers"
```

---

### Task 6: Mention-sentence extraction — `dashboard/lib/mention.ts`

**Files:**
- Create: `dashboard/lib/mention.ts`
- Test: `dashboard/__tests__/mention.test.ts`

- [ ] **Step 1: Failing tests:**

```ts
import { describe, it, expect } from "vitest";
import { extractMentionSentence, pickRepresentative } from "@/lib/mention";

describe("extractMentionSentence", () => {
  const text =
    "There are many options. Brightwheel is a popular choice for daycare management! Some prefer others. What about pricing?";
  it("finds the sentence containing a brand variation", () => {
    const r = extractMentionSentence(text, ["Brightwheel"]);
    expect(r).toEqual({
      sentence: "Brightwheel is a popular choice for daycare management!",
      brand: "Brightwheel",
    });
  });
  it("is case-insensitive and tries variations in order", () => {
    const r = extractMentionSentence("we like BRIGHT WHEEL a lot.", ["Brightwheel", "bright wheel"]);
    expect(r?.brand).toBe("bright wheel");
  });
  it("null when absent or empty", () => {
    expect(extractMentionSentence("Nothing here.", ["Brightwheel"])).toBeNull();
    expect(extractMentionSentence("", ["Brightwheel"])).toBeNull();
    expect(extractMentionSentence("text", [])).toBeNull();
  });
  it("handles text without terminal punctuation", () => {
    const r = extractMentionSentence("brands: brightwheel, procare", ["Brightwheel"]);
    expect(r?.sentence).toBe("brands: brightwheel, procare");
  });
});

describe("pickRepresentative", () => {
  const rows = [
    { brand_mentioned: false, queried_at: "2026-07-05T10:00:00Z" },
    { brand_mentioned: true, queried_at: "2026-07-03T10:00:00Z" },
    { brand_mentioned: true, queried_at: "2026-07-04T10:00:00Z" },
  ];
  it("most recent mentioned wins", () => {
    expect(pickRepresentative(rows)?.queried_at).toBe("2026-07-04T10:00:00Z");
  });
  it("falls back to most recent overall", () => {
    const none = rows.map((r) => ({ ...r, brand_mentioned: false }));
    expect(pickRepresentative(none)?.queried_at).toBe("2026-07-05T10:00:00Z");
  });
  it("null on empty", () => {
    expect(pickRepresentative([])).toBeNull();
  });
});
```

- [ ] **Step 2: Run to verify failure** — `cd dashboard && npm test`.

- [ ] **Step 3: Implement `dashboard/lib/mention.ts`:**

```ts
export interface MentionSentence { sentence: string; brand: string }

export function extractMentionSentence(
  responseText: string,
  brandVariations: string[]
): MentionSentence | null {
  if (!responseText || brandVariations.length === 0) return null;
  const sentences = responseText
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
  for (const sentence of sentences) {
    const lower = sentence.toLowerCase();
    for (const brand of brandVariations) {
      if (brand && lower.includes(brand.toLowerCase())) {
        return { sentence, brand };
      }
    }
  }
  return null;
}

export function pickRepresentative<T extends { brand_mentioned: boolean; queried_at: string }>(
  rows: T[]
): T | null {
  if (rows.length === 0) return null;
  const byRecency = [...rows].sort(
    (a, b) => new Date(b.queried_at).getTime() - new Date(a.queried_at).getTime()
  );
  return byRecency.find((r) => r.brand_mentioned) ?? byRecency[0];
}
```

- [ ] **Step 4: Run tests** — all pass. **Step 5: Commit**

```bash
git add dashboard/lib/mention.ts dashboard/__tests__/mention.test.ts
git commit -m "feat: mention-sentence extraction + representative response pick"
```

---

### Task 7: Schedules helper + improvement-table types

**Files:**
- Create: `dashboard/lib/schedules.ts`, `dashboard/lib/improvement-types.ts`

No unit tests (thin fetch wrapper + type declarations); verified by typecheck and later usage.

- [ ] **Step 1: `dashboard/lib/schedules.ts`** — server-only helper mirroring the proxy pattern in `app/api/runs/reload-schedules/route.ts`:

```ts
export interface Schedule {
  client_id: string;
  client_name: string;
  cycle_frequency: string;
  cycle_day: string;
  next_run: string | null;
  last_run_status: string | null;
  last_run_at: string | null;
}

/** Fetch schedules from the FastAPI agent server. Returns [] when the agent
 * API is unconfigured or unreachable — callers render nothing in that case. */
export async function fetchSchedules(): Promise<Schedule[]> {
  const api = process.env.LANGGRAPH_API_URL;
  const key = process.env.LANGGRAPH_API_KEY;
  if (!api || !key) return [];
  try {
    const res = await fetch(`${api}/api/schedules`, {
      headers: { Authorization: `Bearer ${key}` },
      cache: "no-store",
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.schedules ?? [];
  } catch {
    return [];
  }
}
```

- [ ] **Step 2: `dashboard/lib/improvement-types.ts`** — types matching migration 008/003 exactly:

```ts
export interface PipelineRun {
  id: string;
  client_id: string;
  thread_id: string;
  run_type: string;
  status: "running" | "awaiting_approval" | "implementing" | "completed" | "error";
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface CrawlCheck { status: "pass" | "fail" | "warn" | string; detail?: string }

export interface CrawlabilityReport {
  has_critical_blocker?: boolean;
  robots_txt?: CrawlCheck;
  js_rendering?: CrawlCheck;
  cdn_blocks?: CrawlCheck;
  [key: string]: unknown;
}

export interface ImprovementRun {
  id: string;
  client_id: string;
  thread_id: string | null;
  ran_at: string;
  crawlability_report: CrawlabilityReport;
  pages_inventoried: number;
  queries_matched: number;
  content_gaps_found: number;
  competitive_gaps_found: number;
  cards_generated: number;
  status: "running" | "completed" | "error";
  error_message: string | null;
  completed_at: string | null;
}

export interface PageInventoryRow {
  id: string;
  run_id: string;
  url: string;
  title: string;
  h1: string;
  first_paragraph: string;
  schema_types: string[];
  word_count: number;
  last_modified: string | null;
  outbound_link_count: number;
  has_faq_schema: boolean;
  has_comparison_table: boolean;
}

export interface QueryPageMatch {
  id: string;
  run_id: string;
  query_id: string;
  query_text: string;
  match_type: "matched" | "weak" | "content_gap";
  matched_page_url: string | null;
  similarity_score: number;
  bucket: string | null;
}

export interface CheckResult { score: number; detail?: string; [key: string]: unknown }

export interface SonnetQuality {
  specificity: number;
  completeness: number;
  answer_directness: number;
  summary: string;
}

export interface PageCitationScore {
  id: string;
  run_id: string;
  page_url: string;
  structural_score: number;
  check_results: Record<string, CheckResult>;
  sonnet_quality: SonnetQuality;
  schema_status: "missing" | "broken" | "valid_incomplete" | "valid_complete";
  schema_errors: string[];
}

export interface ActionCard {
  id: string;
  run_id: string;
  client_id: string | null;
  query_id: string | null;
  page_url: string | null;
  action_type: string;
  track: "automated" | "manual";
  priority: number;
  competitive_gap: number | null;
  structural_score: number | null;
  issue: string;
  before_text: string;
  after_text: string;
  code_block: string;
  status: "pending" | "approved" | "rejected" | "implemented";
  cms_action: string;
  auto_approved: boolean;
  verification: { verified: boolean; checks?: Record<string, unknown>; error?: string } | null;
  brief: {
    target_query: string;
    competitive_landscape: string;
    recommended_title: string;
    recommended_h1: string;
    key_sections: string[];
    facts_to_include: string[];
    schema_type: string;
    internal_link_targets: string[];
    word_count_target: number;
  } | null;
  reddit_data: {
    search_links?: { reddit: string; google: string };
    guidance?: string;
    thread_url?: string | null;
  } | null;
  preview_url: string | null;
  created_at: string;
}
```

- [ ] **Step 3: Typecheck** — `cd dashboard && npx tsc --noEmit` — clean.

- [ ] **Step 4: Commit**

```bash
git add dashboard/lib/schedules.ts dashboard/lib/improvement-types.ts
git commit -m "feat: schedules fetch helper + improvement pipeline types"
```

---

### Task 8: Component-test infrastructure (jsdom + testing-library)

**Files:**
- Modify: `dashboard/package.json` (devDeps), `dashboard/vitest.config.ts`
- Test: `dashboard/__tests__/components/smoke.test.tsx`

- [ ] **Step 1: Install**

Run: `cd dashboard && npm install -D jsdom @testing-library/react`

- [ ] **Step 2: Configure.** Replace `dashboard/vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "node",
    environmentMatchGlobs: [["__tests__/components/**", "jsdom"]],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
});
```

Note: if vitest 4 rejects `environmentMatchGlobs` (it was deprecated), instead keep `environment: "node"` and put `// @vitest-environment jsdom` as the first line of every file in `__tests__/components/` — check `npx vitest --version` output/error and pick whichever works; document the choice in the test file.

- [ ] **Step 3: Smoke test** `dashboard/__tests__/components/smoke.test.tsx`:

```tsx
// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

describe("component test infra", () => {
  it("renders JSX into jsdom", () => {
    render(<div data-testid="ok">hello</div>);
    expect(screen.getByTestId("ok").textContent).toBe("hello");
  });
});
```

- [ ] **Step 4: Run** — `cd dashboard && npm test` — all pass (existing node-env tests unaffected).

- [ ] **Step 5: Commit**

```bash
git add dashboard/package.json dashboard/package-lock.json dashboard/vitest.config.ts dashboard/__tests__/components/smoke.test.tsx
git commit -m "chore: jsdom + testing-library for component tests"
```

---

### Task 9: IA restructure — nav, clients list at /admin/clients, drilldown shell

**Files:**
- Modify: `dashboard/components/admin/NavLinks.tsx`, `dashboard/app/admin/clients/[id]/layout.tsx`, `dashboard/app/admin/clients/[id]/page.tsx`
- Create: `dashboard/app/admin/clients/page.tsx` (receives the old `/admin` clients table), placeholder tab pages `overview/page.tsx`, `queries/page.tsx`, `pages/page.tsx`, `cards/page.tsx` under `dashboard/app/admin/clients/[id]/`
- Note: `/admin` itself is rewritten in Task 10; in THIS task, move its current content to `/admin/clients` verbatim and leave `/admin` temporarily rendering the same moved component import — Task 10 replaces it.

- [ ] **Step 1: Nav.** In `NavLinks.tsx` replace the `links` array:

```ts
const links = [
  { label: "BOARD", href: "/admin", exact: true },
  { label: "CLIENTS", href: "/admin/clients", exact: false },
  { label: "APPROVALS", href: "/admin/approvals", exact: false },
];
```

and simplify `isActive` (drop the `/admin/clients` special case on BOARD):

```ts
const isActive = exact ? pathname === href : pathname.startsWith(href);
```

- [ ] **Step 2: Move the clients table.** Create `dashboard/app/admin/clients/page.tsx` with the exact current content of `dashboard/app/admin/page.tsx` (imports unchanged — they're absolute `@/` paths). Update the `<h1>` to stay "Clients". Then reduce `dashboard/app/admin/page.tsx` to re-export it temporarily:

```tsx
export { default } from "../clients/page";
```

(This file becomes the Visibility Board in Task 10.)

Also fix the back-link in `dashboard/app/admin/approvals/page.tsx` (and anywhere `href="/admin"` means "clients list"): `grep -rn '"/admin"' dashboard/app dashboard/components` and point client-list links at `/admin/clients` (`ClientRow` links to `/admin/clients/[id]/...` already — leave those).

- [ ] **Step 3: Drilldown tabs + default.** In `app/admin/clients/[id]/layout.tsx` replace the tabs array:

```ts
  const tabs = [
    { label: "OVERVIEW", href: `/admin/clients/${id}/overview` },
    { label: "QUERIES", href: `/admin/clients/${id}/queries` },
    { label: "PAGES", href: `/admin/clients/${id}/pages` },
    { label: "RUNS", href: `/admin/clients/${id}/runs` },
    { label: "CARDS", href: `/admin/clients/${id}/cards` },
    { label: "CONFIG", href: `/admin/clients/${id}/config` },
    { label: "REPORTS", href: `/admin/clients/${id}/reports` },
  ];
```

Change `app/admin/clients/[id]/page.tsx` redirect target from `/config` to `/overview`. Breadcrumb "CLIENTS" link → `/admin/clients`.

- [ ] **Step 4: Placeholder tab pages** so nav works before Tasks 11-14. Each new page (`overview/page.tsx`, `queries/page.tsx`, `pages/page.tsx`, `cards/page.tsx`):

```tsx
export default async function OverviewPage() {
  return (
    <p className="font-serif italic" style={{ color: "var(--mute)" }}>
      Coming in this overhaul.
    </p>
  );
}
```

(rename the function per tab: `QueriesPage`, `PagesTabPage`, `CardsPage`).

- [ ] **Step 5: Verify** — `cd dashboard && npx tsc --noEmit && npm run build`. Build passes; AUDIT tab is gone from tabs (audit routes still exist until Task 16 — fine).

- [ ] **Step 6: Commit**

```bash
git add -A dashboard/
git commit -m "feat: IA restructure — BOARD/CLIENTS/APPROVALS nav, drilldown tab shell"
```

---

### Task 10: Surface 1 — Visibility Board at /admin

**Files:**
- Rewrite: `dashboard/app/admin/page.tsx`
- Create: `dashboard/components/board/BoardRow.tsx`
- Reference: mockup `docs/superpowers/mockups/visibility-board-v2.html` (open it and mirror the hierarchy; style with theme vars)

Row grid: `[client+delta | head-to-head hero | biggest moves | sparkline+badge]`. Sorted worst-delta-first. Header rollup; footer next-runs.

- [ ] **Step 1: Server page.** Replace `dashboard/app/admin/page.tsx`:

```tsx
export const dynamic = "force-dynamic";

import { createAdminClient } from "@/lib/supabase/admin";
import { fetchSchedules } from "@/lib/schedules";
import { biggestMovers, measuringCount, opsBadge, rankAndGap, topCompetitor } from "@/lib/derive";
import { BoardRow, type BoardRowData } from "@/components/board/BoardRow";
import type { Client, TrackerRun, PromptScore } from "@/lib/types";

export default async function BoardPage() {
  const supabase = createAdminClient();
  const { data: clients } = await supabase
    .from("clients")
    .select("id, name, brand_name, created_at")
    .order("created_at", { ascending: true });
  const allClients = (clients as Pick<Client, "id" | "name" | "brand_name" | "created_at">[]) || [];

  const rows: BoardRowData[] = await Promise.all(
    allClients.map(async (client) => {
      const [{ data: runs }, { data: pipeline }, { data: pendingCards }, { data: implementedCards }] =
        await Promise.all([
          supabase
            .from("tracker_runs")
            .select("id, ran_at, aggregate_mention_rate, competitor_scores")
            .eq("client_id", client.id)
            .order("ran_at", { ascending: false })
            .limit(6),
          supabase
            .from("pipeline_runs")
            .select("status, started_at")
            .eq("client_id", client.id)
            .order("started_at", { ascending: false })
            .limit(1),
          supabase
            .from("action_cards")
            .select("id, created_at")
            .eq("client_id", client.id)
            .eq("status", "pending"),
          supabase
            .from("action_cards")
            .select("status, created_at")
            .eq("client_id", client.id)
            .eq("status", "implemented"),
        ]);

      const history = ((runs as Pick<TrackerRun, "id" | "ran_at" | "aggregate_mention_rate" | "competitor_scores">[]) || []);
      const latest = history[0] ?? null;
      const previous = history[1] ?? null;

      let movers: ReturnType<typeof biggestMovers> = [];
      if (latest && previous) {
        const { data: scores } = await supabase
          .from("prompt_scores")
          .select("run_id, query, llm, mention_rate, citation_rate")
          .in("run_id", [latest.id, previous.id]);
        const all = (scores as (Pick<PromptScore, "run_id" | "query" | "llm" | "mention_rate" | "citation_rate">)[]) || [];
        movers = biggestMovers(
          all.filter((s) => s.run_id === latest.id),
          all.filter((s) => s.run_id === previous.id)
        );
      }

      const pending = pendingCards || [];
      const oldestPendingDays = pending.length
        ? Math.floor((Date.now() - Math.min(...pending.map((c) => new Date(c.created_at).getTime()))) / 86400000)
        : null;

      const badge = opsBadge({
        latestPipelineStatus: pipeline?.[0]?.status ?? null,
        pendingCount: pending.length,
        oldestPendingDays,
        measuring: measuringCount(implementedCards || [], latest?.ran_at ?? null),
      });

      const rate = latest?.aggregate_mention_rate ?? null;
      const comp = latest ? topCompetitor(latest.competitor_scores) : null;
      const rank = latest && rate != null ? rankAndGap(rate, latest.competitor_scores) : null;

      return {
        clientId: client.id,
        name: client.brand_name || client.name,
        rate,
        delta: rate != null && previous ? rate - previous.aggregate_mention_rate : null,
        competitor: comp,
        rank,
        movers,
        sparkline: [...history].reverse().map((r) => r.aggregate_mention_rate),
        badge,
        pendingCount: pending.length,
        firstRunPending: !latest,
      };
    })
  );

  rows.sort((a, b) => (a.delta ?? 0) - (b.delta ?? 0));

  const improving = rows.filter((r) => (r.delta ?? 0) > 0.005).length;
  const declining = rows.filter((r) => (r.delta ?? 0) < -0.005).length;
  const flat = rows.length - improving - declining;
  const totalCards = rows.reduce((s, r) => s + r.pendingCount, 0);
  const errors = rows.filter((r) => r.badge.kind === "error").length;

  const schedules = await fetchSchedules();
  const upcoming = schedules
    .filter((s) => s.next_run)
    .sort((a, b) => (a.next_run! < b.next_run! ? -1 : 1))
    .slice(0, 3);

  return (
    <>
      {/* header: title + portfolio rollup */}
      {/* rollup line, font-mono labels: "N IMPROVING · N DECLINING · N FLAT — N CARDS TO REVIEW — N ERRORS" */}
      {/* one BoardRow per client */}
      {/* footer: NEXT RUNS — client_name day time, from `upcoming` */}
    </>
  );
}
```

Fill in the JSX per the mockup: `<h1 className="font-display text-[52px] font-light">Board</h1>`, rollup as a mono strip (improving in `--pos`, declining in `--neg`, cards-to-review in amber `#d4a017` when > 0, errors in `--neg`), rows in a bordered list, footer strip in `--faint` mono.

- [ ] **Step 2: BoardRow component** `dashboard/components/board/BoardRow.tsx` (server component — no interactivity beyond links):

```tsx
import Link from "next/link";
import { SparklineChart } from "@/components/charts/SparklineChart";
import { formatRate, formatDelta } from "@/lib/utils";
import type { CompetitorPick, RankResult, QueryMove, OpsBadgeResult } from "@/lib/derive";

export interface BoardRowData {
  clientId: string;
  name: string;
  rate: number | null;
  delta: number | null;
  competitor: CompetitorPick | null;
  rank: RankResult | null;
  movers: QueryMove[];
  sparkline: number[];
  badge: OpsBadgeResult;
  pendingCount: number;
  firstRunPending: boolean;
}

const BADGE_COLOR: Record<string, string> = {
  error: "var(--neg)",
  waiting: "#d4a017",
  measuring: "var(--mute)",
  healthy: "var(--faint)",
};

export function BoardRow({ row, nextRunLabel }: { row: BoardRowData; nextRunLabel?: string }) {
  // grid-cols: [1.2fr | 1.6fr | 1.4fr | 1fr], row links to /admin/clients/{id}/overview
  // Col 1: client name (font-serif 15px --white) + delta line (formatDelta, --pos/--neg/--mute)
  // Col 2 hero: rate huge (font-display ~34px) "VS" competitor rate + NAME (mono),
  //   two horizontal comparison bars (client width = rate*100%, competitor bar likewise;
  //   bar: h-[3px], client fill --white, competitor fill --faint, track --ghost),
  //   sub-line mono: `#${rank.rank} OF ${rank.total} · ${formatRate(gapToLeader)} TO LEADER`
  // Col 3: up to 2 movers: `"{query}" {before%}→{after%}` with arrow colored by direction
  // Col 4: SparklineChart values={row.sparkline} + badge chip (mono 8px, BADGE_COLOR[kind]);
  //   badge kind==="waiting" wraps the chip in <Link href="/admin/approvals">
  // firstRunPending → muted hero: "first run {nextRunLabel ?? "scheduled"}" in font-serif italic --mute
}
```

Write the full JSX following those comments and the mockup. Empty states: `rate == null` → hero shows "—" muted; `movers.length === 0` → "no movement yet" italic muted; sparkline `<2` points already handled by SparklineChart.

- [ ] **Step 3: Verify visually and by build** — `cd dashboard && npx tsc --noEmit && npm run build`. Then `npm run dev` and load `/admin` (with real env if available; otherwise confirm it renders the empty state without crashing — zero clients must not throw).

- [ ] **Step 4: Commit**

```bash
git add dashboard/app/admin/page.tsx dashboard/components/board/
git commit -m "feat: visibility board home (Surface 1)"
```

---

### Task 11: Drilldown header hero + crawlability banner + OVERVIEW tab

**Files:**
- Modify: `dashboard/app/admin/clients/[id]/layout.tsx` (hero + banner)
- Rewrite: `dashboard/app/admin/clients/[id]/overview/page.tsx`
- Create: `dashboard/components/charts/TimelineChart.tsx`
- Reference: mockup `client-drilldown-v4.html`

- [ ] **Step 1: Layout hero.** Extend the layout query + JSX. Fetch in parallel with the client row:

```tsx
  const [{ data: runs }, { data: improvementRuns }, { data: latestScores }] = await Promise.all([
    supabase
      .from("tracker_runs")
      .select("id, ran_at, aggregate_mention_rate, competitor_scores")
      .eq("client_id", id)
      .order("ran_at", { ascending: false })
      .limit(2),
    supabase
      .from("improvement_runs")
      .select("id, ran_at, crawlability_report")
      .eq("client_id", id)
      .order("ran_at", { ascending: false })
      .limit(1),
    // prompt_scores for the latest run only (citation rate):
    // fetch after runs resolve OR do a second await — simplest: second query below
  ]);
```

Then (second await) `prompt_scores` for `runs[0].id` → `aggregateCitationRate`. Compute `topCompetitor`, `rankAndGap`, delta. Render under the client name:

- Visibility % huge: `font-display text-[84px] font-light leading-none` + delta (`formatDelta`) + mono line `VS {COMP NAME} {rate}` + `#${rank} OF ${total}`.
- Second line, serif 13px `--mute`: `cited as source: {rate}% of mentions` plus the definition inline: *"mention = you appear in the answer; citation = the answer links your site"*. When `aggregateCitationRate` returns null: "no mentions yet this cycle".
- Next-run line: `fetchSchedules()`, find this client_id, mono 8px: `NEXT RUN {formatted next_run}` (omit when absent).
- No runs at all → keep the name header, show `first run pending` italic muted, skip hero numbers.

- [ ] **Step 2: Crawlability banner.** In the layout, when `improvementRuns[0]?.crawlability_report?.has_critical_blocker`:

```tsx
{blocker && (
  <div className="mt-4 px-5 py-3.5" style={{ background: "rgba(232,154,160,0.08)", border: "1px solid var(--neg)" }}>
    <div className="font-mono text-[9px] tracking-[0.14em] uppercase mb-1" style={{ color: "var(--neg)" }}>
      CRAWLABILITY BLOCKER — AI CRAWLERS CANNOT ACCESS THE SITE
    </div>
    <div className="font-serif text-[13px]" style={{ color: "var(--white)" }}>
      {failing.map((f) => `${f.name}: ${f.detail}`).join(" · ")}
    </div>
    <Link href="/admin/approvals" className="font-mono text-[9px] tracking-[0.1em] uppercase underline" style={{ color: "var(--neg)" }}>
      VIEW FIX-CRAWLABILITY CARD →
    </Link>
    <div className="font-mono text-[8px] mt-1" style={{ color: "var(--faint)" }}>
      DIAGNOSIS BELOW IS THE PRE-FIX BASELINE — VISIBILITY DATA REMAINS VALID
    </div>
  </div>
)}
```

where `failing` filters `["robots_txt", "cdn_blocks", "js_rendering"]` entries with `status === "fail"`, mapping `{ name, detail: report[name].detail ?? name }`. Import `CrawlabilityReport` from `@/lib/improvement-types`. Tabs stay live (no gating).

- [ ] **Step 3: TimelineChart** `dashboard/components/charts/TimelineChart.tsx` — SVG line chart, server-renderable (pure props, no hooks):

```tsx
interface TimelinePoint { label: string; value: number }
interface TimelineChartProps {
  series: TimelinePoint[];              // client visibility per cycle, oldest→newest
  competitor?: { name: string; series: (number | null)[] }; // dashed line, aligned to series
  height?: number;                       // default 180
}
```

Implementation: viewBox `0 0 640 {height}`, pad 24; x = even spacing, y = value scaled to [0,1] domain. Client line: `stroke="var(--white)" strokeWidth={1.5}`, dots `r=2.5 fill="var(--white)"`, **every point labeled** with `formatRate(value)` in `font-mono text-[8px] fill="var(--mute)"` above the dot. Competitor: `stroke="var(--faint)" strokeDasharray="4 3"`, name label at the last point. X labels (dates) under the axis in `--faint`. `<2` points → render "needs 2+ cycles" italic muted (same pattern as SparklineChart).

- [ ] **Step 4: Overview page.** Rewrite `overview/page.tsx`:

```tsx
import { createAdminClient } from "@/lib/supabase/admin";
import { TimelineChart } from "@/components/charts/TimelineChart";
import { topCompetitor } from "@/lib/derive";
import { formatRate } from "@/lib/utils";
import type { TrackerRun } from "@/lib/types";

export default async function OverviewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const supabase = createAdminClient();
  const [{ data: runs }, { data: client }] = await Promise.all([
    supabase
      .from("tracker_runs")
      .select("id, ran_at, aggregate_mention_rate, competitor_scores, gsc_clicks, gsc_impressions, gsc_ctr")
      .eq("client_id", id)
      .order("ran_at", { ascending: true }),
    supabase.from("clients").select("gsc_site_url").eq("id", id).single(),
  ]);
  const history = (runs as TrackerRun[]) || [];
  // timeline: series = history.map(r => ({ label: short date, value: r.aggregate_mention_rate }))
  // competitor line: pick topCompetitor from the LATEST run, then per run read
  //   competitor_scores[thatName]?.mention_rate ?? null
  // GSC panel: render only when client.gsc_site_url is non-empty —
  //   table of cycles: DATE | CLICKS | IMPRESSIONS | CTR (formatRate(gsc_ctr))
  // empty state: history.length === 0 → "No runs yet." italic muted
}
```

Write the full JSX (SECTION labels in mono uppercase: "VISIBILITY TIMELINE", "SEARCH CONSOLE").

- [ ] **Step 5: Verify** — `npx tsc --noEmit && npm run build`, load `/admin/clients/{id}/overview` in dev if env available.

- [ ] **Step 6: Commit**

```bash
git add -A dashboard/
git commit -m "feat: drilldown hero, crawlability banner, overview tab (Surface 2 pt.1)"
```

---

### Task 12: QUERIES tab — heat table + per-engine row expansion

**Files:**
- Rewrite: `dashboard/app/admin/clients/[id]/queries/page.tsx`
- Create: `dashboard/components/admin/HeatTable.tsx` (client), `dashboard/components/admin/QueryExpansion.tsx` (client), `dashboard/app/api/admin/query-detail/[clientId]/route.ts`
- Test: `dashboard/__tests__/components/heat-table.test.tsx`
- Reference: mockup `client-drilldown-v4.html` (query table section)

Row: query | mention rate per cycle (last ~6, color-scaled) | STABILITY | CITED % | PAGE (+similarity) | TOP COMPETITOR | WAITING. Expansion loads per-engine detail from the API route.

- [ ] **Step 1: Server page** assembles `HeatRow[]`:

```tsx
export interface HeatCell { runId: string; ranAt: string; rate: number | null }
export interface HeatRow {
  query: string;
  cells: HeatCell[];               // oldest→newest, null when query absent that cycle
  stability: string;               // stability_class from computePromptStability
  citedPct: number | null;         // engine-avg citation_rate, latest run
  page: { url: string; similarity: number; weak: boolean } | null;  // query_page_matches latest improvement run
  topCompetitor: { name: string; rate: number } | null;             // competitive_gaps latest tracker run
  waiting: number;                 // pending action_cards with this query_id
}
```

Data: last 6 `tracker_runs` (ids+dates) → `prompt_scores` for those ids (use `engineAverageByQuery` per run); stability via `aggregatePromptScores` + `computePromptStability` from `@/lib/stability` (pass runs oldest→newest); latest `improvement_runs` → its `query_page_matches` (match by `query_text`; `weak = match_type === "weak"`); latest run's `competitive_gaps` rows → per query `compute` top from `competitor_data` (max `mention_rate`); `queries` table maps `prompt_text`→`id` for the WAITING join against pending `action_cards.query_id`. Pass `brand_variations` + `brand_name` and the latest run id down for expansion.

- [ ] **Step 2: API route** `app/api/admin/query-detail/[clientId]/route.ts` — auth exactly like `stability/[clientId]/route.ts`, then:

```ts
// GET ?query=<text>
// 1. latest tracker_run id for client
// 2. tracker_results for that run_id + query: id, engine, brand_mentioned, brand_cited,
//    citation_url, competitor_mentions, response_text, queried_at, run_number
// 3. clients.brand_variations + brand_name
// Per engine: counts { mentioned: x, total: y, cited: z }, representative = pickRepresentative(rows),
// sentence = extractMentionSentence(rep.response_text, [brand_name, ...brand_variations]),
// response payload per engine:
// { engine, mentionedCount, citedCount, total, mentioned, cited, citationUrl,
//   sentence: { sentence, brand } | null, competitorsRecommended: string[] /* rep.competitor_mentions when !mentioned */ }
```

Return `Response.json({ engines })`. Extraction runs server-side (spec item 5).

- [ ] **Step 3: HeatTable client component.** Props `{ rows: HeatRow[]; clientId: string }`. Renders the header row + one row per query; cell background via existing `scoreColor(rate)` at low opacity — implement `heatBg(rate)`:

```ts
function heatBg(rate: number | null): string {
  if (rate === null) return "transparent";
  if (rate === 0) return "rgba(232,154,160,0.14)";
  if (rate < 0.25) return "rgba(253,126,20,0.12)";
  if (rate < 0.5) return "rgba(255,193,7,0.10)";
  return "rgba(132,216,171,0.14)";
}
```

Row click toggles expansion (`useState<string | null>` of expanded query) rendering `<QueryExpansion clientId={clientId} query={row.query} />`. WAITING cell: amber `#d4a017` mono chip `N WAITING` linking to `/admin/approvals` when > 0, else "—". PAGE cell: pathname only (strip origin), `similarity.toFixed(2)`, weak → append mono chip `WEAK` in amber. `<2` cycles → no delta styling anywhere (cells just render what exists).

- [ ] **Step 4: QueryExpansion client component.** On mount `fetch(\`/api/admin/query-detail/${clientId}?query=${encodeURIComponent(query)}\`)`; loading state mono "LOADING…". Per engine sub-row: engine name (mono uppercase), `mentioned {m}/{t} · cited {c}/{t}`, the representative sentence in serif with the matched brand substring wrapped in `<mark style={{ background: "rgba(132,216,171,0.25)", color: "var(--white)" }}>`, citation URL as a link when cited, and when not mentioned: `answer recommended: {competitorsRecommended.join(", ")}` in `--neg`-tinted serif (or "no competitors named" muted).

- [ ] **Step 5: Component test** `__tests__/components/heat-table.test.tsx` (jsdom):

```tsx
// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { HeatTable } from "@/components/admin/HeatTable";

const row = {
  query: "best daycare software",
  cells: [
    { runId: "r1", ranAt: "2026-06-23", rate: 0.2 },
    { runId: "r2", ranAt: "2026-06-30", rate: 0.6 },
  ],
  stability: "gaining",
  citedPct: 0.25,
  page: { url: "https://x.com/guide", similarity: 0.82, weak: false },
  topCompetitor: { name: "KinderCare", rate: 0.61 },
  waiting: 2,
};

describe("HeatTable", () => {
  it("renders query, rates, stability, cited, page, competitor, waiting", () => {
    render(<HeatTable rows={[row]} clientId="c1" />);
    expect(screen.getByText("best daycare software")).toBeTruthy();
    expect(screen.getByText("20%")).toBeTruthy();
    expect(screen.getByText("60%")).toBeTruthy();
    expect(screen.getByText(/gaining/i)).toBeTruthy();
    expect(screen.getByText("25%")).toBeTruthy();
    expect(screen.getByText(/KinderCare/)).toBeTruthy();
    expect(screen.getByText(/2 WAITING/)).toBeTruthy();
  });
  it("flags weak matches", () => {
    render(<HeatTable rows={[{ ...row, page: { ...row.page!, weak: true } }]} clientId="c1" />);
    expect(screen.getByText(/WEAK/)).toBeTruthy();
  });
  it("renders dash when no page match", () => {
    render(<HeatTable rows={[{ ...row, page: null, waiting: 0 }]} clientId="c1" />);
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });
});
```

Run first to see it fail, then make it pass (adjust markup or test to match final render — test asserts content, not styling).

- [ ] **Step 6: Verify** — `npm test && npx tsc --noEmit && npm run build`.

- [ ] **Step 7: Commit**

```bash
git add -A dashboard/
git commit -m "feat: queries heat table with per-engine expansion (Surface 2 pt.2)"
```

---

### Task 13: PAGES tab (D13)

**Files:**
- Rewrite: `dashboard/app/admin/clients/[id]/pages/page.tsx`
- Create: `dashboard/components/pages-tab/PagesTable.tsx` (client — row expansion state)
- Reference: mockup `pages-tab-v2.html`

- [ ] **Step 1: Server page.** Latest `improvement_runs` row for the client; empty state when none: *"No improvement run yet — pages appear after the next scheduled run."* Fetch by `run_id`: `page_inventory`, `page_citation_scores`, `query_page_matches`; plus pending `action_cards` for the client (for per-page waiting links + brief buttons). Assemble:

```ts
export interface PageRowData {
  url: string;
  title: string;
  score: number | null;                 // structural_score; null = not scored (unmatched)
  schemaStatus: string | null;
  hasFaq: boolean;
  hasComparison: boolean;
  wordCount: number;
  lastModified: string | null;
  queriesServed: { query: string; similarity: number; weak: boolean }[];
  checks: Record<string, { score: number; detail?: string }> | null;
  schemaErrors: string[];
  sonnet: { specificity: number; completeness: number; answer_directness: number; summary: string } | null;
  waitingCards: { id: string; action_type: string }[];
}
export interface ContentGapRow {
  query: string;
  topCompetitor: string | null;         // from competitive_gaps latest tracker run (competitor_data max)
  gap: number | null;
  briefCardId: string | null;           // action_cards action_type='content_brief' matching query_id
}
```

`queriesServed` includes `weak` matches display-only (label "weak match, not scored"). Content gaps = `query_page_matches` with `match_type === "content_gap"`.

- [ ] **Step 2: PagesTable component.** Table columns: PAGE (title + url path) | READINESS (score 0-100 color-coded: `>=70 --pos`, `40-69 #ffc107`, `<40 --neg`, null → "not scored" muted) | STRUCTURE (chips: schema_status, FAQ, TABLE) | QUERIES SERVED (count; list in expansion) | WORDS. Row expansion shows:
  - the 9 checks (order: answer_first, faq_schema, comparison_tables, lists, freshness, word_count, source_citations, author_attribution, schema_validation) each as `CHECK NAME  {score} pts — {detail}`;
  - `schema_errors` list when non-empty (mono, `--neg`);
  - Sonnet quality: `SPECIFICITY {n}/5 · COMPLETENESS {n}/5 · DIRECTNESS {n}/5` + summary sentence in serif italic;
  - waiting cards links → `/admin/approvals` (mono amber `{action_type} WAITING`).
  Footer section "CONTENT GAPS": per gap row query + `{topCompetitor} leads by {gap%}` when gap, and either a `VIEW BRIEF CARD →` link (`/admin/approvals#card-{briefCardId}`) or muted italic *"no brief — generated when a competitor leads"*.

- [ ] **Step 3: Verify** — `npx tsc --noEmit && npm run build`; dev-load if env available.

- [ ] **Step 4: Commit**

```bash
git add -A dashboard/
git commit -m "feat: pages tab — inventory, citation readiness, content gaps (D13)"
```

---

### Task 14: RUNS tab + Run detail (Surface 4) + CARDS tab

**Files:**
- Rewrite: `dashboard/app/admin/clients/[id]/runs/page.tsx`, `dashboard/app/admin/clients/[id]/runs/[runId]/page.tsx`, `dashboard/app/admin/clients/[id]/cards/page.tsx`
- Create: `dashboard/components/runs/RunRail.tsx`
- Delete usage of: `RunRow.tsx`, `RunDetail.tsx` (files deleted in Task 16)
- Reference: mockup `run-detail.html`

- [ ] **Step 1: RUNS list.** A run = `pipeline_runs` row. Query all for client (desc `started_at`), plus `improvement_runs` for the client (join in JS by `thread_id`, tolerate null). Columns: DATE | STATUS (mono chip: error `--neg`, awaiting_approval amber, completed `--faint`, running/implementing `--mute`) | CARDS GENERATED (`improvement.cards_generated` or "—") | link → `/admin/clients/{id}/runs/{pipelineRunId}`. Empty state italic muted.

- [ ] **Step 2: Run detail page.** `runId` = pipeline_runs.id. Fetch: the pipeline run; matching `improvement_runs` by `thread_id`; matching `tracker_runs` by `thread_id`; previous `tracker_runs` for the client before that one (delta); `competitive_gaps` for the tracker run (worst gap); by improvement run_id: `page_citation_scores` (avg + min structural_score), `query_page_matches` (matched/weak/gap counts), `action_cards` (total/auto_approved/pending). Next tracker run after `completed_at` (for the footer "re-measured by" line — else next schedule from `fetchSchedules()`).

Render:
- Header: date, duration (`completed_at - started_at`, humanized `Xm Ys`; "running" when null), status chip.
- `<RunRail status={pipeline.status} />`.
- Six evidence tiles (grid 3×2, same tile idiom as `/admin` stats strip):
  1. MEASUREMENT — tracker rate + delta vs previous; worst gap: `losing "{query}" by {gap%} to {name}` (max competitive_gap).
  2. CRAWLABILITY — `BLOCKED`/`CLEAR` (+ `<details>` expansion listing every report key with status + detail).
  3. PAGES — `pages_inventoried` inventoried.
  4. MATCHING — `{matched} matched · {weak} weak · {gaps} gaps`.
  5. READINESS — `avg {avg} · lowest {min}` structural score (— when no scores).
  6. CARDS — `{total} generated · {auto} auto · {pending} to you`.
- Funnel line (mono, one line): `{queries} queries → {matched} matched → {scored} scored → {gaps} gaps → {cards} cards → {auto} auto + {pending} to you` (queries = matches count total; scored = citation score rows).
- Footer: `re-measured by next run {date}` (or `next scheduled run {date}`) + link `VIEW THIS RUN'S CARDS IN APPROVALS →` → `/admin/approvals#run-{improvementRunId}`.
- Every tile must render "—" gracefully when its source row is missing (old runs without thread links).

- [ ] **Step 3: RunRail component** `components/runs/RunRail.tsx` — retrospective, no live progress:

```tsx
const SEGMENTS = ["MEASURE", "DIAGNOSE", "CARDS", "APPROVAL", "IMPLEMENT", "RE-MEASURE"] as const;
// status → segment states (done | active | pending | error):
// running:            [done, active, pending, pending, pending, pending]
// awaiting_approval:  [done, done, done, active, pending, pending]
// implementing:       [done, done, done, done, active, pending]
// completed:          [done, done, done, done, done, pending]  // re-measure belongs to the NEXT run
// error:              first non-done segment renders error (use: running failed → DIAGNOSE error; keep simple: mark all done up to none, show an error chip on the rail's right end with error_message)
```

Render as a horizontal flex of segments joined by 1px lines: done = `--white` dot + label `--mute`; active = amber dot; pending = `--ghost`; error chip `--neg` with `error_message` truncated 80 chars.

- [ ] **Step 4: CARDS tab** `cards/page.tsx`: all `action_cards` for client (`client_id` eq, desc `created_at`), grouped by status sections: PENDING / IMPLEMENTED / APPROVED / REJECTED. Row: date · action_type (mono) · page_url path or query · status chip · `AUTO` chip when auto_approved · verification badge when `verification` present (`verified: true` → `VERIFIED ✓` in `--pos`; false → `NOT VERIFIED` in amber) · `preview_url` link when present ("PR/PREVIEW →"). Note: read `action_type`/`structural_score`, never legacy `pillar`/`score`.

- [ ] **Step 5: Verify** — `npx tsc --noEmit && npm run build` (note: old `RunDetail`/`RunRow` imports must be gone from these pages).

- [ ] **Step 6: Commit**

```bash
git add -A dashboard/
git commit -m "feat: pipeline run list, retrospective run detail, cards tab (Surface 4)"
```

---

### Task 15: Surface 3 — Approvals inbox rebuild

**Files:**
- Rewrite: `dashboard/app/admin/approvals/page.tsx`
- Create: `dashboard/components/approvals/InboxGroup.tsx` (client), `dashboard/components/approvals/AutomatedCard.tsx`, `BriefCard.tsx`, `CommunityCheckCard.tsx`, `CrawlabilityCard.tsx`
- Test: `dashboard/__tests__/components/approval-cards.test.tsx`
- Reference: mockup `approvals-inbox.html`

- [ ] **Step 1: Server page.** Fetch pending cards on the NEW schema:

```ts
const { data: cards } = await supabase
  .from("action_cards")
  .select("id, run_id, client_id, query_id, page_url, action_type, track, priority, competitive_gap, structural_score, issue, before_text, after_text, code_block, status, cms_action, auto_approved, brief, reddit_data, created_at")
  .in("status", ["pending", "approved"])  // approved = auto_approved not yet implemented
  .order("created_at", { ascending: true });
```

Filter in JS: review items = `status === "pending" && !auto_approved`; auto-approved footer items = `auto_approved === true && status !== "implemented"`. Group by `run_id` (improvement run id). For each group fetch its `improvement_runs` row (`id, client_id, ran_at, thread_id`), the client (`brand_name, cms_type`), and thread resolution: prefer `improvement_runs.thread_id`; when null (pre-010 rows) fall back to the latest `pipeline_runs` for that client with `status = "awaiting_approval"` and `started_at <= ran_at` (order desc, limit 1). Metrics context per group: latest 2 `tracker_runs` for the client → rate, delta, `topCompetitor` + `rankAndGap` → strip text `why you're here: {rate} {▲/▼}{delta} · losing to {name} by {gap}` (or "leading" when gap 0). Sort groups oldest-first (wait age). Each group gets `id="run-{runId}"` anchor; each card `id="card-{cardId}"`.

- [ ] **Step 2: InboxGroup client component.** Props: `{ group }` where

```ts
interface InboxGroupData {
  runId: string;
  threadId: string | null;
  clientName: string;
  cmsType: string;
  waitDays: number;
  contextStrip: string;
  cards: ActionCard[];          // review items, from lib/improvement-types
  autoApproved: { id: string; action_type: string }[];
}
```

Header: `{clientName} — {cards.length} CARDS · WAITING {waitDays}D` + CMS consequence line (mono): `wordpress → "WORDPRESS — changes go live on approve"`, `github → "GITHUB — opens a PR, you merge"`, `webflow → "WEBFLOW — staged, you publish"`, `shopify → "SHOPIFY — changes go live on approve"`, else `"COPY_PASTE — manual apply"`. Context strip beneath in serif italic. Decision state: `useState<Record<string, "approved" | "rejected">>({})` like old ApprovalsClient, plus community-check per-card local state. Renders each card through a type switch:

```tsx
function renderCard(card: ActionCard) {
  if (card.action_type === "content_brief") return <BriefCard ... />;
  if (card.action_type === "community_check" || card.action_type === "reddit_engagement") return <CommunityCheckCard ... />;
  if (card.action_type === "fix_crawlability") return <CrawlabilityCard ... />;
  return <AutomatedCard ... />;
}
```

Every card shows a "why" line: `target: "{queryText ?? page_url}" {competitive_gap ? `· gap ${formatRate(gap)}` : ""}` (pass query text map from server: `queries` table lookup by query_id). Footer per group: tally `{approved} approved · {rejected} rejected · {undecided} undecided`, auto-approved note *"{n} cards auto-approved — implement on finalize"* listing action_types, and the FINALIZE button (`disabled` until every review card decided; label `FINALIZE RUN ({approved} approve / {rejected} reject)`); POST to `/api/admin/approve` with `{ threadId, approvedCardIds, rejectedCardIds }`. `threadId === null` → button disabled with note "thread unresolved — resume from server". Success → group collapses to a confirmation line.

- [ ] **Step 3: Card renderers.** All follow the old `ApprovalCard.tsx` visual idiom (bordered box, mono labels, `--ink-2` code backgrounds — NOT `--surface`):
  - **AutomatedCard**: issue serif; BEFORE (`--neg` text) / AFTER (`--pos`) pre blocks; CODE block when present; buttons APPROVE (`--pos` border) / REJECT (`--neg` border) / VIEW PAGE (link to page_url, `--faint` border).
  - **BriefCard**: renders `card.brief` as a document — recommended_title (font-display 20px), H1 line, KEY SECTIONS as list, FACTS TO INCLUDE list, `SCHEMA {schema_type} · TARGET {word_count_target} WORDS` mono footer. Buttons: ACCEPT & ASSIGN (maps to approve; no implementation happens — cms_action is "none") / REJECT.
  - **CommunityCheckCard**: issue; two search-link buttons `SEARCH REDDIT →` and `GOOGLE SITE:REDDIT →` (from `reddit_data.search_links`, `target="_blank"`); guidance serif italic; a thread-URL text input + MARK DONE (approve with the URL noted — store input value via `onDone(cardId, threadUrl)` which the group holds in state and simply approves the card; URL persistence beyond approval is out of scope for v1 — display-only) / SKIP (reject).
  - **CrawlabilityCard**: the issue statement large serif, `PRIORITY 0` chip `--neg`, APPROVE (assign fix) / REJECT.

- [ ] **Step 4: Component tests** `__tests__/components/approval-cards.test.tsx` (jsdom) — one render test per card type asserting its distinctive content:

```tsx
// @vitest-environment jsdom
// AutomatedCard: renders issue, before/after text, APPROVE + REJECT buttons; clicking APPROVE calls onDecide(card.id, "approved")
// BriefCard: renders brief.recommended_title, key_sections items, "ACCEPT & ASSIGN"
// CommunityCheckCard: renders both search links with correct hrefs from reddit_data.search_links, MARK DONE, SKIP
// CrawlabilityCard: renders issue and PRIORITY 0
```

Write the four tests with realistic card fixtures (use the `ActionCard` type; brief/reddit_data shapes from Task 7). Run → fail → implement → pass.

- [ ] **Step 5: Deep links + old component note.** Board waiting badges and drilldown WAITING cells already link to `/admin/approvals` (Tasks 10/12); confirm anchors `#run-{id}` / `#card-{id}` exist here. Old `ApprovalCard.tsx`/`ApprovalsClient.tsx` are now unreferenced (deleted next task).

- [ ] **Step 6: Verify** — `npm test && npx tsc --noEmit && npm run build`.

- [ ] **Step 7: Commit**

```bash
git add -A dashboard/
git commit -m "feat: grouped approvals inbox with per-run finalize (Surface 3)"
```

---

### Task 16: Removals — legacy audit surfaces & dead components

**Files:**
- Delete: `dashboard/app/admin/clients/[id]/audit/` (entire directory: page, loading, [runId]/page, [runId]/loading, [runId]/PageScoreRow.tsx), `dashboard/app/admin/clients/[id]/export/[runId]/page.tsx` (reads `audit_runs`; only linked from audit pages), `dashboard/components/admin/TriggerAuditButton.tsx`, `dashboard/components/admin/ApprovalCard.tsx`, `dashboard/components/admin/ApprovalsClient.tsx`, `dashboard/components/admin/RunDetail.tsx`, `dashboard/components/admin/RunRow.tsx`
- Verify no other file references them.

- [ ] **Step 1: Delete**

```bash
git rm -r "dashboard/app/admin/clients/[id]/audit" "dashboard/app/admin/clients/[id]/export"
git rm dashboard/components/admin/TriggerAuditButton.tsx dashboard/components/admin/ApprovalCard.tsx dashboard/components/admin/ApprovalsClient.tsx dashboard/components/admin/RunDetail.tsx dashboard/components/admin/RunRow.tsx
```

- [ ] **Step 2: Sweep references**

Run: `grep -rn "TriggerAuditButton\|PageScoreRow\|ApprovalsClient\|ApprovalCard\|RunDetail\|RunRow\|/audit\|/export/" dashboard/app dashboard/components --include="*.tsx" --include="*.ts"`
Expected: no hits (fix any stragglers — e.g. links in `ClientRow.tsx` or old loading files).

- [ ] **Step 3: Build** — `cd dashboard && npx tsc --noEmit && npm run build` — clean.

- [ ] **Step 4: Commit**

```bash
git add -A dashboard/
git commit -m "chore: remove legacy audit surfaces and superseded components"
```

---

### Task 17: Final verification pass

- [ ] **Step 1: Full test suites**

Run: `cd agents && .venv/bin/python -m pytest tests/ -q` and `cd dashboard && npm test && npm run lint && npx tsc --noEmit && npm run build`
Expected: everything green.

- [ ] **Step 2: Spec walk.** Open the spec and confirm each surface/element maps to shipped code (board hero format, delta, movers, sparkline, badge precedence, rollup, footer; drilldown hero + citation-rate line + next-run + banner; overview timeline labels + GSC; queries table all 7 columns + expansion contents; pages tab table/expansion/gaps footer; runs list + rail + 6 tiles + funnel + footer links; inbox grouping/context/renderers/auto-footer/rejections; removals). Fix gaps before proceeding.

- [ ] **Step 3: Runtime smoke.** If `.env`/Supabase creds are available in `dashboard/`: `npm run dev`, load `/admin`, `/admin/clients`, one drilldown tab each, `/admin/approvals`. Empty-data states must render without crashes. Record what was and wasn't verifiable.

- [ ] **Step 4: Deploy checklist (report, don't run):** paste migration 010 in Supabase SQL editor; redeploy FastAPI (approve API change is backward-compatible); Vercel deploy after.

---

## Self-review notes (already applied)

- Spec's "Sidebar" rendered as existing top nav (Conventions #8) — hierarchy preserved, visual language unchanged.
- Spec's inbox thread fix required a run↔thread link that doesn't exist in the schema; Task 1's migration is the minimal structural fix (spec backend item list implies it via Surface 3 bullet 1).
- `measuring` badge derivation defined as implemented-cards-created-after-latest-tracker-run (pipeline order guarantees card `created_at` > its cycle's tracker `ran_at`).
- Community-check thread-URL persistence: no storage endpoint exists; v1 treats MARK DONE as approve (recorded decision), URL input display-only — consistent with spec's no-fabricated-data rule.
