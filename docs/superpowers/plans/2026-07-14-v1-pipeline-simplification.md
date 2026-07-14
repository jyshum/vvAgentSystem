# V1 Pipeline Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make new, explicitly enabled V1 runs use tracked-query visibility, the deterministic technical-audit foundation, and at most five direct community-research opportunities without executing or presenting the legacy query-page matcher, readiness scorer, content-gap briefs, or AI-authored technical fixes.

**Architecture:** Add one fail-closed rollout policy at the improvement-pipeline boundary. When that policy is active for a client, preserve the neutral page inventory, run only implemented technical check sets, bypass every heuristic/LLM content-audit stage, and derive community opportunities directly from tracker competitor rates. Keep the existing legacy route and historical tables untouched. Simplify primary dashboard views for V1 while rendering old run URLs in an explicit legacy mode.

**Tech Stack:** Python 3.11, pytest, Supabase/PostgREST, Next.js 16, React 19, TypeScript, Vitest, Testing Library.

## Global Constraints

- Do not delete, migrate, or reinterpret historical `query_page_matches`, `page_citation_scores`, `page_inventory`, `competitive_gaps`, or `action_cards` rows.
- Do not remove the direct `/admin/clients/[id]/pages` route; remove only its primary-navigation entry.
- An active V1 run must never fall back to legacy matching/scoring because a technical check failed or returned Unknown.
- An inactive or non-allowlisted client must retain the current legacy pipeline unchanged.
- The technical-audit feature remains default-off and internal-client-only. An empty allowlist means no client is enabled; `*` is the explicit all-client development escape hatch.
- Only implemented check sets may be configured. In this plan, that is `foundation`; later plans expand the same registry.
- No AI model selects community opportunities, evaluates technical facts, writes technical fixes, approves changes, or publishes changes in this tranche.
- New V1 community cards are manual search tasks, not claims that a Reddit thread was found or validated.
- The neutral inventory remains available as bounded technical evidence. It must not be described as query coverage.
- Run focused tests after every task and the full agent/dashboard suites before completion.

---

## Task 1: Add a fail-closed rollout policy

**Files:**

- Create: `agents/src/technical_audit/rollout.py`
- Create: `agents/tests/technical_audit/test_rollout.py`
- Modify: `agents/src/technical_audit/__init__.py`

- [ ] **Step 1: Write failing rollout-policy tests**

Create `agents/tests/technical_audit/test_rollout.py` with tests for all boundary cases:

```python
import pytest

from src.technical_audit.rollout import AuditRolloutPolicy


def test_defaults_are_off_and_allow_nobody(monkeypatch):
    monkeypatch.delenv("TECHNICAL_AUDIT_V1_ENABLED", raising=False)
    monkeypatch.delenv("TECHNICAL_AUDIT_INTERNAL_CLIENT_IDS", raising=False)
    monkeypatch.delenv("TECHNICAL_AUDIT_CHECK_SETS", raising=False)

    policy = AuditRolloutPolicy.from_environment()

    assert policy.enabled is False
    assert policy.client_ids == frozenset()
    assert policy.check_sets == ("foundation",)
    assert policy.active_for("client-1") is False


def test_enabled_requires_explicit_client_membership(monkeypatch):
    monkeypatch.setenv("TECHNICAL_AUDIT_V1_ENABLED", "true")
    monkeypatch.setenv(
        "TECHNICAL_AUDIT_INTERNAL_CLIENT_IDS", "client-1, client-2"
    )

    policy = AuditRolloutPolicy.from_environment()

    assert policy.active_for("client-1") is True
    assert policy.active_for("client-3") is False


def test_star_explicitly_enables_all_clients(monkeypatch):
    monkeypatch.setenv("TECHNICAL_AUDIT_V1_ENABLED", "true")
    monkeypatch.setenv("TECHNICAL_AUDIT_INTERNAL_CLIENT_IDS", "*")

    assert AuditRolloutPolicy.from_environment().active_for("any-client") is True


def test_only_available_check_sets_are_accepted(monkeypatch):
    monkeypatch.setenv("TECHNICAL_AUDIT_CHECK_SETS", "foundation,protocol")

    with pytest.raises(ValueError, match="Unavailable technical audit check set"):
        AuditRolloutPolicy.from_environment()
```

