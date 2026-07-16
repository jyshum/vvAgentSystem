# Technical Audit Frontend Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the deterministic technical audit a dedicated admin surface (`AUDIT` tab) that shows findings, run-over-run lifecycle, and cause-grouped action cards, and remove the leftover screens from the deleted scoring engine.

**Architecture:** Reads go direct to Supabase from React Server Components via `createAdminClient()`. Writes (card transitions, run trigger) go through Next route handlers that proxy to FastAPI, because every transition in `agents/src/technical_audit/workflow.py` carries a stale-precondition guard and a deterministic re-audit that a direct table write would silently skip. One new backend endpoint lets the tab start an audit without firing the whole GEO pipeline.

**Tech Stack:** Next.js 16.2.9 (App Router, RSC), React 19.2.4, Tailwind v4, Vitest 4 + @testing-library/react, Supabase JS, FastAPI (Python 3.11, pytest).

**Spec:** `docs/superpowers/specs/2026-07-16-technical-audit-frontend-design.md`

---

## Critical Context For Someone New

**Read the spec first.** The non-obvious rules:

1. **No LLM in the audit path, ever.** A test spawns a fresh interpreter and fails if `openai`/`anthropic` get imported (`agents/tests/technical_audit/test_full_audit.py:158`). Do not import anything that pulls them in.
2. **Five states, no scores.** `pass | fail | review | unknown | not_applicable`. `unknown` means "we could not determine," and must never render as a failure. There is no score anywhere. Do not add one.
3. **No new dependencies.** `dashboard/package.json` has React, Next, Supabase and nothing else. No shadcn, no Radix, no icon library, no Motion. Do not `npm install` anything.
4. **Colors are inline CSS variables, not utility classes.** The codebase writes `style={{ color: "var(--mute)" }}`, not `className="text-gray-400"`. Follow it. Tokens are in `dashboard/app/globals.css`.
5. **No em-dashes in user-visible strings.** Use a hyphen.
6. **Dark theme only.** No `prefers-color-scheme` work.
7. **Never edit RUNS.** `app/admin/clients/[id]/runs/**` and `lib/run-presentation.ts` are explicitly out of scope.
8. **Never delete `/admin/approvals`.** It is a live top-level nav item with inbound deep links. Out of scope.

**House style reference:** copy the idioms in `dashboard/components/runs/TechnicalAuditChecklist.tsx` - mono micro-labels at `text-[8px] uppercase tracking-[0.12em]` in `var(--faint)`, `font-display font-light` numerals, `border` with `borderColor: "var(--hair)"`, sharp corners.

**Commands:**
- Frontend tests: `cd dashboard && npm test`
- Single frontend test: `cd dashboard && npx vitest run __tests__/components/<file> -t "<name>"`
- Backend tests: `cd agents && .venv/bin/python -m pytest -q`
- Component tests need `// @vitest-environment jsdom` as the **first line** (vitest 4 removed `environmentMatchGlobs`; the config default is `node`).

---

## File Structure

**Backend (2 files):**
| File | Responsibility |
|---|---|
| `agents/src/technical_audit/pipeline.py` | Add `run_standalone_audit()` - wraps existing `_run_and_persist_technical_audit` with `improvement_run_id=None` |
| `agents/server.py` | Add `POST /api/technical-audit/runs` |

**Frontend (new):**
| File | Responsibility |
|---|---|
| `dashboard/lib/technical-audit-types.ts` | *(modify)* add card + group types, drop `severity` |
| `dashboard/lib/technical-audit-data.ts` | Server-side loader: one function returning run + results + groups + cards |
| `dashboard/components/audit/LifecycleStrip.tsx` | Run-over-run counts |
| `dashboard/components/audit/AuditSummary.tsx` | Header, status counts, run switcher |
| `dashboard/components/audit/RunAuditButton.tsx` | `"use client"` - POST to trigger route |
| `dashboard/components/audit/ActionCard.tsx` | One card per finding group |
| `dashboard/components/audit/CardActions.tsx` | `"use client"` - state-machine buttons |
| `dashboard/components/audit/FindingsSections.tsx` | Moved from `components/runs/TechnicalAuditChecklist.tsx` |
| `dashboard/app/admin/clients/[id]/audit/page.tsx` | RSC assembly |
| `dashboard/app/api/technical-audit/runs/route.ts` | Proxy: trigger audit |
| `dashboard/app/api/technical-audit/cards/[cardId]/[action]/route.ts` | Proxy: card transitions |

**Frontend (modify):** `dashboard/lib/client-tabs.ts`
**Frontend (delete):** `app/admin/clients/[id]/cards/`, `app/admin/clients/[id]/pages/`, `components/pages-tab/`

---

## Task 1: Standalone audit runner (backend)

**Files:**
- Modify: `agents/src/technical_audit/pipeline.py`
- Test: `agents/tests/technical_audit/test_pipeline_standalone.py` (create)

**Context:** `_run_and_persist_technical_audit(sb, state, improvement_run_id, enabled_check_sets)` at `pipeline.py:47` already accepts `improvement_run_id` as a parameter, and `technical_audit_runs.improvement_run_id` is nullable (`supabase/migrations/014_technical_audit_foundation.sql:20`). So this is a thin wrapper, not an extraction. The `state` shape it needs is built the same way `cli.py:112-126` builds it.

- [ ] **Step 1: Write the failing test**

Create `agents/tests/technical_audit/test_pipeline_standalone.py`:

```python
from unittest.mock import patch

from tests.technical_audit.helpers import FakeSupabase


def _client_row():
    return {
        "id": "client-1",
        "brand_name": "Budget Your MD",
        "website_domain": "example.com",
        "site_platform": "squarespace",
        "implementation_mode": "copy_paste",
        "gsc_site_url": "",
    }


def test_run_standalone_audit_passes_null_improvement_run_id():
    """A standalone audit must not create an improvement_runs row."""
    from src.technical_audit import pipeline

    sb = FakeSupabase({"clients": [_client_row()]})
    captured = {}

    def fake_audit(sb_arg, state, improvement_run_id, enabled_check_sets):
        captured["improvement_run_id"] = improvement_run_id
        captured["state"] = state
        captured["check_sets"] = enabled_check_sets
        return {"run_id": "audit-1", "summary": {"total": 1}, "results": [], "error": None}

    with patch.object(pipeline, "_get_supabase", return_value=sb), \
         patch.object(pipeline, "_run_and_persist_technical_audit", fake_audit):
        result = pipeline.run_standalone_audit("client-1")

    assert captured["improvement_run_id"] is None
    assert captured["state"]["client_id"] == "client-1"
    assert captured["state"]["client_config"]["website_domain"] == "example.com"
    assert captured["state"]["client_config"]["site_platform"] == "squarespace"
    assert result["technical_audit_run_id"] == "audit-1"
    assert sb.inserted_tables().count("improvement_runs") == 0


def test_run_standalone_audit_raises_for_unknown_client():
    from src.technical_audit import pipeline

    sb = FakeSupabase({"clients": []})
    with patch.object(pipeline, "_get_supabase", return_value=sb):
        try:
            pipeline.run_standalone_audit("missing")
        except ValueError as exc:
            assert "client not found" in str(exc)
        else:
            raise AssertionError("expected ValueError")
```

- [ ] **Step 2: Check the fake-Supabase helper supports this**

Run: `cd agents && grep -n "class FakeSupabase" -A 40 tests/technical_audit/helpers.py`

If `FakeSupabase` does not accept a seed dict or lacks `inserted_tables()`, adapt the test to the helper's real API rather than changing the helper (other suites depend on it). If the helper cannot express this at all, add a minimal local fake **inside this test file only**.

- [ ] **Step 3: Run test to verify it fails**