- [ ] **Step 2: Run the focused test and confirm it fails**

Run:

```bash
cd agents
.venv/bin/python -m pytest tests/technical_audit/test_rollout.py -q
```

Expected: collection fails because `src.technical_audit.rollout` does not exist.

- [ ] **Step 3: Implement the immutable policy**

Create `agents/src/technical_audit/rollout.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
import os


AVAILABLE_CHECK_SETS = frozenset({"foundation"})


def _csv(value: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(part.strip() for part in value.split(",") if part.strip()))


@dataclass(frozen=True)
class AuditRolloutPolicy:
    enabled: bool
    client_ids: frozenset[str]
    check_sets: tuple[str, ...]

    @classmethod
    def from_environment(cls) -> "AuditRolloutPolicy":
        enabled = os.environ.get("TECHNICAL_AUDIT_V1_ENABLED", "false").lower() == "true"
        client_ids = frozenset(_csv(os.environ.get("TECHNICAL_AUDIT_INTERNAL_CLIENT_IDS", "")))
        check_sets = _csv(os.environ.get("TECHNICAL_AUDIT_CHECK_SETS", "foundation"))
        unavailable = set(check_sets) - AVAILABLE_CHECK_SETS
        if unavailable:
            names = ", ".join(sorted(unavailable))
            raise ValueError(f"Unavailable technical audit check set(s): {names}")
        if not check_sets:
            raise ValueError("At least one technical audit check set is required")
        return cls(enabled=enabled, client_ids=client_ids, check_sets=check_sets)

    def active_for(self, client_id: str) -> bool:
        return self.enabled and ("*" in self.client_ids or client_id in self.client_ids)
```

Export `AuditRolloutPolicy` and `AVAILABLE_CHECK_SETS` from `agents/src/technical_audit/__init__.py` without importing the runner or causing network initialization.

- [ ] **Step 4: Run the focused tests and confirm they pass**

Run:

```bash
cd agents
.venv/bin/python -m pytest tests/technical_audit/test_rollout.py -q
```

Expected: all four tests pass.

- [ ] **Step 5: Commit**

```bash
git add agents/src/technical_audit/rollout.py agents/src/technical_audit/__init__.py agents/tests/technical_audit/test_rollout.py
git commit -m "feat: add fail-closed technical audit rollout policy"
```

---

## Task 2: Select community opportunities directly from tracker evidence

**Files:**

- Create: `agents/src/improvement/community.py`
- Create: `agents/tests/test_community.py`
- Reuse without changing behavior: `agents/src/improvement/card_generator.py`

- [ ] **Step 1: Write failing deterministic-selection tests**

Create `agents/tests/test_community.py`:

```python
from src.improvement.community import select_community_opportunities


def _gap(query_id, query, client, competitors, bucket="consideration"):
    return {
        "query_id": query_id,
        "query": query,
        "bucket": bucket,
        "client_mention_rate": client,
        "competitor_data": competitors,
    }


def test_selects_only_positive_competitor_leads_in_descending_order():
    rows = [
        _gap("q2", "second", 0.20, [{"name": "B", "mention_rate": 0.60}]),
        _gap("q1", "first", 0.10, [{"name": "A", "mention_rate": 0.50}]),
        _gap("q3", "winning", 0.70, [{"name": "C", "mention_rate": 0.20}]),
        _gap("q4", "no evidence", 0.10, []),
    ]

    selection = select_community_opportunities(rows)

    assert selection.competitor_lead_count == 2
    assert [item.query_id for item in selection.opportunities] == ["q1", "q2"]
    assert selection.opportunities[0].top_competitor == "A"
    assert selection.opportunities[0].competitive_gap == 0.4


def test_uses_query_id_as_stable_tie_break_and_caps_at_five():
    rows = [
        _gap(f"q{i}", f"query {i}", 0.0, [{"name": "A", "mention_rate": 0.5}])
        for i in range(7, 0, -1)
    ]

    selection = select_community_opportunities(rows, limit=5)

    assert selection.competitor_lead_count == 7
    assert [item.query_id for item in selection.opportunities] == [
        "q1", "q2", "q3", "q4", "q5"
    ]


def test_card_payload_contains_measured_values_but_no_thread_claim():
    selection = select_community_opportunities([
        _gap("q1", "medical student budgeting", 0.1, [
            {"name": "Competitor", "mention_rate": 0.55}
        ])
    ])

    payload = selection.opportunities[0].to_gap_dict()

    assert payload == {
        "query": "medical student budgeting",
        "query_id": "q1",
        "bucket": "consideration",
        "top_competitor": "Competitor",
        "client_mention_rate": 0.1,
        "competitor_mention_rate": 0.55,
        "competitive_gap": 0.45,
    }
    assert "thread_url" not in payload
```

- [ ] **Step 2: Run the test and confirm the missing module failure**

Run:

```bash
cd agents
.venv/bin/python -m pytest tests/test_community.py -q
```

Expected: collection fails because `src.improvement.community` does not exist.

- [ ] **Step 3: Implement pure selection types and logic**

Create `agents/src/improvement/community.py` with these public interfaces:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CommunityOpportunity:
    query: str
    query_id: str | None
    bucket: str
    top_competitor: str
    client_mention_rate: float
    competitor_mention_rate: float
    competitive_gap: float

    def to_gap_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class CommunitySelection:
    opportunities: tuple[CommunityOpportunity, ...]
    competitor_lead_count: int


def select_community_opportunities(
    gap_rows: list[dict], *, limit: int = 5
) -> CommunitySelection:
    candidates: list[CommunityOpportunity] = []
    for row in gap_rows:
        competitors = row.get("competitor_data") or []
        if not competitors:
            continue
        top = max(competitors, key=lambda item: float(item.get("mention_rate") or 0.0))
        client_rate = float(row.get("client_mention_rate") or 0.0)
        competitor_rate = float(top.get("mention_rate") or 0.0)
        gap = round(competitor_rate - client_rate, 4)
        if gap <= 0:
            continue
        candidates.append(CommunityOpportunity(
            query=row["query"],
            query_id=row.get("query_id"),
            bucket=row.get("bucket") or "",
            top_competitor=top["name"],
            client_mention_rate=client_rate,
            competitor_mention_rate=competitor_rate,
            competitive_gap=gap,
        ))
    candidates.sort(key=lambda item: (
        -item.competitive_gap,
        item.query_id or item.query,
    ))
    return CommunitySelection(
        opportunities=tuple(candidates[:max(0, limit)]),
        competitor_lead_count=len(candidates),
    )