Run: `cd agents && .venv/bin/python -m pytest tests/technical_audit/test_pipeline_standalone.py -v`
Expected: FAIL with `AttributeError: module 'src.technical_audit.pipeline' has no attribute 'run_standalone_audit'`

- [ ] **Step 4: Implement**

Add to the end of `agents/src/technical_audit/pipeline.py`:

```python
def run_standalone_audit(
    client_id: str,
    check_sets: tuple[str, ...] = DEFAULT_CHECK_SETS,
) -> dict:
    """Run and persist a technical audit with no improvement run around it.

    The audit is a first-class thing: it does not need a GEO pipeline run to
    exist. `technical_audit_runs.improvement_run_id` is nullable precisely so
    this is possible.
    """
    sb = _get_supabase()
    response = (
        sb.table("clients")
        .select("id,brand_name,website_domain,site_platform,implementation_mode,gsc_site_url")
        .eq("id", client_id)
        .maybe_single()
        .execute()
    )
    if not response.data:
        raise ValueError("client not found")
    client = response.data

    state = {
        "client_id": client_id,
        "thread_id": None,
        "client_config": {
            "brand_name": client["brand_name"],
            "website_domain": client["website_domain"],
            "site_platform": client.get("site_platform") or "other",
            "implementation_mode": client.get("implementation_mode") or "copy_paste",
            "gsc_site_url": client.get("gsc_site_url") or "",
        },
    }

    audit = _run_and_persist_technical_audit(sb, state, None, check_sets)
    return {
        "technical_audit_run_id": audit["run_id"],
        "technical_audit_summary": audit["summary"],
        "technical_audit_error": audit["error"],
    }
```

- [ ] **Step 5: Run tests**

Run: `cd agents && .venv/bin/python -m pytest tests/technical_audit/test_pipeline_standalone.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Verify nothing else broke**

Run: `cd agents && .venv/bin/python -m pytest -q`
Expected: PASS - was 357 before, expect 359 now. `run_technical_pipeline` behaviour must be unchanged.

- [ ] **Step 7: Commit**

```bash
git add agents/src/technical_audit/pipeline.py agents/tests/technical_audit/test_pipeline_standalone.py
git commit -m "feat: add standalone technical audit runner"
```

---

## Task 2: Standalone audit endpoint (backend)

**Files:**
- Modify: `agents/server.py`

**Context:** Follow the `/api/run` pattern at `agents/server.py:137` - background thread, immediate return. Card endpoints already live at `/api/technical-audit/cards/*`; this joins them.

- [ ] **Step 1: Implement the endpoint**

In `agents/server.py`, add near the other `ApproveCardRequest` model:

```python
class TriggerAuditRequest(BaseModel):
    client_id: str
```

Add after the `GET /api/technical-audit/runs/{run_id}` handler:

```python
def _run_audit_background(client_id: str) -> None:
    from src.technical_audit.pipeline import run_standalone_audit

    try:
        result = run_standalone_audit(client_id)
        print(f"  [Audit] Completed {client_id}: run {result['technical_audit_run_id']}")
    except Exception as e:
        print(f"  [Audit] Failed for {client_id}: {e}")


@app.post("/api/technical-audit/runs")
async def trigger_technical_audit(
    req: TriggerAuditRequest, authorization: str | None = Header(None)
):
    verify_auth(authorization)
    sb = _get_supabase()
    client = (
        sb.table("clients").select("id").eq("id", req.client_id).maybe_single().execute()
    )
    if not client.data:
        raise HTTPException(status_code=404, detail="client not found")

    t = threading.Thread(
        target=_run_audit_background, args=(req.client_id,), daemon=True
    )
    t.start()
    return {"status": "started", "client_id": req.client_id}
```

- [ ] **Step 2: Verify the server imports cleanly**

Run: `cd agents && .venv/bin/python -c "import server; print([r.path for r in server.app.routes if 'technical-audit' in r.path])"`
Expected: output includes `/api/technical-audit/runs` and the four card routes.

- [ ] **Step 3: Verify the audit purity test still passes**

Run: `cd agents && .venv/bin/python -m pytest tests/technical_audit/test_full_audit.py -q`
Expected: PASS. This confirms the new import path pulls in no LLM module.

- [ ] **Step 4: Run the full backend suite**

Run: `cd agents && .venv/bin/python -m pytest -q`
Expected: PASS (359)

- [ ] **Step 5: Commit**

```bash
git add agents/server.py
git commit -m "feat: add standalone technical audit trigger endpoint"
```

---

## Task 3: Frontend types

**Files:**
- Modify: `dashboard/lib/technical-audit-types.ts`

**Context:** Card fields come from `supabase/migrations/018_technical_audit_workflow.sql`. Statuses come from `ALLOWED_TRANSITIONS` in `agents/src/technical_audit/workflow.py:10`. Lifecycle states come from `classify_lifecycle` in `lifecycle.py:50`.

- [ ] **Step 1: Remove `severity` and add the new types**

In `dashboard/lib/technical-audit-types.ts`, delete the line `severity: string;` from `TechnicalAuditResult`, then append:

```typescript
export type TechnicalAuditLifecycleState =
  | "new"
  | "continuing"
  | "changed"
  | "resolved"
  | "regressed";

export type TechnicalAuditCardStatus =
  | "observed"
  | "draft_prepared"
  | "approved"
  | "rejected"
  | "applied"
  | "verified"
  | "still_failing"
  | "stale";

export interface TechnicalAuditFindingGroup {
  id: string;
  audit_run_id: string;
  group_key: string;
  check_id: string;
  remediation_id: string | null;
  summary: string;
  status: "fail" | "review" | "unknown";
  subjects: string[];
  created_at: string;
}

export interface TechnicalAuditActionCard {
  id: string;
  client_id: string;
  audit_run_id: string;
  group_key: string | null;
  source: "technical" | "community";
  status: TechnicalAuditCardStatus;
  title: string;
  platform: string;
  implementation_mode: string;
  instructions: string[];
  copy_values: Record<string, unknown>;
  precondition: Record<string, unknown>;
  approved_by: string | null;
  approved_at: string | null;
  applied_at: string | null;
  verification: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

/** Mirrors ALLOWED_TRANSITIONS in agents/src/technical_audit/workflow.py.
 *  The backend is authoritative; this only decides which buttons to render,
 *  so the UI never offers an action the state machine would reject. */
export const CARD_ALLOWED_TRANSITIONS: Record<
  TechnicalAuditCardStatus,
  TechnicalAuditCardStatus[]
> = {
  observed: ["draft_prepared", "rejected"],
  draft_prepared: ["approved", "rejected"],
  approved: ["applied", "rejected", "stale"],
  applied: ["verified", "still_failing"],
  stale: ["draft_prepared", "rejected"],
  rejected: [],
  verified: [],
  still_failing: ["draft_prepared"],
};

export const CARD_STATUS_LABEL: Record<TechnicalAuditCardStatus, string> = {
  observed: "observed",
  draft_prepared: "draft prepared",
  approved: "approved",
  rejected: "rejected",
  applied: "applied",
  verified: "verified",
  still_failing: "still failing",
  stale: "stale",
};

export const LIFECYCLE_LABEL: Record<TechnicalAuditLifecycleState, string> = {
  new: "new",
  continuing: "continuing",
  changed: "changed",
  resolved: "resolved",
  regressed: "regressed",
};

export const LIFECYCLE_COLOR: Record<TechnicalAuditLifecycleState, string> = {
  new: "var(--white)",
  continuing: "var(--mute)",
  changed: "var(--mute)",
  resolved: "var(--pos)",
  regressed: "var(--neg)",
};