```

Do not call `check_competitive_gaps`, the matcher, a model SDK, or Supabase from this module.

- [ ] **Step 4: Run the focused tests**

Run:

```bash
cd agents
.venv/bin/python -m pytest tests/test_community.py -q
```

Expected: all three tests pass.

- [ ] **Step 5: Commit**

```bash
git add agents/src/improvement/community.py agents/tests/test_community.py
git commit -m "feat: derive community opportunities from visibility evidence"
```

---

## Task 3: Bypass the legacy content audit for allowlisted V1 runs

**Files:**

- Modify: `agents/src/improvement/pipeline.py`
- Modify: `agents/tests/test_improvement_pipeline.py`
- Verify unchanged contract: `agents/src/graph/nodes.py`
- Verify unchanged state shape: `agents/src/graph/state.py`

- [ ] **Step 1: Replace the enabled-run regression test with strict non-call assertions**

In `agents/tests/test_improvement_pipeline.py`, update the existing V1-enabled test setup to set all three controls:

```python
monkeypatch.setenv("TECHNICAL_AUDIT_V1_ENABLED", "true")
monkeypatch.setenv("TECHNICAL_AUDIT_INTERNAL_CLIENT_IDS", "client-1")
monkeypatch.setenv("TECHNICAL_AUDIT_CHECK_SETS", "foundation")
```

Supply seven positive direct tracker gaps in deliberately unsorted order. Patch every forbidden legacy stage and assert none is called:

```python
mock_match.assert_not_called()
mock_gap_check.assert_not_called()
mock_score.assert_not_called()
mock_quality.assert_not_called()
mock_classify.assert_not_called()
mock_sonnet.assert_not_called()
mock_brief.assert_not_called()
mock_crawlability_card.assert_not_called()
```

Also assert:

```python
assert result["query_matches"] == []
assert result["citation_scores"] == []
assert len(result["competitive_gap_data"]) == 5
assert [card["action_type"] for card in result["action_cards"]] == [
    "community_check"
] * 5
assert all(card["track"] == "manual" for card in result["action_cards"])
assert "query_page_matches" not in [call.args[0] for call in sb.table.call_args_list]
assert "page_citation_scores" not in [call.args[0] for call in sb.table.call_args_list]
```

Inspect the `improvement_runs.update(...)` call and assert `queries_matched == 0`, `content_gaps_found == 0`, `competitive_gaps_found == 7`, and `cards_generated == 5`.

- [ ] **Step 2: Add a non-allowlisted legacy regression test**

Add a test with the global flag true but `TECHNICAL_AUDIT_INTERNAL_CLIENT_IDS=client-2` while the state client is `client-1`. Assert the matcher and legacy gap helper are called, no technical-audit tables are touched, and the legacy return values remain present. This proves the allowlist is a routing control, not merely a UI flag.

- [ ] **Step 3: Add an audit-error non-fallback test**

Update the existing technical-audit initialization-failure test so the client is allowlisted. Make `_run_and_persist_technical_audit` raise. Assert the returned `technical_audit_error` is populated while matcher, scorer, content brief, and Sonnet mocks remain uncalled. This is the safety invariant: a failed deterministic audit must not activate the deprecated heuristic path.

- [ ] **Step 4: Run the focused pipeline tests and confirm failure**

Run:

```bash
cd agents
.venv/bin/python -m pytest tests/test_improvement_pipeline.py -q
```

Expected: the new assertions fail because the current flag-only path still calls `match_queries_to_pages` and `check_competitive_gaps`.

- [ ] **Step 5: Route once at the pipeline boundary**

In `agents/src/improvement/pipeline.py`:

1. Import `AuditRolloutPolicy` and `select_community_opportunities`.
2. Build the policy once after `client_id` is known.
3. Assign `technical_v1_active = policy.active_for(client_id)`.
4. Replace every current `technical_audit_enabled` branch with `technical_v1_active`.
5. Pass `policy.check_sets` into `_run_and_persist_technical_audit`; store the set names in `technical_audit_runs.scope` at insert and completion.
6. Keep `build_inventory` and `page_inventory` persistence in both routes.

Use this exact stage split:

```python
if technical_v1_active:
    print("  Step 3: Query-page matching deferred for technical V1...")
    matches = []
else:
    print("  Step 3: Query-page matching...")
    query_dicts = [
        {
            "query": q["prompt_text"],
            "query_id": q["id"],
            "bucket": q.get("bucket", ""),
        }
        for q in queries
    ]
    matches = match_queries_to_pages(inventory, query_dicts)
    # Preserve the existing query_page_matches insert here.
```

Use this exact community split:

```python
if technical_v1_active:
    community_selection = select_community_opportunities(
        competitive_gaps_data or [], limit=5
    )
    gap_results = [
        opportunity.to_gap_dict()
        for opportunity in community_selection.opportunities
    ]
    comp_gaps = community_selection.competitor_lead_count
else:
    gap_results = check_competitive_gaps(matches, competitive_gaps_data or [])
    comp_gaps = sum(
        1 for gap in gap_results if gap["competitive_gap"] > 0
    )
```

Leave the existing card-persistence and history machinery shared. Empty `matches` and `citation_scores` prevent page actions and content briefs; `gap_results` contains only the bounded community opportunities. Continue to call `build_community_check_card` so its manual search links and cautious guidance remain unchanged.

Do not remove legacy imports or functions in this tranche; the inactive route still uses them.

- [ ] **Step 6: Make check-set execution explicit**

Change `run_technical_audit` and `build_v1_registry` to accept `enabled_check_sets: tuple[str, ...]`. In this tranche:

```python
def build_v1_registry(
    enabled_check_sets: tuple[str, ...] = ("foundation",),
) -> CheckRegistry:
    if enabled_check_sets != ("foundation",):
        raise ValueError(
            f"Unsupported technical audit check sets: {enabled_check_sets}"
        )
    # Register the four existing foundation checks.
```

Pass the policy value through `_run_and_persist_technical_audit` to `run_technical_audit`. This prevents a configuration string from claiming that an unimplemented check set ran.

- [ ] **Step 7: Preserve the graph return shape**

Do not remove `query_matches`, `citation_scores`, or `competitive_gap_data` from `GEOState` yet. New V1 runs return empty lists for the first two and the selected measured opportunities for the third. Legacy and historical consumers continue to receive the old shapes.

- [ ] **Step 8: Run agent tests**

Run:

```bash
cd agents
.venv/bin/python -m pytest tests/test_community.py tests/technical_audit/test_rollout.py tests/test_improvement_pipeline.py tests/test_graph_nodes.py -q
```

Expected: all focused tests pass.

- [ ] **Step 9: Commit**

```bash
git add agents/src/improvement/pipeline.py agents/src/technical_audit/runner.py agents/src/technical_audit/checks/__init__.py agents/tests/test_improvement_pipeline.py
git commit -m "feat: bypass legacy scoring for allowlisted v1 runs"
```

---

## Task 4: Remove page-matching claims from the primary query view

**Files:**

- Modify: `dashboard/app/admin/clients/[id]/queries/page.tsx`
- Modify: `dashboard/components/admin/HeatTable.tsx`
- Modify: `dashboard/__tests__/components/heat-table.test.tsx`

- [ ] **Step 1: Update the HeatTable test to specify the simplified columns**

Remove the `page` field from the test fixture and replace the page-match tests with:

```tsx
it("renders visibility evidence without a page-match or similarity column", () => {
  render(<HeatTable rows={[row]} clientId="c1" />);
  expect(screen.getByText("best daycare software")).toBeTruthy();
  expect(screen.getByText("20%")).toBeTruthy();
  expect(screen.getByText("60%")).toBeTruthy();
  expect(screen.getByText("25%")).toBeTruthy();
  expect(screen.getByText(/KinderCare/)).toBeTruthy();
  expect(screen.queryByText("PAGE")).toBeNull();
  expect(screen.queryByText(/0\.82/)).toBeNull();
  expect(screen.queryByText("WEAK")).toBeNull();
});
```

- [ ] **Step 2: Run the component test and confirm failure**

Run:

```bash
cd dashboard
npm test -- __tests__/components/heat-table.test.tsx
```

Expected: the assertion fails because the current table still renders `PAGE`.

- [ ] **Step 3: Remove matcher data from the query page**

In `dashboard/app/admin/clients/[id]/queries/page.tsx`:

- remove the latest `improvement_runs` fetch;
- remove the `query_page_matches` fetch;
- remove `latestImprovementRunId`, `matches`, and `pageByQuery`;
- stop adding `page` to each `HeatRow`;
- retain tracked-query history, citation rate, stability, competitor visibility, paraphrases, and pending-card counts.

In `dashboard/components/admin/HeatTable.tsx`:

- remove `page` from `HeatRow`;
- remove `pagePathname`;
- remove the `PAGE` header and row cell;
- update the grid template from five trailing data columns to four:

```tsx
const gridTemplate = `2fr repeat(${cycleCount}, 44px) 0.8fr 0.6fr 1fr 0.8fr`;
```

Do not remove the competitor or pending-card columns. They remain useful and are not generated by page matching.

- [ ] **Step 4: Run the focused test and type-aware lint**

Run:

```bash
cd dashboard
npm test -- __tests__/components/heat-table.test.tsx
npx eslint components/admin/HeatTable.tsx app/admin/clients/'[id]'/queries/page.tsx __tests__/components/heat-table.test.tsx
```

Expected: tests and changed-file lint pass.

- [ ] **Step 5: Commit**

```bash
git add dashboard/app/admin/clients/'[id]'/queries/page.tsx dashboard/components/admin/HeatTable.tsx dashboard/__tests__/components/heat-table.test.tsx
git commit -m "refactor: remove heuristic page matching from query view"
```

---

## Task 5: Hide the legacy Pages tab while preserving its route

**Files:**

- Create: `dashboard/lib/client-tabs.ts`
- Create: `dashboard/__tests__/client-tabs.test.ts`
- Modify: `dashboard/app/admin/clients/[id]/layout.tsx`
- Do not modify: `dashboard/app/admin/clients/[id]/pages/page.tsx`

- [ ] **Step 1: Write the navigation contract test**

Create `dashboard/__tests__/client-tabs.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { clientTabs } from "@/lib/client-tabs";