/** Order for the lifecycle strip. Regressed leads: a fix that broke again is
 *  the one fact nothing else in the product reports. */
export const LIFECYCLE_STRIP_ORDER: TechnicalAuditLifecycleState[] = [
  "regressed",
  "new",
  "resolved",
  "changed",
];
```

- [ ] **Step 2: Fix the two fixtures that set `severity`**

Removing the field breaks exactly two object literals (verified - these are the only `severity` usages in the whole dashboard, and both are test fixtures, not RUNS source, so editing them does not violate the RUNS scope rule).

Delete this line from `dashboard/__tests__/components/technical-audit-checklist.test.tsx:44`:

```typescript
    severity: "medium",
```

Delete this line from `dashboard/__tests__/components/run-technical-audit-evidence.test.tsx:40`:

```typescript
  severity: "medium",
```

- [ ] **Step 3: Verify the removal compiles**

Run: `cd dashboard && npx tsc --noEmit`
Expected: PASS. If any *other* file still references `result.severity`, stop and report rather than editing it - anything under `app/admin/clients/[id]/runs/**` is out of scope, and in that case keep `severity` in the type instead.

- [ ] **Step 4: Run existing tests**

Run: `cd dashboard && npm test`
Expected: PASS (both edited test files still pass - `severity` was never asserted on, only set)

- [ ] **Step 5: Commit**

```bash
git add dashboard/lib/technical-audit-types.ts dashboard/__tests__/components/technical-audit-checklist.test.tsx dashboard/__tests__/components/run-technical-audit-evidence.test.tsx
git commit -m "feat: add technical audit card and lifecycle types"
```

---

## Task 4: Audit data loader

**Files:**
- Create: `dashboard/lib/technical-audit-data.ts`

**Context:** Server-only. Uses `createAdminClient()` from `dashboard/lib/supabase/admin.ts`, the same client every other admin page uses.

- [ ] **Step 1: Implement the loader**

Create `dashboard/lib/technical-audit-data.ts`:

```typescript
import { createAdminClient } from "@/lib/supabase/admin";
import type {
  TechnicalAuditActionCard,
  TechnicalAuditFindingGroup,
  TechnicalAuditResult,
  TechnicalAuditRun,
} from "@/lib/technical-audit-types";

export interface AuditTabData {
  run: TechnicalAuditRun | null;
  runs: Pick<TechnicalAuditRun, "id" | "status" | "started_at">[];
  results: TechnicalAuditResult[];
  groups: TechnicalAuditFindingGroup[];
  cards: TechnicalAuditActionCard[];
}

/** Loads everything the AUDIT tab renders for one run.
 *  `runId` omitted means the latest run for the client. */
export async function loadAuditTabData(
  clientId: string,
  runId?: string,
): Promise<AuditTabData> {
  const supabase = createAdminClient();

  const { data: runList } = await supabase
    .from("technical_audit_runs")
    .select("id, status, started_at")
    .eq("client_id", clientId)
    .order("started_at", { ascending: false })
    .limit(20);

  const runs = (runList as AuditTabData["runs"]) ?? [];
  const targetId = runId ?? runs[0]?.id;
  if (!targetId) {
    return { run: null, runs, results: [], groups: [], cards: [] };
  }

  const { data: run } = await supabase
    .from("technical_audit_runs")
    .select("*")
    .eq("id", targetId)
    .eq("client_id", clientId)
    .maybeSingle();

  if (!run) {
    return { run: null, runs, results: [], groups: [], cards: [] };
  }

  const [resultsRes, groupsRes, cardsRes] = await Promise.all([
    supabase
      .from("technical_audit_results")
      .select("*")
      .eq("audit_run_id", targetId)
      .order("section")
      .order("check_id")
      .order("subject"),
    supabase
      .from("technical_audit_finding_groups")
      .select("*")
      .eq("audit_run_id", targetId),
    supabase
      .from("technical_audit_action_cards")
      .select("*")
      .eq("audit_run_id", targetId)
      .order("created_at", { ascending: true }),
  ]);

  return {
    run: run as TechnicalAuditRun,
    runs,
    results: (resultsRes.data as TechnicalAuditResult[]) ?? [],
    groups: (groupsRes.data as TechnicalAuditFindingGroup[]) ?? [],
    cards: (cardsRes.data as TechnicalAuditActionCard[]) ?? [],
  };
}

/** Counts results by lifecycle_state for the strip. Returns only non-zero
 *  states so the strip stays quiet when nothing changed. */
export function lifecycleCounts(
  results: TechnicalAuditResult[],
): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const result of results) {
    if (!result.lifecycle_state) continue;
    counts[result.lifecycle_state] = (counts[result.lifecycle_state] ?? 0) + 1;
  }
  return counts;
}
```

- [ ] **Step 2: Typecheck**

Run: `cd dashboard && npx tsc --noEmit`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add dashboard/lib/technical-audit-data.ts
git commit -m "feat: add technical audit tab data loader"
```

---

## Task 5: LifecycleStrip component

**Files:**
- Create: `dashboard/components/audit/LifecycleStrip.tsx`
- Test: `dashboard/__tests__/components/lifecycle-strip.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `dashboard/__tests__/components/lifecycle-strip.test.tsx`:

```typescript
// @vitest-environment jsdom
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { LifecycleStrip } from "@/components/audit/LifecycleStrip";

afterEach(cleanup);