describe("clientTabs", () => {
  it("omits the legacy Pages route from primary navigation", () => {
    const tabs = clientTabs("client-1");
    expect(tabs.map((tab) => tab.label)).toEqual([
      "OVERVIEW",
      "QUERIES",
      "RUNS",
      "CARDS",
      "CONFIG",
      "REPORTS",
    ]);
    expect(tabs.some((tab) => tab.href.endsWith("/pages"))).toBe(false);
  });
});
```

- [ ] **Step 2: Run the test and confirm the missing-module failure**

Run:

```bash
cd dashboard
npm test -- __tests__/client-tabs.test.ts
```

Expected: the test fails because `@/lib/client-tabs` does not exist.

- [ ] **Step 3: Extract the primary tab list**

Create `dashboard/lib/client-tabs.ts`:

```ts
export interface ClientTab {
  label: string;
  href: string;
}

export function clientTabs(clientId: string): ClientTab[] {
  return [
    { label: "OVERVIEW", href: `/admin/clients/${clientId}/overview` },
    { label: "QUERIES", href: `/admin/clients/${clientId}/queries` },
    { label: "RUNS", href: `/admin/clients/${clientId}/runs` },
    { label: "CARDS", href: `/admin/clients/${clientId}/cards` },
    { label: "CONFIG", href: `/admin/clients/${clientId}/config` },
    { label: "REPORTS", href: `/admin/clients/${clientId}/reports` },
  ];
}
```

Import and call `clientTabs(id)` in `layout.tsx`. Do not redirect, delete, or edit the Pages route; old bookmarks and historical evidence must continue to work.

- [ ] **Step 4: Run the focused test and lint**

Run:

```bash
cd dashboard
npm test -- __tests__/client-tabs.test.ts
npx eslint lib/client-tabs.ts app/admin/clients/'[id]'/layout.tsx __tests__/client-tabs.test.ts
```

Expected: test and lint pass.

- [ ] **Step 5: Commit**

```bash
git add dashboard/lib/client-tabs.ts dashboard/__tests__/client-tabs.test.ts dashboard/app/admin/clients/'[id]'/layout.tsx
git commit -m "refactor: hide legacy pages view from primary navigation"
```

---

## Task 6: Give technical V1 and historical runs distinct presentations

**Files:**

- Create: `dashboard/lib/run-presentation.ts`
- Create: `dashboard/__tests__/run-presentation.test.ts`
- Modify: `dashboard/app/admin/clients/[id]/runs/[runId]/page.tsx`

- [ ] **Step 1: Write pure presentation tests**

Create `dashboard/__tests__/run-presentation.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { buildRunFunnel, runPresentationMode } from "@/lib/run-presentation";

describe("run presentation", () => {
  it("uses technical mode when a checklist run exists", () => {
    expect(runPresentationMode({ id: "audit-1" })).toBe("technical_v1");
  });

  it("does not describe matching or content gaps in technical mode", () => {
    const text = buildRunFunnel({
      mode: "technical_v1",
      technicalStatus: "completed",
      technicalChecks: 14,
      technicalFailures: 2,
      technicalReviews: 3,
      technicalUnknown: 1,
      competitorLeads: 7,
      cards: 5,
      matched: 0,
      weak: 0,
      contentGaps: 0,
      scoredPages: 0,
    });
    expect(text).toContain("14 technical checks");
    expect(text).toContain("7 measured competitor leads");
    expect(text).toContain("5 manual cards");
    expect(text).not.toMatch(/matched|weak|content gaps|scored/i);
  });

  it("preserves the legacy funnel vocabulary", () => {
    const text = buildRunFunnel({
      mode: "legacy",
      technicalStatus: null,
      technicalChecks: 0,
      technicalFailures: 0,
      technicalReviews: 0,
      technicalUnknown: 0,
      competitorLeads: 2,
      cards: 3,
      matched: 4,
      weak: 1,
      contentGaps: 2,
      scoredPages: 4,
    });
    expect(text).toContain("4 matched");
    expect(text).toContain("1 weak");
    expect(text).toContain("2 content gaps");
    expect(text).toContain("4 pages scored");
  });
});
```

- [ ] **Step 2: Run and confirm failure**

Run:

```bash
cd dashboard
npm test -- __tests__/run-presentation.test.ts
```

Expected: missing-module failure.

- [ ] **Step 3: Implement the pure mode/funnel helper**

Create `dashboard/lib/run-presentation.ts` with:

```ts
export type RunPresentationMode = "technical_v1" | "legacy";

export function runPresentationMode(
  technicalAuditRun: { id: string } | null,
): RunPresentationMode {
  return technicalAuditRun ? "technical_v1" : "legacy";
}
```

Add a typed `buildRunFunnel` that returns:

- technical completed: `AI visibility measured → {n} technical checks · {fail} failures · {review} reviews · {unknown} unknown → {leads} measured competitor leads → {cards} manual cards`;
- technical non-completed: `AI visibility measured → technical audit {status} → {leads} measured competitor leads → {cards} manual cards`;
- legacy: preserve the existing matched/weak/content-gap/page-scored wording.

- [ ] **Step 4: Apply mode-aware rendering to the run page**

In `dashboard/app/admin/clients/[id]/runs/[runId]/page.tsx`:

- compute the mode only after `technicalAuditBundle` is available;
- show a visible `LEGACY CONTENT AUDIT` badge for improvement runs without a technical-audit run;
- in technical mode, keep the neutral inventory tile but label it `AUDIT SCOPE`, not page coverage;
- render the `MATCHING` tile only in legacy mode;
- retain the technical checklist in technical mode;
- use `buildRunFunnel` so technical runs never display matched, weak, content-gap, readiness-score, or page-scored language;
- in technical mode label the action count as manual/review work, not auto-generated fixes;
- keep the existing legacy score and matching calculations solely for legacy rendering.

It is acceptable for this tranche to keep read-only historical queries in the server fetch. New V1 runs write no matching/score rows, and the next schema/card plan will further normalize the data loader. Avoid a broad server-component rewrite here.

- [ ] **Step 5: Run focused tests and changed-file lint**

Run:

```bash
cd dashboard
npm test -- __tests__/run-presentation.test.ts __tests__/components/technical-audit-checklist.test.tsx
npx eslint lib/run-presentation.ts __tests__/run-presentation.test.ts app/admin/clients/'[id]'/runs/'[runId]'/page.tsx
```

Expected: tests and changed-file lint pass.

- [ ] **Step 6: Commit**

```bash
git add dashboard/lib/run-presentation.ts dashboard/__tests__/run-presentation.test.ts dashboard/app/admin/clients/'[id]'/runs/'[runId]'/page.tsx
git commit -m "refactor: separate technical v1 and legacy run evidence"
```

---

## Task 7: Update operator controls and verify the complete tranche

**Files:**

- Modify: `docs/technical-audit-operations.md`
- Modify: `PROJECT_STATE.md`

- [ ] **Step 1: Update rollout documentation**

Replace the current flag-only instructions with:

```bash
TECHNICAL_AUDIT_V1_ENABLED=true
TECHNICAL_AUDIT_INTERNAL_CLIENT_IDS=demo-client-id-1,demo-client-id-2
TECHNICAL_AUDIT_CHECK_SETS=foundation
```

Document these exact semantics:

- false/missing global flag: legacy route;
- true flag plus empty allowlist: no clients enabled;
- true flag plus listed IDs: only listed clients use V1;
- `*`: all clients, development/testing only;
- unavailable check-set name: configuration error, never a silent partial audit;
- technical-audit runtime error: V1 run reports the error and does not fall back to legacy heuristic content work.

Correct stale statements that say query matching or content-gap cards remain active in technical V1. State that this tranche creates only bounded manual community cards; technical result/action composition comes in the next plan.

- [ ] **Step 2: Record the product boundary in project state**

Update `PROJECT_STATE.md` with:

- new V1 run path and allowlist controls;
- legacy preservation/Pages-route behavior;
- direct community selection and five-card cap;
- current implemented check set: `foundation` only;
- no technical remediation cards yet;
- the ordered follow-on plan roadmap below.

- [ ] **Step 3: Run the full agent suite**

Run:

```bash
cd agents
.venv/bin/python -m pytest -q
```

Expected: all tests pass. If an unrelated pre-existing failure appears, record the exact test and output; do not call the tranche complete until changed-feature tests pass and the baseline is reconciled.

- [ ] **Step 4: Run the full dashboard suite**

Run:

```bash
cd dashboard
npm test
npm run build
```

Expected: all tests and the production build pass.

- [ ] **Step 5: Run changed-file lint**

Run:

```bash
cd dashboard
npx eslint \
  lib/client-tabs.ts \
  lib/run-presentation.ts \
  components/admin/HeatTable.tsx \
  app/admin/clients/'[id]'/layout.tsx \
  app/admin/clients/'[id]'/queries/page.tsx \
  app/admin/clients/'[id]'/runs/'[runId]'/page.tsx \
  __tests__/client-tabs.test.ts \
  __tests__/run-presentation.test.ts \
  __tests__/components/heat-table.test.tsx