describe("LifecycleStrip", () => {
  it("renders non-zero lifecycle counts with regressed first", () => {
    render(
      <LifecycleStrip
        counts={{ regressed: 2, new: 3, resolved: 5, continuing: 40 }}
        previousRunAt="2026-07-09T11:02:00Z"
      />,
    );

    expect(screen.getByText("2 regressed")).toBeDefined();
    expect(screen.getByText("3 new")).toBeDefined();
    expect(screen.getByText("5 resolved")).toBeDefined();

    const items = screen.getAllByTestId("lifecycle-item");
    expect(items[0].textContent).toContain("regressed");
  });

  it("omits states with a zero count", () => {
    render(<LifecycleStrip counts={{ new: 1 }} previousRunAt="2026-07-09T11:02:00Z" />);
    expect(screen.queryByText(/regressed/)).toBeNull();
  });

  it("renders nothing when there is no previous run to compare against", () => {
    const { container } = render(
      <LifecycleStrip counts={{ new: 5 }} previousRunAt={null} />,
    );
    expect(container.firstChild).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dashboard && npx vitest run __tests__/components/lifecycle-strip.test.tsx`
Expected: FAIL - cannot resolve `@/components/audit/LifecycleStrip`

- [ ] **Step 3: Implement**

Create `dashboard/components/audit/LifecycleStrip.tsx`:

```typescript
import {
  LIFECYCLE_COLOR,
  LIFECYCLE_LABEL,
  LIFECYCLE_STRIP_ORDER,
} from "@/lib/technical-audit-types";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

export function LifecycleStrip({
  counts,
  previousRunAt,
}: {
  counts: Record<string, number>;
  previousRunAt: string | null;
}) {
  if (!previousRunAt) return null;

  const items = LIFECYCLE_STRIP_ORDER.filter((state) => (counts[state] ?? 0) > 0);
  if (items.length === 0) return null;

  return (
    <div
      className="mb-6 flex flex-wrap items-center gap-x-7 gap-y-2 border px-4 py-3"
      style={{ borderColor: "var(--hair)" }}
    >
      <span
        className="font-mono text-[8px] uppercase tracking-[0.12em]"
        style={{ color: "var(--faint)" }}
      >
        Since {formatDate(previousRunAt)}
      </span>
      {items.map((state) => (
        <span
          key={state}
          data-testid="lifecycle-item"
          className="font-serif text-[13px]"
          style={{ color: LIFECYCLE_COLOR[state] }}
        >
          {counts[state]} {LIFECYCLE_LABEL[state]}
        </span>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd dashboard && npx vitest run __tests__/components/lifecycle-strip.test.tsx`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add dashboard/components/audit/LifecycleStrip.tsx dashboard/__tests__/components/lifecycle-strip.test.tsx
git commit -m "feat: add audit lifecycle strip"
```

---

## Task 6: CardActions component

**Files:**
- Create: `dashboard/components/audit/CardActions.tsx`
- Test: `dashboard/__tests__/components/card-actions.test.tsx`

**Context:** Buttons are derived from `CARD_ALLOWED_TRANSITIONS` so the UI cannot offer an action the backend rejects. A 409 from the proxy means a stale precondition - the guard working - and must be shown, not swallowed.

- [ ] **Step 1: Write the failing test**

Create `dashboard/__tests__/components/card-actions.test.tsx`:

```typescript
// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { CardActions } from "@/components/audit/CardActions";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("CardActions", () => {
  it("offers approve and reject for a draft_prepared card", () => {
    render(<CardActions cardId="card-1" status="draft_prepared" />);
    expect(screen.getByRole("button", { name: /approve/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /reject/i })).toBeDefined();
    expect(screen.queryByRole("button", { name: /mark applied/i })).toBeNull();
  });

  it("offers mark applied for an approved card", () => {
    render(<CardActions cardId="card-1" status="approved" />);
    expect(screen.getByRole("button", { name: /mark applied/i })).toBeDefined();
  });

  it("offers no actions for a verified card", () => {
    render(<CardActions cardId="card-1" status="verified" />);
    expect(screen.queryAllByRole("button")).toHaveLength(0);
  });

  it("surfaces a stale precondition refusal instead of failing silently", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 409,
        json: async () => ({ error: "site changed since audit" }),
      }),
    );

    render(<CardActions cardId="card-1" status="approved" />);
    fireEvent.click(screen.getByRole("button", { name: /mark applied/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert").textContent).toContain("site changed since audit");
    });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dashboard && npx vitest run __tests__/components/card-actions.test.tsx`
Expected: FAIL - cannot resolve `@/components/audit/CardActions`

- [ ] **Step 3: Implement**

Create `dashboard/components/audit/CardActions.tsx`:

```typescript
"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  CARD_ALLOWED_TRANSITIONS,
  type TechnicalAuditCardStatus,
} from "@/lib/technical-audit-types";

/** Maps a target status to the backend action route segment and its label.
 *  Only transitions an operator drives are listed; `stale` is set by the
 *  backend guard, never requested from the UI. */
const ACTIONS: Partial<
  Record<TechnicalAuditCardStatus, { action: string; label: string; primary?: boolean }>
> = {
  approved: { action: "approve", label: "Approve", primary: true },
  rejected: { action: "reject", label: "Reject" },
  applied: { action: "mark-applied", label: "Mark applied", primary: true },
  verified: { action: "verify", label: "Verify", primary: true },
};

const BUTTON =
  "border px-3 py-1.5 font-mono text-[9px] uppercase tracking-[0.1em] disabled:opacity-40";

export function CardActions({
  cardId,
  status,
}: {
  cardId: string;
  status: TechnicalAuditCardStatus;
}) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const targets = (CARD_ALLOWED_TRANSITIONS[status] ?? []).filter(
    (target) => ACTIONS[target],
  );

  async function run(action: string) {
    setPending(true);
    setError(null);
    try {
      const res = await fetch(`/api/technical-audit/cards/${cardId}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.error || `Request failed (${res.status})`);
        return;
      }
      router.refresh();
    } catch {
      setError("Network error");
    } finally {
      setPending(false);
    }
  }

  if (targets.length === 0 && !error) return null;

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {targets.map((target) => {
          const config = ACTIONS[target]!;
          return (
            <button
              key={target}
              type="button"
              disabled={pending}
              onClick={() => run(config.action)}
              className={BUTTON}
              style={{
                color: config.primary ? "var(--pos)" : "var(--white)",
                borderColor: config.primary ? "var(--pos)" : "var(--faint)",
              }}
            >
              {config.label}
            </button>
          );
        })}
      </div>
      {error && (
        <p
          role="alert"
          className="mt-2 font-serif text-[12px]"
          style={{ color: "var(--neg)" }}
        >
          {error}
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd dashboard && npx vitest run __tests__/components/card-actions.test.tsx`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add dashboard/components/audit/CardActions.tsx dashboard/__tests__/components/card-actions.test.tsx
git commit -m "feat: add state-machine driven audit card actions"
```

---

## Task 7: ActionCard component

**Files:**
- Create: `dashboard/components/audit/ActionCard.tsx`
- Test: `dashboard/__tests__/components/audit-action-card.test.tsx`

**Context:** One card per finding group. Leads with NOW / EXPECTED. Instructions collapse. `copy_values` holds observed facts only (lists of broken URLs etc.) - never drafted prose.

- [ ] **Step 1: Write the failing test**

Create `dashboard/__tests__/components/audit-action-card.test.tsx`:

```typescript
// @vitest-environment jsdom
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { ActionCard } from "@/components/audit/ActionCard";
import type {
  TechnicalAuditActionCard,
  TechnicalAuditFindingGroup,
  TechnicalAuditResult,
} from "@/lib/technical-audit-types";

afterEach(cleanup);

const group: TechnicalAuditFindingGroup = {
  id: "group-1",
  audit_run_id: "audit-1",
  group_key: "gk-1",
  check_id: "metadata.description",
  remediation_id: "meta_description.correct",
  summary: "Meta description missing",
  status: "fail",
  subjects: ["/a", "/b", "/c", "/d"],
  created_at: "2026-07-16T09:14:00Z",
};

const card: TechnicalAuditActionCard = {
  id: "card-1",
  client_id: "client-1",
  audit_run_id: "audit-1",
  group_key: "gk-1",
  source: "technical",
  status: "draft_prepared",
  title: "Meta description missing",
  platform: "squarespace",
  implementation_mode: "guided",
  instructions: ["Open Page Settings then SEO.", "Edit the SEO Description field."],
  copy_values: {},
  precondition: {},
  approved_by: null,
  approved_at: null,
  applied_at: null,
  verification: {},
  created_at: "2026-07-16T09:14:00Z",
  updated_at: "2026-07-16T09:14:00Z",
};

function result(overrides: Partial<TechnicalAuditResult> = {}): TechnicalAuditResult {
  return {
    id: "result-1",
    audit_run_id: "audit-1",
    check_id: "metadata.description",
    check_version: 1,
    section: "metadata",
    subject: "/a",
    status: "fail",
    summary: "Meta description missing",
    expected: "A meta description describing the page's own content",
    observed: { description: null },
    evidence_refs: [],
    scope: {},
    applicability: { applies: true, reason: "public page" },
    confidence: "high",
    next_action: { owner: "admin", instruction: "Add a meta description" },
    remediation_id: "meta_description.correct",
    lifecycle_state: "new",
    created_at: "2026-07-16T09:14:00Z",
    ...overrides,
  };
}

describe("ActionCard", () => {
  it("renders one card covering all grouped subjects, not one per subject", () => {
    render(<ActionCard card={card} group={group} results={[result()]} />);
    expect(screen.getByText("Meta description missing")).toBeDefined();
    expect(screen.getByTestId("card-subjects").textContent).toContain("4 pages");
  });

  it("leads with expected, and hides instructions behind a disclosure", () => {
    render(<ActionCard card={card} group={group} results={[result()]} />);
    expect(screen.getByTestId("card-expected").textContent).toContain(
      "A meta description describing",
    );
    expect(screen.getByText(/how to apply/i).tagName.toLowerCase()).toBe("summary");
  });

  it("renders the lifecycle chip when the finding regressed", () => {
    render(
      <ActionCard
        card={card}
        group={group}
        results={[result({ lifecycle_state: "regressed" })]}
      />,
    );
    expect(screen.getByText("regressed")).toBeDefined();
  });

  it("renders observed facts from copy_values as data", () => {
    render(
      <ActionCard
        card={{ ...card, copy_values: { broken: ["https://x.test/a", "https://x.test/b"] } }}
        group={group}
        results={[result()]}
      />,
    );
    expect(screen.getByText("https://x.test/a")).toBeDefined();
    expect(screen.getByText("https://x.test/b")).toBeDefined();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dashboard && npx vitest run __tests__/components/audit-action-card.test.tsx`
Expected: FAIL - cannot resolve `@/components/audit/ActionCard`

- [ ] **Step 3: Implement**

Create `dashboard/components/audit/ActionCard.tsx`:

```typescript
import {
  CARD_STATUS_LABEL,
  LIFECYCLE_COLOR,
  LIFECYCLE_LABEL,
  TECHNICAL_AUDIT_STATUS_COLOR,
  TECHNICAL_AUDIT_STATUS_LABEL,
  type TechnicalAuditActionCard,
  type TechnicalAuditFindingGroup,
  type TechnicalAuditLifecycleState,
  type TechnicalAuditResult,
} from "@/lib/technical-audit-types";
import { CardActions } from "@/components/audit/CardActions";

const CHIP =
  "shrink-0 border px-2 py-1 font-mono text-[8px] uppercase tracking-[0.12em]";
const LABEL = "font-mono text-[8px] uppercase tracking-[0.12em]";

/** copy_values carries observed facts only (lists of failing URLs, dead
 *  sources, insecure resources). Never drafted prose - see the spec. */
function observedFacts(copyValues: Record<string, unknown>): string[] {
  const facts: string[] = [];
  for (const value of Object.values(copyValues)) {
    if (!Array.isArray(value)) continue;
    for (const item of value) {
      if (typeof item === "string") facts.push(item);
      else if (item && typeof item === "object") {
        const record = item as Record<string, unknown>;
        const url = record.url ?? record.href ?? record.target;
        const detail = record.status ?? record.reason;
        if (typeof url === "string") {
          facts.push(detail === undefined ? url : `${url} - ${String(detail)}`);
        }
      }
    }
  }
  return facts.slice(0, 10);
}

function subjectLine(subjects: string[]): string {
  const count = subjects.length;
  const noun = count === 1 ? "page" : "pages";
  const head = subjects[0] ?? "";
  const rest = count > 1 ? ` +${count - 1}` : "";
  return `${count} ${noun} · ${head}${rest}`;
}

export function ActionCard({
  card,
  group,
  results,
}: {
  card: TechnicalAuditActionCard;
  group: TechnicalAuditFindingGroup | undefined;
  results: TechnicalAuditResult[];
}) {
  const representative = results[0];
  const subjects = group?.subjects ?? results.map((item) => item.subject);
  const statusColor = TECHNICAL_AUDIT_STATUS_COLOR[group?.status ?? "fail"];
  const facts = observedFacts(card.copy_values);

  const lifecycle = results.find(
    (item) => item.lifecycle_state === "regressed",
  )?.lifecycle_state ?? representative?.lifecycle_state;
  const regressed = lifecycle === "regressed";

  return (
    <div
      className="mb-2.5 border p-4"
      style={{
        background: "var(--ink-soft)",
        borderColor: regressed ? "rgba(232, 154, 160, 0.4)" : "var(--hair)",
      }}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="font-serif text-[15px]" style={{ color: "var(--white)" }}>
            {card.title}
          </div>
          <div
            data-testid="card-subjects"
            className="mt-1 break-all font-mono text-[9px]"
            style={{ color: "var(--faint)" }}
          >
            {subjectLine(subjects)}
          </div>
        </div>
        <div className="flex shrink-0 gap-1.5">
          <span className={CHIP} style={{ color: statusColor, borderColor: statusColor }}>
            {TECHNICAL_AUDIT_STATUS_LABEL[group?.status ?? "fail"]}
          </span>
          {lifecycle && (
            <span
              className={CHIP}
              style={{
                color: LIFECYCLE_COLOR[lifecycle as TechnicalAuditLifecycleState],
                borderColor: LIFECYCLE_COLOR[lifecycle as TechnicalAuditLifecycleState],
              }}
            >
              {LIFECYCLE_LABEL[lifecycle as TechnicalAuditLifecycleState]}
            </span>
          )}
        </div>
      </div>

      <div className="my-3 px-3 py-3" style={{ background: "var(--ink)" }}>
        <div className="grid gap-y-2" style={{ gridTemplateColumns: "76px 1fr" }}>
          <div className={LABEL} style={{ color: "var(--faint)" }}>
            Now
          </div>
          <div className="font-serif text-[13px]" style={{ color: "var(--neg)" }}>
            {facts.length > 0 ? (
              <ul className="space-y-0.5">
                {facts.map((fact) => (
                  <li key={fact} className="break-all font-mono text-[11px]">
                    {fact}
                  </li>
                ))}
              </ul>
            ) : (
              representative?.summary ?? card.title
            )}
          </div>
          <div className={LABEL} style={{ color: "var(--faint)" }}>
            Expected
          </div>
          <div
            data-testid="card-expected"
            className="font-serif text-[13px]"
            style={{ color: "var(--mute)" }}
          >
            {representative?.expected ?? "-"}
          </div>
        </div>
      </div>

      {card.instructions.length > 0 && (
        <details>
          <summary
            className={`${LABEL} cursor-pointer py-1`}
            style={{ color: "var(--faint)" }}
          >
            How to apply · {card.platform}
          </summary>
          <ol
            className="ml-4 mt-2 list-decimal space-y-1 font-serif text-[13px] leading-relaxed"
            style={{ color: "var(--mute)" }}
          >
            {card.instructions.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </details>
      )}

      <details>
        <summary
          className={`${LABEL} cursor-pointer py-1`}
          style={{ color: "var(--faint)" }}
        >
          Evidence · {results.length} findings
        </summary>
        <pre
          className="mt-2 overflow-x-auto whitespace-pre-wrap break-words font-mono text-[10px] leading-relaxed"
          style={{ color: "var(--mute)" }}
        >
          {JSON.stringify(
            results.map((item) => ({ subject: item.subject, observed: item.observed })),
            null,
            2,
          )}
        </pre>
      </details>

      <div
        className="mt-3 flex flex-wrap items-center gap-3 border-t pt-3"
        style={{ borderColor: "var(--hair)" }}
      >
        <CardActions cardId={card.id} status={card.status} />
        <span className={LABEL} style={{ color: "var(--faint)" }}>
          {CARD_STATUS_LABEL[card.status]}
        </span>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd dashboard && npx vitest run __tests__/components/audit-action-card.test.tsx`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add dashboard/components/audit/ActionCard.tsx dashboard/__tests__/components/audit-action-card.test.tsx
git commit -m "feat: add cause-grouped audit action card"
```

---

## Task 8: Move the checklist into components/audit

**Files:**
- Create: `dashboard/components/audit/FindingsSections.tsx`
- Delete: `dashboard/components/runs/TechnicalAuditChecklist.tsx` **only if** nothing under `runs/` still imports it
- Test: `dashboard/__tests__/components/technical-audit-checklist.test.tsx` (update import)

**Context:** RUNS is out of scope. `components/runs/RunTechnicalAuditEvidence.tsx` imports `TechnicalAuditChecklist`, and run-detail imports that. **Do not break them.**

- [ ] **Step 1: Check who imports it**

Run: `cd dashboard && grep -rln "TechnicalAuditChecklist" --include="*.tsx" . | grep -v node_modules`
Expected: `components/runs/RunTechnicalAuditEvidence.tsx`, `__tests__/components/technical-audit-checklist.test.tsx`, and possibly the run-detail page.

- [ ] **Step 2: Copy, do not move**

Because RUNS still consumes the original, create `dashboard/components/audit/FindingsSections.tsx` as a **re-export plus rename**, keeping one implementation:

```typescript
/** The findings accordion, shared by the AUDIT tab and the legacy run-detail
 *  embed. The implementation stays in components/runs/ until the RUNS redesign
 *  retires that embed; this alias gives the AUDIT tab a stable name without
 *  duplicating the component. */
export { TechnicalAuditChecklist as FindingsSections } from "@/components/runs/TechnicalAuditChecklist";
```

- [ ] **Step 3: Verify both entry points typecheck**

Run: `cd dashboard && npx tsc --noEmit`
Expected: PASS

- [ ] **Step 4: Run the existing checklist test unchanged**

Run: `cd dashboard && npx vitest run __tests__/components/technical-audit-checklist.test.tsx`
Expected: PASS (unchanged - we did not modify the implementation)

- [ ] **Step 5: Commit**

```bash
git add dashboard/components/audit/FindingsSections.tsx
git commit -m "feat: alias findings accordion for the audit tab"
```

---

## Task 9: AuditSummary and RunAuditButton

**Files:**
- Create: `dashboard/components/audit/RunAuditButton.tsx`
- Create: `dashboard/components/audit/AuditSummary.tsx`
- Test: `dashboard/__tests__/components/audit-summary.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `dashboard/__tests__/components/audit-summary.test.tsx`:

```typescript
// @vitest-environment jsdom
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { AuditSummary } from "@/components/audit/AuditSummary";
import type { TechnicalAuditRun } from "@/lib/technical-audit-types";

afterEach(cleanup);

const run: TechnicalAuditRun = {
  id: "audit-1",
  client_id: "client-1",
  improvement_run_id: null,
  pipeline_run_id: null,
  audit_version: 1,
  status: "completed",
  scope: {},
  summary: { pass: 196, fail: 12, review: 3, unknown: 2, not_applicable: 4, total: 217 },
  error_message: null,
  started_at: "2026-07-16T09:14:00Z",
  completed_at: "2026-07-16T09:16:00Z",
};

describe("AuditSummary", () => {
  it("renders every status count including unknown", () => {
    render(<AuditSummary run={run} clientId="client-1" domain="example.com" />);
    expect(screen.getByText("12 fail")).toBeDefined();
    expect(screen.getByText("2 unknown")).toBeDefined();
    expect(screen.getByText("196 pass")).toBeDefined();
  });

  it("shows the check total", () => {
    render(<AuditSummary run={run} clientId="client-1" domain="example.com" />);
    expect(screen.getByTestId("audit-meta").textContent).toContain("217 checks");
  });

  it("renders no score anywhere", () => {
    const { container } = render(
      <AuditSummary run={run} clientId="client-1" domain="example.com" />,
    );
    expect(container.textContent).not.toContain("/100");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dashboard && npx vitest run __tests__/components/audit-summary.test.tsx`
Expected: FAIL - cannot resolve `@/components/audit/AuditSummary`

- [ ] **Step 3: Implement RunAuditButton**

Create `dashboard/components/audit/RunAuditButton.tsx`:

```typescript
"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function RunAuditButton({ clientId }: { clientId: string }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setPending(true);
    setError(null);
    try {
      const res = await fetch("/api/technical-audit/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ clientId }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.error || `Could not start audit (${res.status})`);
        return;
      }
      router.refresh();
    } catch {
      setError("Network error");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={run}
        disabled={pending}
        className="border px-3 py-1.5 font-mono text-[9px] uppercase tracking-[0.1em] disabled:opacity-40"
        style={{ color: "var(--pos)", borderColor: "var(--pos)" }}
      >
        {pending ? "Starting" : "Run audit"}
      </button>
      {error && (
        <span role="alert" className="font-serif text-[11px]" style={{ color: "var(--neg)" }}>
          {error}
        </span>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Implement AuditSummary**

Create `dashboard/components/audit/AuditSummary.tsx`:

```typescript
import {
  TECHNICAL_AUDIT_STATUS_COLOR,
  TECHNICAL_AUDIT_STATUS_LABEL,
  TECHNICAL_AUDIT_STATUS_ORDER,
  type TechnicalAuditRun,
} from "@/lib/technical-audit-types";
import { RunAuditButton } from "@/components/audit/RunAuditButton";

export function AuditSummary({
  run,
  clientId,
  domain,
}: {
  run: TechnicalAuditRun;
  clientId: string;
  domain: string;
}) {
  return (
    <div className="mb-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-[30px] font-light" style={{ color: "var(--white)" }}>
            Technical audit
          </h1>
          <div
            data-testid="audit-meta"
            className="mt-1 font-mono text-[8px] uppercase tracking-[0.12em]"
            style={{ color: "var(--faint)" }}
          >
            v{run.audit_version} · {run.summary.total} checks · {domain}
          </div>
        </div>
        <RunAuditButton clientId={clientId} />
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {TECHNICAL_AUDIT_STATUS_ORDER.map((status) => (
          <span
            key={status}
            className="border px-2 py-1 font-mono text-[8px] uppercase tracking-[0.1em]"
            style={{
              color: TECHNICAL_AUDIT_STATUS_COLOR[status],
              borderColor: TECHNICAL_AUDIT_STATUS_COLOR[status],
            }}
          >
            {run.summary[status] ?? 0} {TECHNICAL_AUDIT_STATUS_LABEL[status]}
          </span>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd dashboard && npx vitest run __tests__/components/audit-summary.test.tsx`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add dashboard/components/audit/AuditSummary.tsx dashboard/components/audit/RunAuditButton.tsx dashboard/__tests__/components/audit-summary.test.tsx
git commit -m "feat: add audit summary header and run trigger"
```

---

## Task 10: API proxy routes

**Files:**
- Create: `dashboard/app/api/technical-audit/runs/route.ts`
- Create: `dashboard/app/api/technical-audit/cards/[cardId]/[action]/route.ts`

**Context:** Copy the auth/config/error shape from `dashboard/app/api/runs/trigger/route.ts` exactly. Next 16 dynamic route params are a Promise and must be awaited.

- [ ] **Step 1: Confirm the Next 16 params signature**

Run: `cd dashboard && grep -rn "params" app/admin/clients/\[id\]/cards/page.tsx | head -3`
Expected: shows `params: Promise<{ id: string }>` then `await params`. Route handlers follow the same rule. If unsure, check `node_modules/next/dist/docs/` per `dashboard/AGENTS.md`.

- [ ] **Step 2: Implement the run trigger proxy**

Create `dashboard/app/api/technical-audit/runs/route.ts`:

```typescript
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { isConfiguredAdmin } from "@/lib/auth/admin";
import { NextRequest, NextResponse } from "next/server";

const LANGGRAPH_API = process.env.LANGGRAPH_API_URL;
const LANGGRAPH_KEY = process.env.LANGGRAPH_API_KEY;

export async function POST(req: NextRequest) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  if (!process.env.SUPABASE_SERVICE_ROLE_KEY) {
    return NextResponse.json(
      { error: "SUPABASE_SERVICE_ROLE_KEY missing on server" },
      { status: 503 },
    );
  }

  const admin = createAdminClient();
  if (!isConfiguredAdmin(user.email)) {
    const { data: clientUser } = await admin
      .from("client_users")
      .select("role")
      .eq("user_id", user.id)
      .maybeSingle();
    if (clientUser?.role !== "admin") {
      return NextResponse.json({ error: "Forbidden" }, { status: 403 });
    }
  }

  if (!LANGGRAPH_API || !LANGGRAPH_KEY) {
    return NextResponse.json({ error: "Audit API not configured" }, { status: 503 });
  }

  const { clientId } = await req.json();
  if (!clientId) return NextResponse.json({ error: "clientId required" }, { status: 400 });

  try {
    const res = await fetch(`${LANGGRAPH_API}/api/technical-audit/runs`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${LANGGRAPH_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ client_id: clientId }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return NextResponse.json(
        { error: body.detail || "Audit API error" },
        { status: res.status === 404 ? 404 : 502 },
      );
    }
    return NextResponse.json({ ok: true });
  } catch {
    return NextResponse.json({ error: "Audit API unreachable" }, { status: 502 });
  }
}
```

- [ ] **Step 3: Implement the card action proxy**

Create `dashboard/app/api/technical-audit/cards/[cardId]/[action]/route.ts`:

```typescript
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { isConfiguredAdmin } from "@/lib/auth/admin";
import { NextRequest, NextResponse } from "next/server";

const LANGGRAPH_API = process.env.LANGGRAPH_API_URL;
const LANGGRAPH_KEY = process.env.LANGGRAPH_API_KEY;

/** Only these transitions are operator-driven. `stale` is set by the backend
 *  guard and is never requested from the UI. */
const ALLOWED_ACTIONS = new Set(["approve", "reject", "mark-applied", "verify"]);

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ cardId: string; action: string }> },
) {
  const { cardId, action } = await params;
  if (!ALLOWED_ACTIONS.has(action)) {
    return NextResponse.json({ error: "Unknown action" }, { status: 400 });
  }

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  if (!process.env.SUPABASE_SERVICE_ROLE_KEY) {
    return NextResponse.json(
      { error: "SUPABASE_SERVICE_ROLE_KEY missing on server" },
      { status: 503 },
    );
  }

  const admin = createAdminClient();
  if (!isConfiguredAdmin(user.email)) {
    const { data: clientUser } = await admin
      .from("client_users")
      .select("role")
      .eq("user_id", user.id)
      .maybeSingle();
    if (clientUser?.role !== "admin") {
      return NextResponse.json({ error: "Forbidden" }, { status: 403 });
    }
  }

  if (!LANGGRAPH_API || !LANGGRAPH_KEY) {
    return NextResponse.json({ error: "Audit API not configured" }, { status: 503 });
  }

  try {
    const res = await fetch(
      `${LANGGRAPH_API}/api/technical-audit/cards/${cardId}/${action}`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${LANGGRAPH_KEY}`,
          "Content-Type": "application/json",
        },
        body: action === "approve"
          ? JSON.stringify({ approved_by: user.email })
          : undefined,
      },
    );

    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      // 409 is the stale-precondition guard refusing. Pass it through intact:
      // it is the state machine working, and the operator must see the reason.
      const status = res.status === 409 || res.status === 404 ? res.status : 502;
      return NextResponse.json(
        { error: body.detail || "Card action failed" },
        { status },
      );
    }
    return NextResponse.json({ ok: true, card: body.card });
  } catch {
    return NextResponse.json({ error: "Audit API unreachable" }, { status: 502 });
  }
}
```

- [ ] **Step 4: Typecheck**

Run: `cd dashboard && npx tsc --noEmit`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add dashboard/app/api/technical-audit
git commit -m "feat: add technical audit API proxy routes"
```

---

## Task 11: The AUDIT page

**Files:**
- Create: `dashboard/app/admin/clients/[id]/audit/page.tsx`

**Context:** Look at `dashboard/app/admin/clients/[id]/cards/page.tsx` for the RSC + `params: Promise` + `createAdminClient` shape before writing this (you delete that file in Task 13, so read it now).

- [ ] **Step 1: Implement the page**

Create `dashboard/app/admin/clients/[id]/audit/page.tsx`:

```typescript
export const dynamic = "force-dynamic";

import { createAdminClient } from "@/lib/supabase/admin";
import { loadAuditTabData, lifecycleCounts } from "@/lib/technical-audit-data";
import { AuditSummary } from "@/components/audit/AuditSummary";
import { LifecycleStrip } from "@/components/audit/LifecycleStrip";
import { ActionCard } from "@/components/audit/ActionCard";
import { FindingsSections } from "@/components/audit/FindingsSections";
import { RunAuditButton } from "@/components/audit/RunAuditButton";

const LABEL = "font-mono text-[8px] uppercase tracking-[0.12em]";

export default async function AuditPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ run?: string }>;
}) {
  const { id } = await params;
  const { run: runParam } = await searchParams;

  const supabase = createAdminClient();
  const { data: client } = await supabase
    .from("clients")
    .select("website_domain")
    .eq("id", id)
    .maybeSingle();

  const { run, runs, results, groups, cards } = await loadAuditTabData(id, runParam);

  if (!run) {
    return (
      <div>
        <div className="mb-4 flex items-end justify-between gap-4">
          <h1 className="font-display text-[30px] font-light" style={{ color: "var(--white)" }}>
            Technical audit
          </h1>
          <RunAuditButton clientId={id} />
        </div>
        <p className="font-serif italic" style={{ color: "var(--mute)" }}>
          No audit has run for this client yet.
        </p>
      </div>
    );
  }

  if (run.status !== "completed") {
    const failed = run.status === "error";
    return (
      <div>
        <div className="mb-4 flex items-end justify-between gap-4">
          <h1
            className="font-display text-[30px] font-light"
            style={{ color: failed ? "var(--neg)" : "var(--white)" }}
          >
            Technical audit {failed ? "failed" : "running"}
          </h1>
          <RunAuditButton clientId={id} />
        </div>
        <p className="font-serif text-[13px]" style={{ color: "var(--mute)" }}>
          {failed
            ? run.error_message || "The audit stopped before producing a checklist."
            : "Evidence is still being collected. Reload in a moment."}
        </p>
      </div>
    );
  }

  const previousRunAt = runs.find(
    (item) => item.id !== run.id && new Date(item.started_at) < new Date(run.started_at),
  )?.started_at ?? null;

  const groupByKey = new Map(groups.map((group) => [group.group_key, group]));
  const resultsByKey = new Map<string, typeof results>();
  for (const group of groups) {
    resultsByKey.set(
      group.group_key,
      results.filter(
        (item) => item.check_id === group.check_id && group.subjects.includes(item.subject),
      ),
    );
  }

  const openCards = cards.filter(
    (card) => !["rejected", "verified"].includes(card.status),
  );

  return (
    <div>
      <AuditSummary run={run} clientId={id} domain={client?.website_domain ?? ""} />

      <LifecycleStrip counts={lifecycleCounts(results)} previousRunAt={previousRunAt} />

      {openCards.length > 0 && (
        <section className="mb-8">
          <div className={`mb-2.5 ${LABEL}`} style={{ color: "var(--faint)" }}>
            Needs action · {openCards.length} cards
          </div>
          {openCards.map((card) => (
            <ActionCard
              key={card.id}
              card={card}
              group={card.group_key ? groupByKey.get(card.group_key) : undefined}
              results={card.group_key ? resultsByKey.get(card.group_key) ?? [] : []}
            />
          ))}
        </section>
      )}

      <div className={`mb-2.5 ${LABEL}`} style={{ color: "var(--faint)" }}>
        All findings
      </div>
      <FindingsSections run={run} results={results} />
    </div>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `cd dashboard && npx tsc --noEmit`
Expected: PASS

- [ ] **Step 3: Build**

Run: `cd dashboard && npm run build`
Expected: PASS, and the route list includes `/admin/clients/[id]/audit`.

- [ ] **Step 4: Commit**

```bash
git add dashboard/app/admin/clients/\[id\]/audit
git commit -m "feat: add technical audit tab page"
```

---

## Task 12: Navigation

**Files:**
- Modify: `dashboard/lib/client-tabs.ts`
- Test: `dashboard/__tests__/client-tabs.test.ts` (create)

- [ ] **Step 1: Write the failing test**

Create `dashboard/__tests__/client-tabs.test.ts`:

```typescript
import { describe, expect, it } from "vitest";

import { clientTabs } from "@/lib/client-tabs";

describe("clientTabs", () => {
  it("includes an AUDIT tab", () => {
    const labels = clientTabs("client-1").map((tab) => tab.label);
    expect(labels).toContain("AUDIT");
  });

  it("no longer includes the retired CARDS tab", () => {
    const labels = clientTabs("client-1").map((tab) => tab.label);
    expect(labels).not.toContain("CARDS");
  });

  it("points AUDIT at the client's audit route", () => {
    const audit = clientTabs("client-1").find((tab) => tab.label === "AUDIT");
    expect(audit?.href).toBe("/admin/clients/client-1/audit");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dashboard && npx vitest run __tests__/client-tabs.test.ts`
Expected: FAIL - "AUDIT" not found

- [ ] **Step 3: Implement**

Replace the array body in `dashboard/lib/client-tabs.ts`:

```typescript
export function clientTabs(clientId: string): ClientTab[] {
  return [
    { label: "OVERVIEW", href: `/admin/clients/${clientId}/overview` },
    { label: "QUERIES", href: `/admin/clients/${clientId}/queries` },
    { label: "RUNS", href: `/admin/clients/${clientId}/runs` },
    { label: "AUDIT", href: `/admin/clients/${clientId}/audit` },
    { label: "CONFIG", href: `/admin/clients/${clientId}/config` },
    { label: "REPORTS", href: `/admin/clients/${clientId}/reports` },
  ];
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd dashboard && npx vitest run __tests__/client-tabs.test.ts`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add dashboard/lib/client-tabs.ts dashboard/__tests__/client-tabs.test.ts
git commit -m "feat: add AUDIT tab and retire CARDS tab"
```

---

## Task 13: Delete the legacy scoring screens

**Files:**
- Delete: `dashboard/app/admin/clients/[id]/cards/`
- Delete: `dashboard/app/admin/clients/[id]/pages/`
- Delete: `dashboard/components/pages-tab/`
- Delete: any test files covering only the above

**Context:** Both were verified to have zero inbound links. **Do NOT touch `components/approvals/`, `app/admin/approvals/`, `components/board/`, `components/admin/HeatTable.tsx`, or `lib/run-presentation.ts`** - `/admin/approvals` is live and out of scope.

- [ ] **Step 1: Re-verify zero inbound links before deleting**

Run:
```bash
cd dashboard && grep -rn "pages-tab\|clients/\[id\]/cards\|clients/\[id\]/pages" --include="*.tsx" --include="*.ts" . | grep -v node_modules | grep -v "^./app/admin/clients/\[id\]/pages/\|^./components/pages-tab/\|^./app/admin/clients/\[id\]/cards/"
```
Expected: **no output**. If anything is listed, stop and report it rather than deleting.

- [ ] **Step 2: Find tests that cover only the deleted code**

Run: `cd dashboard && grep -rln "PagesTable\|pages-tab" __tests__/`
Expected: a list (possibly empty). These tests get deleted with their subject.

- [ ] **Step 3: Delete**

```bash
cd dashboard
git rm -r "app/admin/clients/[id]/cards" "app/admin/clients/[id]/pages" components/pages-tab
```
Then `git rm` any test files found in Step 2.

- [ ] **Step 4: Typecheck and test**

Run: `cd dashboard && npx tsc --noEmit && npm test`
Expected: PASS. If a test fails because it referenced `PagesTable`, delete that test file - it is testing deleted code.

- [ ] **Step 5: Build**

Run: `cd dashboard && npm run build`
Expected: PASS. `/admin/clients/[id]/cards` and `/admin/clients/[id]/pages` are gone from the route list; `/admin/approvals` is still present.

- [ ] **Step 6: Commit**

```bash
git commit -m "refactor: remove legacy scoring screens from dashboard"
```

---

## Task 14: Full verification

- [ ] **Step 1: Backend suite**

Run: `cd agents && .venv/bin/python -m pytest -q`
Expected: 359 passed

- [ ] **Step 2: Audit purity test specifically**

Run: `cd agents && .venv/bin/python -m pytest tests/technical_audit/test_full_audit.py::test_technical_audit_imports_no_llm_or_matcher_modules -v`
Expected: PASS

- [ ] **Step 3: Frontend suite**

Run: `cd dashboard && npm test`
Expected: all pass

- [ ] **Step 4: Typecheck, lint, build**

Run: `cd dashboard && rm -rf .next && npx tsc --noEmit && npm run lint && npm run build`
Expected: all pass, zero tsc errors.

The `rm -rf .next` is required, not cosmetic. A stale `.next/types/` accumulates duplicate generated files with a `" 3"` filename suffix (`routes.d 3.ts`, `validator 3.ts`, `cache-life.d 3.ts`) left by interrupted builds, and `tsc` reports them as duplicate-identifier errors that have nothing to do with the source. `.next/` is gitignored, so this never reaches the repo. From a clean `.next`, tsc is expected to report **zero** errors - do not accept a non-zero count as "pre-existing".

- [ ] **Step 5: Grep for regressions the tests cannot catch**

Run:
```bash
cd dashboard && grep -rn "structural_score\|/100\|scorer\.py" --include="*.tsx" --include="*.ts" components/audit app/admin/clients/\[id\]/audit lib/technical-audit-types.ts lib/technical-audit-data.ts
```
Expected: **no output** - no scores in any new code.

Run:
```bash
cd dashboard && grep -rn "—" --include="*.tsx" components/audit app/admin/clients/\[id\]/audit
```
Expected: **no output** - no em-dashes in user-visible strings.

- [ ] **Step 6: Confirm no new dependencies**

Run: `cd dashboard && git diff master --stat -- package.json package-lock.json`
Expected: **no output**. If `package.json` changed, a dependency was added - revert it.

- [ ] **Step 7: Report**

State plainly what passed and what did not. If anything failed, say so with the output rather than describing the work as complete.

---

## End-to-end verification (after merge, per the 2026-07-16 decision)

No local Docker demo is required. The real check is production:

1. Merge to `master`, let Vercel deploy, and redeploy the FastAPI service (the new endpoint lives there).
2. Open `/admin/clients/<client>/audit` and confirm the tab renders with the existing 217-result run.
3. Click **Run audit**. Confirm a new `technical_audit_runs` row appears with `improvement_run_id` **null** and no new `improvement_runs` row.
4. Confirm the lifecycle strip appears on the second run and reports counts against the first.
5. Walk one card: approve, mark applied, verify. Confirm the state machine advances.
6. To exercise the stale guard: approve a card, change the page on the live site, then mark applied. Expect a visible 409 refusal, not a silent success.

---

## Notes for the implementer

- If a task's test does not fail for the reason the plan predicts, stop and investigate. A test that passes before the implementation exists is testing nothing.
- `FakeSupabase` in `agents/tests/technical_audit/helpers.py` is shared. Do not change its API to suit Task 1; adapt the test instead.
- If Task 3's `severity` removal breaks a file under `app/admin/clients/[id]/runs/**`, keep `severity` in the type. RUNS is out of scope and not worth breaking for one unused field.