```

Expected: no changed-file lint errors. The operator guide currently records a separate pre-existing repository-wide lint issue; verify whether it still exists before repeating that claim.

- [ ] **Step 6: Manually inspect one V1 fixture and one legacy run**

On a development/staging Supabase project only:

1. Enable one demo client by ID with `foundation`.
2. Run the improvement pipeline with at least seven positive tracker competitor leads.
3. Confirm the run writes technical observations/results and at most five `community_check` cards.
4. Confirm it writes no `query_page_matches` or `page_citation_scores` rows.
5. Confirm the query page has no PAGE/similarity/WEAK column.
6. Confirm the run page has no matching/content-gap/readiness-score claims.
7. Open an older run URL and confirm the legacy badge, matching evidence, and direct Pages route still render.
8. Remove the client ID from the allowlist and confirm the next run follows the legacy route.

- [ ] **Step 7: Commit documentation**

```bash
git add docs/technical-audit-operations.md PROJECT_STATE.md
git commit -m "docs: document simplified v1 rollout and rollback"
```

- [ ] **Step 8: Request code review before integration**

Use the `requesting-code-review` skill against the complete commit range. Resolve correctness findings, rerun Task 7 Steps 3–5, then use `verification-before-completion` before claiming the tranche is ready to merge.

---

## Sequential Follow-on Plans

This plan intentionally changes orchestration and presentation before adding more collectors. It does not reduce the approved checklist. After this tranche is verified, write and execute these plans in order against the then-current code:

1. **Unified technical audit cards and workflow** — linked immutable result evidence plus editable workflow records; Fail/Review/Unknown inbox behavior; Pass/Not applicable audit-page behavior; grouping, lifecycle, stale-state guard, and fresh re-audit verification.
2. **Protocol check set** — robots.txt, sitemap, TLS/HTTPS, and schema integrity/coverage with bounded evidence and five-state outcomes.
3. **Site-integrity check set** — broken links, image integrity/appropriateness review boundaries, freshness consistency, and existing source-support verification with bounded crawling.
4. **Performance and connected-service check set** — CrUX, Lighthouse lab context, Google Search Console, and Bing Webmaster Tools; disconnected integrations become explicit Unknown with owner/unblock instructions.
5. **Platform remediation adapters** — universal cards with Squarespace guided instructions, GitHub pull requests, guarded WordPress/Webflow staging/API paths, and copy/paste fallback. No adapter may publish without approval, stale-state validation, rollback, and re-audit.

Each follow-on plan must expand `AVAILABLE_CHECK_SETS`, add registry-level tests, update the stored scope/check versions, and pass the same internal allowlist gate. Do not enable an empty or partially implemented set by configuration alone.
